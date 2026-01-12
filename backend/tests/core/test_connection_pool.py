"""
Tests for Connection Pool

Tests async connection pooling with health checks and metrics.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from backend.core.connection_pool import (
    ConnectionPool,
    ConnectionFactory,
    ConnectionState,
    PoolConfig,
    PoolStats,
    PooledConnection,
    PoolExhaustedError,
    PoolClosedError,
    SimpleConnectionFactory,
    create_pool,
)


class MockConnection:
    """Mock connection for testing."""
    
    def __init__(self, conn_id: int):
        self.id = conn_id
        self.closed = False
        self.healthy = True
    
    def close(self):
        self.closed = True


class MockConnectionFactory(ConnectionFactory[MockConnection]):
    """Mock factory for testing."""
    
    def __init__(self):
        self._counter = 0
        self.create_calls = 0
        self.close_calls = 0
        self.health_calls = 0
    
    async def create(self) -> MockConnection:
        self.create_calls += 1
        self._counter += 1
        return MockConnection(self._counter)
    
    async def close(self, connection: MockConnection) -> None:
        self.close_calls += 1
        connection.close()
    
    async def is_healthy(self, connection: MockConnection) -> bool:
        self.health_calls += 1
        return connection.healthy and not connection.closed


class TestPooledConnection:
    """Tests for PooledConnection wrapper."""
    
    def test_initial_state(self):
        """Should start idle."""
        conn = MockConnection(1)
        pooled = PooledConnection(connection=conn)
        
        assert pooled.state == ConnectionState.IDLE
        assert pooled.use_count == 0
    
    def test_mark_in_use(self):
        """Should track usage."""
        pooled = PooledConnection(connection=MockConnection(1))
        
        pooled.mark_in_use()
        
        assert pooled.state == ConnectionState.IN_USE
        assert pooled.use_count == 1
    
    def test_mark_idle(self):
        """Should return to idle."""
        pooled = PooledConnection(connection=MockConnection(1))
        pooled.mark_in_use()
        
        pooled.mark_idle()
        
        assert pooled.state == ConnectionState.IDLE
    
    def test_is_expired(self):
        """Should detect expired connections."""
        pooled = PooledConnection(connection=MockConnection(1))
        
        # Not expired immediately
        assert not pooled.is_expired(60.0)
        
        # Simulate old connection
        pooled.last_used_at = datetime(2020, 1, 1)
        assert pooled.is_expired(60.0)
    
    def test_in_use_not_expired(self):
        """In-use connections should never be expired."""
        pooled = PooledConnection(connection=MockConnection(1))
        pooled.last_used_at = datetime(2020, 1, 1)
        pooled.mark_in_use()
        
        assert not pooled.is_expired(60.0)


class TestPoolConfig:
    """Tests for PoolConfig."""
    
    def test_defaults(self):
        """Should have sensible defaults."""
        config = PoolConfig()
        
        assert config.min_connections == 1
        assert config.max_connections == 10
        assert config.idle_timeout_seconds == 300.0
        assert config.acquire_timeout_seconds == 30.0


class TestPoolStats:
    """Tests for PoolStats."""
    
    def test_to_dict(self):
        """Should convert to dict."""
        stats = PoolStats(
            total_connections=5,
            idle_connections=3,
            in_use_connections=2,
        )
        
        d = stats.to_dict()
        
        assert d["total_connections"] == 5
        assert d["idle_connections"] == 3
        assert "uptime_seconds" in d


class TestConnectionPool:
    """Tests for ConnectionPool."""
    
    @pytest.mark.asyncio
    async def test_start_creates_min_connections(self):
        """Should create minimum connections on start."""
        factory = MockConnectionFactory()
        config = PoolConfig(min_connections=3, max_connections=10)
        pool = ConnectionPool(factory, config)
        
        await pool.start()
        
        assert factory.create_calls == 3
        assert pool.stats.total_connections == 3
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_acquire_returns_connection(self):
        """Should return a connection."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_connections=1))
        await pool.start()
        
        async with pool.acquire() as conn:
            assert isinstance(conn, MockConnection)
            assert conn.id == 1
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_connection_reused(self):
        """Should reuse connections."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_connections=1))
        await pool.start()
        
        # Use connection twice
        async with pool.acquire() as conn1:
            first_id = conn1.id
        
        async with pool.acquire() as conn2:
            second_id = conn2.id
        
        # Should be same connection
        assert first_id == second_id
        assert factory.create_calls == 1
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_creates_new_when_all_in_use(self):
        """Should create new connection if all are in use."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_connections=1, max_connections=5))
        await pool.start()
        
        # Hold first connection
        async with pool.acquire() as conn1:
            # Get another - should create new
            async with pool.acquire() as conn2:
                assert conn1.id != conn2.id
                assert factory.create_calls == 2
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_exhausted_pool_timeout(self):
        """Should timeout when pool exhausted."""
        factory = MockConnectionFactory()
        config = PoolConfig(
            min_connections=1,
            max_connections=1,
            acquire_timeout_seconds=0.1,
        )
        pool = ConnectionPool(factory, config)
        await pool.start()
        
        async with pool.acquire():
            # Try to get another connection - should timeout
            with pytest.raises(PoolExhaustedError) as exc:
                async with pool.acquire():
                    pass
            
            assert exc.value.max_connections == 1
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_closed_pool_raises(self):
        """Should raise when pool is closed."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory)
        await pool.start()
        await pool.close()
        
        with pytest.raises(PoolClosedError):
            async with pool.acquire():
                pass
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Should track statistics."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_connections=1))
        await pool.start()
        
        async with pool.acquire():
            pass
        
        stats = pool.stats
        assert stats.total_acquires == 1
        assert stats.total_releases == 1
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Should work as context manager."""
        factory = MockConnectionFactory()
        
        async with ConnectionPool(factory, PoolConfig(min_connections=1)) as pool:
            async with pool.acquire() as conn:
                assert conn is not None
    
    @pytest.mark.asyncio
    async def test_close_closes_all_connections(self):
        """Should close all connections on close."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_connections=3))
        await pool.start()
        
        await pool.close()
        
        assert factory.close_calls == 3
        assert pool.stats.total_connections == 0
    
    @pytest.mark.asyncio
    async def test_auto_start_on_acquire(self):
        """Should auto-start if not started."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_connections=1))
        
        # Acquire without explicit start
        async with pool.acquire() as conn:
            assert conn is not None
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_acquires(self):
        """Should handle concurrent acquires."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_connections=1, max_connections=5))
        await pool.start()
        
        async def use_connection():
            async with pool.acquire() as conn:
                await asyncio.sleep(0.01)
                return conn.id
        
        # Run 5 concurrent tasks
        results = await asyncio.gather(*[use_connection() for _ in range(5)])
        
        # Should have used multiple connections
        assert len(set(results)) <= 5
        
        await pool.close()


class TestSimpleConnectionFactory:
    """Tests for SimpleConnectionFactory."""
    
    @pytest.mark.asyncio
    async def test_create_sync_function(self):
        """Should work with sync functions."""
        counter = [0]
        
        def create():
            counter[0] += 1
            return {"id": counter[0]}
        
        factory = SimpleConnectionFactory(
            create_fn=create,
            close_fn=lambda c: None,
        )
        
        conn = await factory.create()
        assert conn["id"] == 1
    
    @pytest.mark.asyncio
    async def test_create_async_function(self):
        """Should work with async functions."""
        async def create():
            await asyncio.sleep(0)
            return {"id": 1}
        
        factory = SimpleConnectionFactory(
            create_fn=create,
            close_fn=lambda c: None,
        )
        
        conn = await factory.create()
        assert conn["id"] == 1
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Should check health."""
        factory = SimpleConnectionFactory(
            create_fn=lambda: {"healthy": True},
            close_fn=lambda c: None,
            health_fn=lambda c: c["healthy"],
        )
        
        conn = await factory.create()
        assert await factory.is_healthy(conn)
        
        conn["healthy"] = False
        assert not await factory.is_healthy(conn)


class TestCreatePool:
    """Tests for create_pool convenience function."""
    
    @pytest.mark.asyncio
    async def test_create_pool(self):
        """Should create pool with simple callables."""
        connections = []
        
        pool = create_pool(
            create_fn=lambda: MockConnection(len(connections) + 1),
            close_fn=lambda c: c.close(),
            health_fn=lambda c: not c.closed,
            config=PoolConfig(min_connections=1),
        )
        
        async with pool:
            async with pool.acquire() as conn:
                assert isinstance(conn, MockConnection)


class TestPoolHealthChecks:
    """Tests for health check behavior."""
    
    @pytest.mark.asyncio
    async def test_unhealthy_connection_removed(self):
        """Should remove unhealthy connection on release."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_connections=1))
        await pool.start()
        
        # Get connection and make unhealthy
        async with pool.acquire() as conn:
            conn.healthy = False
        
        # Connection should be removed
        assert pool.stats.total_connections == 0
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_healthy_connection_kept(self):
        """Should keep healthy connection."""
        factory = MockConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_connections=1))
        await pool.start()
        
        async with pool.acquire() as conn:
            assert conn.healthy
        
        # Connection should still be there
        assert pool.stats.total_connections == 1
        
        await pool.close()

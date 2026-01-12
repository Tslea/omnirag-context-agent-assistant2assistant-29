"""
Connection Pool

Generic async connection pooling with health checks and metrics.
Designed for database and vector store connections.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """State of a pooled connection."""
    IDLE = "idle"
    IN_USE = "in_use"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class PoolConfig:
    """Configuration for connection pool."""
    min_connections: int = 1
    max_connections: int = 10
    idle_timeout_seconds: float = 300.0  # 5 minutes
    acquire_timeout_seconds: float = 30.0
    health_check_interval_seconds: float = 60.0
    retry_connect_on_failure: bool = True
    max_connect_retries: int = 3


@dataclass
class PoolStats:
    """Statistics for a connection pool."""
    total_connections: int = 0
    idle_connections: int = 0
    in_use_connections: int = 0
    total_acquires: int = 0
    total_releases: int = 0
    total_timeouts: int = 0
    total_errors: int = 0
    avg_acquire_time_ms: float = 0.0
    max_acquire_time_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_connections": self.total_connections,
            "idle_connections": self.idle_connections,
            "in_use_connections": self.in_use_connections,
            "total_acquires": self.total_acquires,
            "total_releases": self.total_releases,
            "total_timeouts": self.total_timeouts,
            "total_errors": self.total_errors,
            "avg_acquire_time_ms": round(self.avg_acquire_time_ms, 2),
            "max_acquire_time_ms": round(self.max_acquire_time_ms, 2),
            "uptime_seconds": (datetime.utcnow() - self.created_at).total_seconds(),
        }


# Type variable for connection type
T = TypeVar("T")


@dataclass
class PooledConnection(Generic[T]):
    """Wrapper for a pooled connection."""
    connection: T
    state: ConnectionState = ConnectionState.IDLE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: datetime = field(default_factory=datetime.utcnow)
    use_count: int = 0
    
    def mark_in_use(self) -> None:
        """Mark connection as in use."""
        self.state = ConnectionState.IN_USE
        self.last_used_at = datetime.utcnow()
        self.use_count += 1
    
    def mark_idle(self) -> None:
        """Mark connection as idle."""
        self.state = ConnectionState.IDLE
        self.last_used_at = datetime.utcnow()
    
    def is_expired(self, idle_timeout: float) -> bool:
        """Check if connection has been idle too long."""
        if self.state != ConnectionState.IDLE:
            return False
        idle_seconds = (datetime.utcnow() - self.last_used_at).total_seconds()
        return idle_seconds > idle_timeout
    
    @property
    def age_seconds(self) -> float:
        """Get connection age in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()


class ConnectionFactory(ABC, Generic[T]):
    """Abstract factory for creating connections."""
    
    @abstractmethod
    async def create(self) -> T:
        """Create a new connection."""
        pass
    
    @abstractmethod
    async def close(self, connection: T) -> None:
        """Close a connection."""
        pass
    
    @abstractmethod
    async def is_healthy(self, connection: T) -> bool:
        """Check if a connection is healthy."""
        pass
    
    async def on_acquire(self, connection: T) -> None:
        """Called when connection is acquired. Override for hooks."""
        pass
    
    async def on_release(self, connection: T) -> None:
        """Called when connection is released. Override for hooks."""
        pass


class PoolError(Exception):
    """Base exception for pool errors."""
    pass


class PoolExhaustedError(PoolError):
    """Raised when pool is exhausted and timeout reached."""
    def __init__(self, max_connections: int, timeout: float):
        self.max_connections = max_connections
        self.timeout = timeout
        super().__init__(
            f"Pool exhausted: max {max_connections} connections, "
            f"timed out after {timeout}s"
        )


class PoolClosedError(PoolError):
    """Raised when trying to use a closed pool."""
    pass


class ConnectionPool(Generic[T]):
    """
    Async connection pool with health checks and metrics.
    
    Example:
        ```python
        class VectorDBFactory(ConnectionFactory[ChromaClient]):
            async def create(self) -> ChromaClient:
                return await ChromaClient.connect()
            async def close(self, conn):
                await conn.close()
            async def is_healthy(self, conn):
                return await conn.heartbeat()
        
        pool = ConnectionPool(VectorDBFactory(), PoolConfig(max_connections=10))
        await pool.start()
        
        async with pool.acquire() as conn:
            results = await conn.query(...)
        
        await pool.close()
        ```
    """
    
    def __init__(
        self,
        factory: ConnectionFactory[T],
        config: Optional[PoolConfig] = None,
    ):
        self._factory = factory
        self._config = config or PoolConfig()
        
        self._connections: list[PooledConnection[T]] = []
        self._lock = asyncio.Lock()
        self._available = asyncio.Condition(self._lock)
        self._closed = False
        self._started = False
        
        # Stats tracking
        self._stats = PoolStats()
        self._acquire_times: list[float] = []
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
    
    @property
    def config(self) -> PoolConfig:
        """Get pool configuration."""
        return self._config
    
    @property
    def stats(self) -> PoolStats:
        """Get current pool statistics."""
        self._stats.total_connections = len(self._connections)
        self._stats.idle_connections = sum(
            1 for c in self._connections if c.state == ConnectionState.IDLE
        )
        self._stats.in_use_connections = sum(
            1 for c in self._connections if c.state == ConnectionState.IN_USE
        )
        if self._acquire_times:
            self._stats.avg_acquire_time_ms = sum(self._acquire_times) / len(self._acquire_times)
            self._stats.max_acquire_time_ms = max(self._acquire_times)
        return self._stats
    
    async def start(self) -> None:
        """Start the pool and create minimum connections."""
        if self._started:
            return
        
        async with self._lock:
            # Create minimum connections
            for _ in range(self._config.min_connections):
                try:
                    await self._create_connection_locked()
                except Exception as e:
                    logger.warning(f"Failed to create initial connection: {e}")
            
            self._started = True
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(
            f"Connection pool started with {len(self._connections)} connections "
            f"(min={self._config.min_connections}, max={self._config.max_connections})"
        )
    
    async def close(self) -> None:
        """Close the pool and all connections."""
        if self._closed:
            return
        
        self._closed = True
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._lock:
            for pooled in self._connections:
                try:
                    pooled.state = ConnectionState.CLOSING
                    await self._factory.close(pooled.connection)
                    pooled.state = ConnectionState.CLOSED
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            
            self._connections.clear()
        
        logger.info("Connection pool closed")
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[T]:
        """
        Acquire a connection from the pool.
        
        Usage:
            async with pool.acquire() as conn:
                await conn.query(...)
        """
        if self._closed:
            raise PoolClosedError("Pool is closed")
        
        if not self._started:
            await self.start()
        
        start_time = time.perf_counter()
        pooled = await self._acquire()
        acquire_time = (time.perf_counter() - start_time) * 1000
        self._acquire_times.append(acquire_time)
        # Keep only last 1000 measurements
        if len(self._acquire_times) > 1000:
            self._acquire_times = self._acquire_times[-1000:]
        
        try:
            await self._factory.on_acquire(pooled.connection)
            yield pooled.connection
        finally:
            await self._factory.on_release(pooled.connection)
            await self._release(pooled)
    
    async def _acquire(self) -> PooledConnection[T]:
        """Internal: acquire a pooled connection."""
        deadline = time.monotonic() + self._config.acquire_timeout_seconds
        
        async with self._available:
            while True:
                # Check for available idle connection
                for pooled in self._connections:
                    if pooled.state == ConnectionState.IDLE:
                        pooled.mark_in_use()
                        self._stats.total_acquires += 1
                        return pooled
                
                # Try to create new connection if under limit
                if len(self._connections) < self._config.max_connections:
                    try:
                        pooled = await self._create_connection_locked()
                        pooled.mark_in_use()
                        self._stats.total_acquires += 1
                        return pooled
                    except Exception as e:
                        self._stats.total_errors += 1
                        logger.warning(f"Failed to create connection: {e}")
                
                # Wait for a connection to become available
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._stats.total_timeouts += 1
                    raise PoolExhaustedError(
                        self._config.max_connections,
                        self._config.acquire_timeout_seconds,
                    )
                
                try:
                    await asyncio.wait_for(
                        self._available.wait(),
                        timeout=remaining,
                    )
                except asyncio.TimeoutError:
                    self._stats.total_timeouts += 1
                    raise PoolExhaustedError(
                        self._config.max_connections,
                        self._config.acquire_timeout_seconds,
                    )
    
    async def _release(self, pooled: PooledConnection[T]) -> None:
        """Internal: release a connection back to the pool."""
        async with self._available:
            if pooled in self._connections and not self._closed:
                # Check health before returning to pool
                try:
                    if await self._factory.is_healthy(pooled.connection):
                        pooled.mark_idle()
                        self._stats.total_releases += 1
                        self._available.notify()
                        return
                except Exception:
                    pass
                
                # Unhealthy - close and remove
                try:
                    await self._factory.close(pooled.connection)
                except Exception as e:
                    logger.warning(f"Error closing unhealthy connection: {e}")
                
                self._connections.remove(pooled)
            
            self._available.notify()
    
    async def _create_connection_locked(self) -> PooledConnection[T]:
        """Create a new connection (must hold lock)."""
        retries = self._config.max_connect_retries if self._config.retry_connect_on_failure else 1
        last_error: Optional[Exception] = None
        
        for attempt in range(retries):
            try:
                conn = await self._factory.create()
                pooled = PooledConnection(connection=conn)
                self._connections.append(pooled)
                return pooled
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))  # Backoff
        
        raise last_error or Exception("Failed to create connection")
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired connections."""
        while not self._closed:
            try:
                await asyncio.sleep(self._config.idle_timeout_seconds / 2)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired(self) -> None:
        """Close expired idle connections."""
        async with self._lock:
            expired = [
                c for c in self._connections
                if c.is_expired(self._config.idle_timeout_seconds)
                and len(self._connections) > self._config.min_connections
            ]
            
            for pooled in expired:
                try:
                    pooled.state = ConnectionState.CLOSING
                    await self._factory.close(pooled.connection)
                    self._connections.remove(pooled)
                except Exception as e:
                    logger.warning(f"Error closing expired connection: {e}")
    
    async def _health_check_loop(self) -> None:
        """Background task to check connection health."""
        while not self._closed:
            try:
                await asyncio.sleep(self._config.health_check_interval_seconds)
                await self._health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in health check loop: {e}")
    
    async def _health_check(self) -> None:
        """Check health of idle connections."""
        async with self._lock:
            unhealthy = []
            
            for pooled in self._connections:
                if pooled.state == ConnectionState.IDLE:
                    try:
                        if not await self._factory.is_healthy(pooled.connection):
                            unhealthy.append(pooled)
                    except Exception:
                        unhealthy.append(pooled)
            
            for pooled in unhealthy:
                try:
                    pooled.state = ConnectionState.CLOSING
                    await self._factory.close(pooled.connection)
                    self._connections.remove(pooled)
                    logger.info("Removed unhealthy connection from pool")
                except Exception as e:
                    logger.warning(f"Error closing unhealthy connection: {e}")
    
    # Context manager support
    async def __aenter__(self) -> "ConnectionPool[T]":
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


# === Convenience: Simple Connection Pool Factory ===

class SimpleConnectionFactory(ConnectionFactory[T]):
    """
    Simple connection factory using callables.
    
    Example:
        factory = SimpleConnectionFactory(
            create_fn=lambda: MyDB.connect(),
            close_fn=lambda c: c.close(),
            health_fn=lambda c: c.ping(),
        )
    """
    
    def __init__(
        self,
        create_fn: Callable[[], T],
        close_fn: Callable[[T], Any],
        health_fn: Optional[Callable[[T], bool]] = None,
    ):
        self._create_fn = create_fn
        self._close_fn = close_fn
        self._health_fn = health_fn or (lambda _: True)
    
    async def create(self) -> T:
        result = self._create_fn()
        if asyncio.iscoroutine(result):
            return await result
        return result
    
    async def close(self, connection: T) -> None:
        result = self._close_fn(connection)
        if asyncio.iscoroutine(result):
            await result
    
    async def is_healthy(self, connection: T) -> bool:
        result = self._health_fn(connection)
        if asyncio.iscoroutine(result):
            return await result
        return result


# === Utilities ===

def create_pool(
    create_fn: Callable[[], T],
    close_fn: Callable[[T], Any],
    health_fn: Optional[Callable[[T], bool]] = None,
    config: Optional[PoolConfig] = None,
) -> ConnectionPool[T]:
    """
    Create a connection pool with simple callables.
    
    Example:
        pool = create_pool(
            create_fn=lambda: chromadb.Client(),
            close_fn=lambda c: c.close(),
            config=PoolConfig(max_connections=5),
        )
    """
    factory = SimpleConnectionFactory(
        create_fn=create_fn,
        close_fn=close_fn,
        health_fn=health_fn,
    )
    return ConnectionPool(factory, config)

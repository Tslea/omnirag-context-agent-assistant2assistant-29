"""
Tests for Thread-Safe State Management

Tests the ThreadSafeState wrapper and related utilities.
"""

import asyncio
import pytest
from datetime import datetime

from backend.core.state import (
    StateVersion,
    ThreadSafeState,
    SharedContext,
    ThreadSafeSharedContext,
)


class TestStateVersion:
    """Tests for StateVersion."""
    
    def test_initial_version(self):
        """Should start at version 0."""
        version = StateVersion()
        assert version.version == 0
        assert version.last_modifier is None
    
    def test_increment(self):
        """Should increment version."""
        version = StateVersion()
        new_version = version.increment("test_agent")
        
        assert new_version.version == 1
        assert new_version.last_modifier == "test_agent"
        # Timestamp should be >= (can be same if very fast)
        assert new_version.last_modified >= version.last_modified


class TestThreadSafeState:
    """Tests for ThreadSafeState wrapper."""
    
    @pytest.mark.asyncio
    async def test_get_initial_value(self):
        """Should return initial value."""
        state = ThreadSafeState(initial_value={"count": 0})
        value = await state.get()
        assert value == {"count": 0}
    
    @pytest.mark.asyncio
    async def test_set_value(self):
        """Should set new value."""
        state = ThreadSafeState(initial_value=0)
        await state.set(42)
        value = await state.get()
        assert value == 42
    
    @pytest.mark.asyncio
    async def test_version_increments_on_set(self):
        """Should increment version on set."""
        state = ThreadSafeState(initial_value=0)
        assert state.version.version == 0
        
        await state.set(1, modifier="test")
        assert state.version.version == 1
        assert state.version.last_modifier == "test"
    
    @pytest.mark.asyncio
    async def test_read_context(self):
        """Should provide read access via context manager."""
        state = ThreadSafeState(initial_value={"key": "value"})
        
        async with state.read() as data:
            assert data["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_write_context(self):
        """Should provide write access via context manager."""
        state = ThreadSafeState(initial_value={"count": 0})
        
        async with state.write(modifier="writer") as data:
            data["count"] = 10
        
        async with state.read() as data:
            assert data["count"] == 10
        
        assert state.version.version == 1
        assert state.version.last_modifier == "writer"
    
    @pytest.mark.asyncio
    async def test_update_atomic(self):
        """Should apply update atomically."""
        state = ThreadSafeState(initial_value={"count": 0})
        
        await state.update(lambda d: d.update({"count": d["count"] + 5}))
        
        value = await state.get()
        assert value["count"] == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_updates(self):
        """Should handle concurrent updates safely."""
        state = ThreadSafeState(initial_value={"count": 0})
        
        async def increment():
            for _ in range(100):
                await state.update(lambda d: d.update({"count": d["count"] + 1}))
        
        # Run multiple concurrent incrementers
        await asyncio.gather(
            increment(),
            increment(),
            increment(),
        )
        
        value = await state.get()
        assert value["count"] == 300  # 3 tasks * 100 increments
    
    @pytest.mark.asyncio
    async def test_update_if_version_success(self):
        """Should update when version matches."""
        state = ThreadSafeState(initial_value={"value": "old"})
        
        result = await state.update_if_version(
            expected_version=0,
            func=lambda d: d.update({"value": "new"}),
        )
        
        assert result is True
        value = await state.get()
        assert value["value"] == "new"
    
    @pytest.mark.asyncio
    async def test_update_if_version_failure(self):
        """Should not update when version mismatches."""
        state = ThreadSafeState(initial_value={"value": "old"})
        
        # Increment version
        await state.set({"value": "old"})
        
        # Try to update with old version
        result = await state.update_if_version(
            expected_version=0,  # Wrong version
            func=lambda d: d.update({"value": "new"}),
        )
        
        assert result is False
        value = await state.get()
        assert value["value"] == "old"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_on_change_callback(self):
        """Should call callback on changes."""
        state = ThreadSafeState(initial_value=0)
        changes = []
        
        state.on_change(lambda v, ver: changes.append((v, ver.version)))
        
        await state.set(1)
        await state.set(2)
        
        assert len(changes) == 2
        assert changes[0] == (1, 1)
        assert changes[1] == (2, 2)


class TestSharedContext:
    """Tests for SharedContext dataclass."""
    
    def test_default_values(self):
        """Should have sensible defaults."""
        ctx = SharedContext()
        assert ctx.project_structure is None
        assert ctx.security_findings == []
        assert ctx.compliance_findings == []
        assert ctx._version == 0
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        ctx = SharedContext(workspace_path="/project")
        d = ctx.to_dict()
        
        assert d["workspace_path"] == "/project"
        assert d["security_findings"] == []
        assert "_version" in d


class TestThreadSafeSharedContext:
    """Tests for ThreadSafeSharedContext."""
    
    @pytest.mark.asyncio
    async def test_project_structure(self):
        """Should get/set project structure safely."""
        ctx = ThreadSafeSharedContext()
        
        # Initially None
        structure = await ctx.get_project_structure()
        assert structure is None
        
        # Set structure
        await ctx.set_project_structure({"type": "fullstack"})
        structure = await ctx.get_project_structure()
        assert structure == {"type": "fullstack"}
    
    @pytest.mark.asyncio
    async def test_security_findings(self):
        """Should manage security findings safely."""
        ctx = ThreadSafeSharedContext()
        
        # Add findings
        await ctx.add_security_finding({"id": 1, "severity": "high"})
        await ctx.add_security_finding({"id": 2, "severity": "low"})
        
        # Get findings
        findings = await ctx.get_security_findings()
        assert len(findings) == 2
        
        # Clear findings
        await ctx.clear_security_findings()
        findings = await ctx.get_security_findings()
        assert len(findings) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_finding_additions(self):
        """Should handle concurrent additions safely."""
        ctx = ThreadSafeSharedContext()
        
        async def add_findings(prefix: str):
            for i in range(50):
                await ctx.add_security_finding({"id": f"{prefix}_{i}"})
        
        # Add concurrently from multiple "agents"
        await asyncio.gather(
            add_findings("security"),
            add_findings("compliance"),
        )
        
        findings = await ctx.get_security_findings()
        assert len(findings) == 100
    
    @pytest.mark.asyncio
    async def test_version_tracking(self):
        """Should track version across changes."""
        ctx = ThreadSafeSharedContext()
        initial_version = ctx.version
        
        await ctx.add_security_finding({"id": 1})
        assert ctx.version > initial_version
        
        v1 = ctx.version
        await ctx.set_project_structure({"type": "backend"})
        assert ctx.version > v1
    
    @pytest.mark.asyncio
    async def test_to_dict(self):
        """Should serialize safely."""
        ctx = ThreadSafeSharedContext(workspace_path="/test")
        await ctx.add_security_finding({"id": 1})
        
        d = await ctx.to_dict()
        assert d["workspace_path"] == "/test"
        assert len(d["security_findings"]) == 1


class TestConcurrencyStress:
    """Stress tests for concurrency safety."""
    
    @pytest.mark.asyncio
    async def test_many_concurrent_writers(self):
        """Should handle many concurrent writers."""
        state = ThreadSafeState(initial_value={"values": []})
        
        async def writer(writer_id: int):
            for i in range(20):
                await state.update(
                    lambda d: d["values"].append(f"{writer_id}_{i}")
                )
                await asyncio.sleep(0.001)  # Small delay to increase contention
        
        # Run 10 concurrent writers
        await asyncio.gather(*[writer(i) for i in range(10)])
        
        value = await state.get()
        assert len(value["values"]) == 200  # 10 writers * 20 values
    
    @pytest.mark.asyncio
    async def test_readers_and_writers(self):
        """Should handle concurrent readers and writers."""
        state = ThreadSafeState(initial_value={"count": 0})
        read_values = []
        
        async def writer():
            for i in range(50):
                await state.update(lambda d: d.update({"count": d["count"] + 1}))
                await asyncio.sleep(0.001)
        
        async def reader():
            for _ in range(50):
                async with state.read() as data:
                    read_values.append(data["count"])
                await asyncio.sleep(0.001)
        
        await asyncio.gather(
            writer(),
            reader(),
            reader(),
        )
        
        # Final value should be 50
        value = await state.get()
        assert value["count"] == 50
        
        # All read values should be valid (0-50)
        assert all(0 <= v <= 50 for v in read_values)

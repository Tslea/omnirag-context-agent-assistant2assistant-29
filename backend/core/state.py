"""
Thread-Safe State Management

Provides thread-safe wrappers for shared state in async contexts.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class StateVersion:
    """Tracks version information for state changes."""
    version: int = 0
    last_modified: datetime = field(default_factory=datetime.utcnow)
    last_modifier: Optional[str] = None
    
    def increment(self, modifier: Optional[str] = None) -> "StateVersion":
        """Create incremented version."""
        return StateVersion(
            version=self.version + 1,
            last_modified=datetime.utcnow(),
            last_modifier=modifier,
        )


class ThreadSafeState(Generic[T]):
    """
    Thread-safe wrapper for mutable state in async contexts.
    
    Provides:
    - Automatic locking for all operations
    - Version tracking for optimistic concurrency
    - Change notifications via callbacks
    
    Example:
        ```python
        state = ThreadSafeState(initial_value=MyData())
        
        # Read safely
        async with state.read() as data:
            print(data.some_field)
        
        # Write safely
        async with state.write() as data:
            data.some_field = "new value"
            # Lock released after context
        
        # Atomic update
        await state.update(lambda d: setattr(d, 'count', d.count + 1))
        ```
    """
    
    def __init__(
        self,
        initial_value: T,
        name: str = "state",
    ):
        self._value = initial_value
        self._name = name
        self._lock = asyncio.Lock()
        self._version = StateVersion()
        self._on_change_callbacks: list[Callable[[T, StateVersion], None]] = []
    
    @property
    def version(self) -> StateVersion:
        """Get current version (read without lock for monitoring)."""
        return self._version
    
    def read(self) -> "ReadContext[T]":
        """
        Get a read context for the state.
        
        Returns:
            Context manager that yields the state value
        """
        return ReadContext(self)
    
    def write(self, modifier: Optional[str] = None) -> "WriteContext[T]":
        """
        Get a write context for the state.
        
        Args:
            modifier: Optional identifier for who is making the change
            
        Returns:
            Context manager that yields the state value
        """
        return WriteContext(self, modifier)
    
    async def get(self) -> T:
        """Get current value (shorthand for read context)."""
        async with self._lock:
            return self._value
    
    async def set(self, value: T, modifier: Optional[str] = None) -> None:
        """Set value (shorthand for write context)."""
        async with self._lock:
            self._value = value
            self._version = self._version.increment(modifier)
            self._notify_change()
    
    async def update(
        self,
        func: Callable[[T], None],
        modifier: Optional[str] = None,
    ) -> None:
        """
        Apply an update function to the state atomically.
        
        Args:
            func: Function that modifies the state in place
            modifier: Optional identifier for who is making the change
        """
        async with self._lock:
            func(self._value)
            self._version = self._version.increment(modifier)
            self._notify_change()
    
    async def update_if_version(
        self,
        expected_version: int,
        func: Callable[[T], None],
        modifier: Optional[str] = None,
    ) -> bool:
        """
        Apply update only if version matches (optimistic concurrency).
        
        Args:
            expected_version: Version to check against
            func: Function to apply if version matches
            modifier: Optional identifier
            
        Returns:
            True if update was applied, False if version mismatch
        """
        async with self._lock:
            if self._version.version != expected_version:
                logger.warning(
                    f"Version mismatch in {self._name}: "
                    f"expected {expected_version}, got {self._version.version}"
                )
                return False
            
            func(self._value)
            self._version = self._version.increment(modifier)
            self._notify_change()
            return True
    
    def on_change(self, callback: Callable[[T, StateVersion], None]) -> None:
        """Register a callback to be called on state changes."""
        self._on_change_callbacks.append(callback)
    
    def _notify_change(self) -> None:
        """Notify all registered callbacks of state change."""
        for callback in self._on_change_callbacks:
            try:
                callback(self._value, self._version)
            except Exception as e:
                logger.warning(f"Error in change callback for {self._name}: {e}")


class ReadContext(Generic[T]):
    """Context manager for reading state."""
    
    def __init__(self, state: ThreadSafeState[T]):
        self._state = state
    
    async def __aenter__(self) -> T:
        await self._state._lock.acquire()
        return self._state._value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._state._lock.release()
        return False


class WriteContext(Generic[T]):
    """Context manager for writing state."""
    
    def __init__(self, state: ThreadSafeState[T], modifier: Optional[str] = None):
        self._state = state
        self._modifier = modifier
    
    async def __aenter__(self) -> T:
        await self._state._lock.acquire()
        return self._state._value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Only increment version if no exception
        if exc_type is None:
            self._state._version = self._state._version.increment(self._modifier)
            self._state._notify_change()
        self._state._lock.release()
        return False


@dataclass
class SharedContext:
    """
    Typed shared context for agent communication.
    
    Replaces the untyped `shared_state: dict` in AgentContext with
    explicit, typed fields that are thread-safe.
    
    This enables:
    - Type checking and autocomplete
    - Explicit dependencies between agents
    - Safe concurrent access
    """
    # Project structure (managed by Context Agent)
    project_structure: Optional[Any] = None  # Will be ProjectStructure
    
    # Security findings (managed by Security Agent)
    security_findings: list[dict[str, Any]] = field(default_factory=list)
    
    # Compliance findings (managed by Compliance Agent)
    compliance_findings: list[dict[str, Any]] = field(default_factory=list)
    
    # RAG context (managed by RAG Agent)
    relevant_summaries: list[str] = field(default_factory=list)
    
    # Session metadata
    workspace_path: Optional[str] = None
    session_started: datetime = field(default_factory=datetime.utcnow)
    
    # Version for optimistic concurrency
    _version: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "project_structure": (
                self.project_structure.to_dict() 
                if self.project_structure and hasattr(self.project_structure, "to_dict")
                else None
            ),
            "security_findings": self.security_findings,
            "compliance_findings": self.compliance_findings,
            "relevant_summaries": self.relevant_summaries,
            "workspace_path": self.workspace_path,
            "session_started": self.session_started.isoformat(),
            "_version": self._version,
        }


class ThreadSafeSharedContext:
    """
    Thread-safe wrapper for SharedContext.
    
    Provides field-level locking for efficient concurrent access.
    """
    
    def __init__(self, workspace_path: Optional[str] = None):
        self._context = SharedContext(workspace_path=workspace_path)
        self._lock = asyncio.Lock()
        self._field_locks: dict[str, asyncio.Lock] = {
            "project_structure": asyncio.Lock(),
            "security_findings": asyncio.Lock(),
            "compliance_findings": asyncio.Lock(),
            "relevant_summaries": asyncio.Lock(),
        }
    
    @property
    def version(self) -> int:
        """Get current version."""
        return self._context._version
    
    async def get_project_structure(self) -> Optional[Any]:
        """Get project structure safely."""
        async with self._field_locks["project_structure"]:
            return self._context.project_structure
    
    async def set_project_structure(
        self,
        structure: Any,
        modifier: Optional[str] = None,
    ) -> None:
        """Set project structure safely."""
        async with self._field_locks["project_structure"]:
            self._context.project_structure = structure
            self._context._version += 1
            logger.debug(f"Project structure updated by {modifier}, version={self._context._version}")
    
    async def add_security_finding(self, finding: dict[str, Any]) -> None:
        """Add a security finding safely."""
        async with self._field_locks["security_findings"]:
            self._context.security_findings.append(finding)
            self._context._version += 1
    
    async def get_security_findings(self) -> list[dict[str, Any]]:
        """Get security findings safely."""
        async with self._field_locks["security_findings"]:
            return self._context.security_findings.copy()
    
    async def clear_security_findings(self) -> None:
        """Clear security findings safely."""
        async with self._field_locks["security_findings"]:
            self._context.security_findings.clear()
            self._context._version += 1
    
    async def add_compliance_finding(self, finding: dict[str, Any]) -> None:
        """Add a compliance finding safely."""
        async with self._field_locks["compliance_findings"]:
            self._context.compliance_findings.append(finding)
            self._context._version += 1
    
    async def get_compliance_findings(self) -> list[dict[str, Any]]:
        """Get compliance findings safely."""
        async with self._field_locks["compliance_findings"]:
            return self._context.compliance_findings.copy()
    
    async def set_relevant_summaries(self, summaries: list[str]) -> None:
        """Set relevant summaries safely."""
        async with self._field_locks["relevant_summaries"]:
            self._context.relevant_summaries = summaries
            self._context._version += 1
    
    async def get_relevant_summaries(self) -> list[str]:
        """Get relevant summaries safely."""
        async with self._field_locks["relevant_summaries"]:
            return self._context.relevant_summaries.copy()
    
    async def to_dict(self) -> dict[str, Any]:
        """Get full context as dict safely."""
        async with self._lock:
            return self._context.to_dict()

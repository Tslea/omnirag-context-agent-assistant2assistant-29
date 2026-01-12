"""
Workflow Interface

Defines the contract for LangChain/LangGraph workflows.
Workflows orchestrate multi-step processes and agent coordination.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Generic
from uuid import uuid4


class WorkflowStatus(str, Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Individual step execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


T = TypeVar("T")


@dataclass
class WorkflowStep:
    """
    A single step in a workflow.
    
    Attributes:
        id: Unique step identifier
        name: Human-readable step name
        description: What this step does
        handler: Function to execute for this step
        dependencies: Step IDs that must complete before this step
        retry_count: Number of times to retry on failure
        timeout: Timeout in seconds (None = no timeout)
    """
    name: str
    handler: Callable[..., Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    retry_count: int = 0
    timeout: Optional[float] = None
    condition: Optional[Callable[[dict[str, Any]], bool]] = None


@dataclass
class StepResult:
    """Result of executing a workflow step."""
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retries: int = 0


@dataclass
class WorkflowContext:
    """
    Runtime context for workflow execution.
    
    Attributes:
        workflow_id: Unique workflow run identifier
        inputs: Initial workflow inputs
        state: Mutable state that persists across steps
        step_results: Results from completed steps
        metadata: Additional context metadata
    """
    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    inputs: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    step_results: dict[str, StepResult] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def get_input(self, key: str, default: Any = None) -> Any:
        """Get an input value."""
        return self.inputs.get(key, default)
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        return self.state.get(key, default)
    
    def set_state(self, key: str, value: Any) -> None:
        """Set a state value."""
        self.state[key] = value
    
    def get_step_output(self, step_id: str) -> Any:
        """Get the output from a completed step."""
        result = self.step_results.get(step_id)
        return result.output if result else None


@dataclass
class WorkflowMetadata:
    """Metadata describing a workflow."""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    author: Optional[str] = None


@dataclass
class WorkflowResult(Generic[T]):
    """Final result of a workflow execution."""
    workflow_id: str
    status: WorkflowStatus
    output: Optional[T] = None
    error: Optional[str] = None
    step_results: dict[str, StepResult] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    @property
    def is_success(self) -> bool:
        """Check if workflow completed successfully."""
        return self.status == WorkflowStatus.COMPLETED


class WorkflowBase(ABC):
    """
    Abstract base class for workflows.
    
    Workflows define multi-step processes using LangChain/LangGraph.
    They orchestrate agents and tools to accomplish complex tasks.
    
    Example:
        ```python
        class CodeReviewWorkflow(WorkflowBase):
            @property
            def metadata(self) -> WorkflowMetadata:
                return WorkflowMetadata(
                    id="code_review",
                    name="Code Review Workflow",
                    description="Automated code review pipeline"
                )
            
            def define_steps(self) -> list[WorkflowStep]:
                return [
                    WorkflowStep(name="parse", handler=self.parse_code),
                    WorkflowStep(name="analyze", handler=self.analyze, dependencies=["parse"]),
                    WorkflowStep(name="report", handler=self.generate_report, dependencies=["analyze"]),
                ]
        ```
    """
    
    def __init__(self):
        self._status = WorkflowStatus.PENDING
        self._steps: list[WorkflowStep] = []
        self._current_step: Optional[str] = None
    
    @property
    @abstractmethod
    def metadata(self) -> WorkflowMetadata:
        """Return metadata describing this workflow."""
        pass
    
    @property
    def status(self) -> WorkflowStatus:
        """Get the current workflow status."""
        return self._status
    
    @property
    def steps(self) -> list[WorkflowStep]:
        """Get the workflow steps."""
        if not self._steps:
            self._steps = self.define_steps()
        return self._steps
    
    @property
    def current_step(self) -> Optional[str]:
        """Get the currently executing step ID."""
        return self._current_step
    
    @abstractmethod
    def define_steps(self) -> list[WorkflowStep]:
        """
        Define the steps in this workflow.
        
        Returns:
            List of WorkflowStep objects
        """
        pass
    
    async def execute(
        self,
        context: WorkflowContext,
    ) -> WorkflowResult:
        """
        Execute the workflow.
        
        Args:
            context: Workflow context with inputs
            
        Returns:
            WorkflowResult with outputs and status
        """
        started_at = datetime.utcnow()
        self._status = WorkflowStatus.RUNNING
        
        try:
            # Build dependency graph and execute in order
            executed: set[str] = set()
            steps_by_id = {s.id: s for s in self.steps}
            
            while len(executed) < len(self.steps):
                # Find steps ready to execute
                ready = [
                    s for s in self.steps
                    if s.id not in executed
                    and all(dep in executed for dep in s.dependencies)
                ]
                
                if not ready:
                    # Circular dependency or all done
                    break
                
                for step in ready:
                    # Check condition
                    if step.condition and not step.condition(context.state):
                        context.step_results[step.id] = StepResult(
                            step_id=step.id,
                            status=StepStatus.SKIPPED,
                        )
                        executed.add(step.id)
                        continue
                    
                    # Execute step
                    self._current_step = step.id
                    step_result = await self._execute_step(step, context)
                    context.step_results[step.id] = step_result
                    executed.add(step.id)
                    
                    if step_result.status == StepStatus.FAILED:
                        raise Exception(f"Step {step.name} failed: {step_result.error}")
            
            self._status = WorkflowStatus.COMPLETED
            completed_at = datetime.utcnow()
            
            return WorkflowResult(
                workflow_id=context.workflow_id,
                status=WorkflowStatus.COMPLETED,
                output=context.state.get("output"),
                step_results=context.step_results,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            )
            
        except Exception as e:
            self._status = WorkflowStatus.FAILED
            completed_at = datetime.utcnow()
            
            return WorkflowResult(
                workflow_id=context.workflow_id,
                status=WorkflowStatus.FAILED,
                error=str(e),
                step_results=context.step_results,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            )
        finally:
            self._current_step = None
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> StepResult:
        """Execute a single workflow step with retry support."""
        started_at = datetime.utcnow()
        retries = 0
        last_error: Optional[str] = None
        
        while retries <= step.retry_count:
            try:
                output = await step.handler(context)
                completed_at = datetime.utcnow()
                
                return StepResult(
                    step_id=step.id,
                    status=StepStatus.COMPLETED,
                    output=output,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=int((completed_at - started_at).total_seconds() * 1000),
                    retries=retries,
                )
            except Exception as e:
                last_error = str(e)
                retries += 1
        
        completed_at = datetime.utcnow()
        return StepResult(
            step_id=step.id,
            status=StepStatus.FAILED,
            error=last_error,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            retries=retries - 1,
        )
    
    async def cancel(self) -> None:
        """Cancel the workflow execution."""
        self._status = WorkflowStatus.CANCELLED
    
    async def pause(self) -> None:
        """Pause the workflow execution."""
        self._status = WorkflowStatus.PAUSED
    
    async def resume(self) -> None:
        """Resume a paused workflow."""
        if self._status == WorkflowStatus.PAUSED:
            self._status = WorkflowStatus.RUNNING
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.metadata.id}, status={self.status.value})>"

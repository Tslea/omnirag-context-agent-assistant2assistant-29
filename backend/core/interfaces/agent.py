"""
Agent Interface

Defines the contract for all agents in the system.
Agents are the core building blocks loaded as plugins via AutoGen.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4


class MessageType(str, Enum):
    """Types of messages agents can send/receive."""
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM = "system"
    ERROR = "error"
    STATUS = "status"


class AgentStatus(str, Enum):
    """Agent lifecycle states."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentMessage:
    """
    A message exchanged between agents or with the user.
    
    Attributes:
        id: Unique message identifier
        type: Message type
        content: Message content (text or structured data)
        sender: Sender agent ID
        recipient: Optional recipient agent ID (broadcast if None)
        metadata: Additional message metadata
        timestamp: When the message was created
    """
    content: Any
    type: MessageType = MessageType.TEXT
    sender: str = "system"
    id: str = field(default_factory=lambda: str(uuid4()))
    recipient: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "sender": self.sender,
            "recipient": self.recipient,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentMessage":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            type=MessageType(data.get("type", "text")),
            content=data["content"],
            sender=data.get("sender", "system"),
            recipient=data.get("recipient"),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
        )


@dataclass
class AgentTool:
    """
    A tool that an agent can use.
    
    Attributes:
        name: Tool name (used for invocation)
        description: Human-readable description for the LLM
        parameters: JSON Schema for tool parameters
        handler: The actual function to execute
    """
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]
    
    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


@dataclass
class AgentContext:
    """
    Runtime context provided to agents during execution.
    
    Attributes:
        session_id: Current session identifier
        workspace_path: Path to the user's workspace
        config: Agent-specific configuration
        shared_state: State shared between agents
        message_history: Recent message history
    """
    session_id: str
    workspace_path: Optional[str] = None
    config: dict[str, Any] = field(default_factory=dict)
    shared_state: dict[str, Any] = field(default_factory=dict)
    message_history: list[AgentMessage] = field(default_factory=list)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default."""
        return self.config.get(key, default)
    
    def set_shared(self, key: str, value: Any) -> None:
        """Set a value in shared state."""
        self.shared_state[key] = value
    
    def get_shared(self, key: str, default: Any = None) -> Any:
        """Get a value from shared state."""
        return self.shared_state.get(key, default)


@dataclass
class AgentCapability:
    """Describes a capability an agent provides."""
    name: str
    description: str
    version: str = "1.0.0"


@dataclass
class AgentConfig:
    """
    Configuration for creating/configuring an agent.
    
    Attributes:
        name: Agent name
        description: What this agent does
        system_prompt: System prompt for the LLM
        model: LLM model to use
        temperature: Sampling temperature
        max_tokens: Maximum tokens for responses
    """
    name: str
    description: str = ""
    system_prompt: str = ""
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class AgentMetadata:
    """
    Metadata describing an agent.
    
    Attributes:
        id: Unique agent identifier
        name: Human-readable name
        description: What this agent does
        version: Agent version
        capabilities: List of capabilities
        dependencies: Other agents this one depends on (by ID)
        provides: Resources/data this agent provides to others
    """
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: list[AgentCapability] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)
    author: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": [{"name": c.name, "description": c.description, "version": c.version} for c in self.capabilities],
            "dependencies": self.dependencies,
            "provides": self.provides,
            "author": self.author,
            "tags": self.tags,
        }


class AgentBase(ABC):
    """
    Abstract base class for all agents.
    
    Agents are loaded as plugins and orchestrated by AutoGen.
    Each agent has a specific role and set of capabilities.
    
    Example:
        ```python
        class CodeReviewAgent(AgentBase):
            @property
            def metadata(self) -> AgentMetadata:
                return AgentMetadata(
                    id="code_reviewer",
                    name="Code Reviewer",
                    description="Reviews code for quality and issues"
                )
            
            async def process(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
                # Review the code and return feedback
                ...
        ```
    """
    
    def __init__(self):
        self._status = AgentStatus.IDLE
        self._tools: list[AgentTool] = []
    
    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Return metadata describing this agent."""
        pass
    
    @property
    def status(self) -> AgentStatus:
        """Get the current agent status."""
        return self._status
    
    @status.setter
    def status(self, value: AgentStatus) -> None:
        """Set the agent status."""
        self._status = value
    
    @property
    def tools(self) -> list[AgentTool]:
        """Get the tools available to this agent."""
        return self._tools
    
    def register_tool(self, tool: AgentTool) -> None:
        """Register a tool for this agent to use."""
        self._tools.append(tool)
    
    @abstractmethod
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """
        Process an incoming message and return a response.
        
        Args:
            message: The incoming message to process
            context: Runtime context
            
        Returns:
            Response message
        """
        pass
    
    async def initialize(self, context: AgentContext) -> None:
        """
        Initialize the agent. Called once when the agent is loaded.
        Override to perform setup tasks.
        
        Args:
            context: Runtime context
        """
        pass
    
    async def shutdown(self) -> None:
        """
        Shutdown the agent. Called when the agent is being unloaded.
        Override to perform cleanup tasks.
        """
        self._status = AgentStatus.STOPPED
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Override to customize agent behavior.
        
        Returns:
            System prompt string
        """
        return f"You are {self.metadata.name}. {self.metadata.description}"
    
    async def handle_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: AgentContext,
    ) -> Any:
        """
        Handle a tool call from the LLM.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            context: Runtime context
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        for tool in self._tools:
            if tool.name == tool_name:
                return await tool.handler(**arguments)
        raise ValueError(f"Tool not found: {tool_name}")
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.metadata.id}, status={self.status.value})>"

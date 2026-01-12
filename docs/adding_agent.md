# Adding a New Agent to OMNI

This guide explains how to create and register a new agent in OMNI.

## Overview

Agents in OMNI:
- Implement the `AgentBase` interface
- Are loaded dynamically via the plugin system
- Can use LLM providers and other services
- Must be opt-in (disabled by default is recommended)

## Step 1: Create the Agent File

Create a new file in `backend/agents/`:

```python
# backend/agents/my_agent.py

"""
My Custom Agent

Description of what this agent does.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from backend.core.interfaces.agent import (
    AgentBase,
    AgentMetadata,
    AgentCapability,
    AgentMessage,
    AgentContext,
    MessageType,
    AgentStatus,
)
from backend.core.interfaces.llm import LLMProvider, LLMMessage, LLMRole, LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class MyAgentConfig:
    """Configuration for my agent."""
    option1: str = "default"
    option2: bool = False


class MyAgent(AgentBase):
    """
    My custom agent description.
    
    Explain what this agent does and how to use it.
    """
    
    def __init__(
        self,
        config: Optional[MyAgentConfig] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__()
        self.config = config or MyAgentConfig()
        self._llm = llm_provider
    
    @property
    def metadata(self) -> AgentMetadata:
        """Return agent metadata."""
        return AgentMetadata(
            id="my_agent",  # Unique ID
            name="My Agent",  # Display name
            description="What this agent does",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="capability1",
                    description="Description of capability",
                ),
            ],
            tags=["custom", "example"],
        )
    
    def set_llm(self, provider: LLMProvider) -> None:
        """Set LLM provider (optional)."""
        self._llm = provider
    
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """
        Process incoming message.
        
        This is the main entry point for the agent.
        """
        self.status = AgentStatus.EXECUTING
        
        try:
            content = str(message.content).strip()
            
            # Parse command/intent
            if content.startswith("command1 "):
                return await self._handle_command1(content[9:], context)
            elif content.startswith("command2"):
                return await self._handle_command2(context)
            else:
                return self._error("Unknown command")
        
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return self._error(str(e))
        finally:
            self.status = AgentStatus.IDLE
    
    async def _handle_command1(
        self,
        args: str,
        context: AgentContext,
    ) -> AgentMessage:
        """Handle command1."""
        # Your logic here
        result = f"Processed: {args}"
        
        return AgentMessage(
            content=result,
            type=MessageType.TEXT,
            sender=self.metadata.id,
            metadata={"custom_data": "value"},
        )
    
    async def _handle_command2(self, context: AgentContext) -> AgentMessage:
        """Handle command2."""
        return AgentMessage(
            content="Command2 result",
            type=MessageType.TEXT,
            sender=self.metadata.id,
        )
    
    def _error(self, message: str) -> AgentMessage:
        """Create error response."""
        return AgentMessage(
            content=f"Error: {message}",
            type=MessageType.ERROR,
            sender=self.metadata.id,
        )
```

## Step 2: Register the Agent

### Option A: Auto-discovery (Plugin Directory)

Place your agent in a plugin directory configured in `config/default.yaml`:

```yaml
agents:
  plugin_dirs:
    - "./plugins/agents"
    - "~/.omni/agents"
```

### Option B: Manual Registration

Register in `backend/agents/__init__.py`:

```python
from backend.agents.my_agent import MyAgent

# In the agent loader or registry
registry.register(MyAgent)
```

## Step 3: Add Configuration

Add agent-specific config to `config/default.yaml`:

```yaml
agents:
  my_agent:
    option1: "custom_value"
    option2: true
    enabled: true  # Enable by default or not
```

## Agent Interface Reference

### AgentBase

```python
class AgentBase(ABC):
    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Return agent metadata."""
        pass
    
    @abstractmethod
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Process a message."""
        pass
    
    @property
    def status(self) -> AgentStatus:
        """Get agent status."""
        pass
    
    def register_tool(self, tool: AgentTool) -> None:
        """Register a tool."""
        pass
```

### AgentMetadata

```python
@dataclass
class AgentMetadata:
    id: str  # Unique identifier
    name: str  # Display name
    description: str  # What agent does
    version: str  # Semantic version
    capabilities: list[AgentCapability]  # What agent can do
    tags: list[str] = field(default_factory=list)  # For filtering
    author: str = ""
    config_schema: Optional[dict] = None  # JSON schema for config
```

### AgentMessage

```python
@dataclass
class AgentMessage:
    content: Any  # Message content
    type: MessageType = MessageType.TEXT
    sender: str = "system"
    id: str = field(default_factory=lambda: str(uuid4()))
    recipient: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

### AgentContext

```python
@dataclass
class AgentContext:
    session_id: str
    message_history: list[AgentMessage] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    workspace_path: Optional[str] = None
    user_preferences: dict[str, Any] = field(default_factory=dict)
```

## Best Practices

### 1. Safety First

```python
# If agent should NOT write files:
async def write_file(self, *args, **kwargs) -> None:
    raise PermissionError("This agent cannot write files")
```

### 2. Graceful Degradation

```python
# Handle missing LLM gracefully
if not self._llm:
    return AgentMessage(
        content="LLM not configured - using fallback",
        type=MessageType.TEXT,
        sender=self.metadata.id,
    )
```

### 3. Structured Output

```python
# Return structured data in metadata
return AgentMessage(
    content=human_readable_text,
    type=MessageType.TEXT,
    sender=self.metadata.id,
    metadata={
        "findings": [finding.to_dict() for finding in findings],
        "count": len(findings),
    },
)
```

### 4. Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed debug info")
logger.info("Processing request")
logger.warning("Non-fatal issue")
logger.error("Error occurred")
```

### 5. Configuration

```python
@dataclass
class MyAgentConfig:
    """Use dataclass for type safety."""
    setting1: str = "default"  # Document defaults
    setting2: bool = False
    
    # Validate in __post_init__ if needed
    def __post_init__(self):
        if not self.setting1:
            raise ValueError("setting1 cannot be empty")
```

## Example: Read-Only Agent

```python
class ReadOnlyAgent(AgentBase):
    """Agent that only reads, never writes."""
    
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        # Read file
        content = Path(message.content).read_text()
        
        # Analyze (never write)
        analysis = self._analyze(content)
        
        return AgentMessage(
            content=analysis,
            type=MessageType.TEXT,
            sender=self.metadata.id,
        )
    
    # Block all write operations
    async def write_file(self, *args, **kwargs) -> None:
        raise PermissionError("Read-only agent")
    
    async def modify_file(self, *args, **kwargs) -> None:
        raise PermissionError("Read-only agent")
```

## Example: LLM-Powered Agent

```python
class LLMAgent(AgentBase):
    """Agent that uses LLM for processing."""
    
    def __init__(self, llm_provider: LLMProvider):
        super().__init__()
        self._llm = llm_provider
    
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        # Build messages for LLM
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content="You are a helpful assistant.",
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=str(message.content),
            ),
        ]
        
        # Get response
        response = await self._llm.complete(messages, LLMConfig(
            model=self._llm.default_model,
            temperature=0.7,
        ))
        
        return AgentMessage(
            content=response.content,
            type=MessageType.TEXT,
            sender=self.metadata.id,
        )
```

## Testing Your Agent

```python
# backend/tests/agents/test_my_agent.py

import pytest
from backend.agents.my_agent import MyAgent, MyAgentConfig
from backend.core.interfaces.agent import AgentMessage, AgentContext, MessageType


@pytest.fixture
def agent():
    config = MyAgentConfig()
    return MyAgent(config=config)


@pytest.fixture
def context():
    return AgentContext(session_id="test-session")


@pytest.mark.asyncio
async def test_command1(agent, context):
    message = AgentMessage(
        content="command1 test_arg",
        type=MessageType.TEXT,
        sender="user",
    )
    
    response = await agent.process(message, context)
    
    assert response.type == MessageType.TEXT
    assert "Processed" in response.content


@pytest.mark.asyncio
async def test_unknown_command(agent, context):
    message = AgentMessage(
        content="unknown",
        type=MessageType.TEXT,
        sender="user",
    )
    
    response = await agent.process(message, context)
    
    assert response.type == MessageType.ERROR
```

## Checklist

Before submitting your agent:

- [ ] Implements `AgentBase` interface
- [ ] Has proper `metadata` with unique ID
- [ ] Handles errors gracefully
- [ ] Has configuration dataclass
- [ ] Includes docstrings
- [ ] Has unit tests
- [ ] Follows safety guidelines (no unintended writes)
- [ ] Works without LLM if marked as optional
- [ ] Logging is appropriate level

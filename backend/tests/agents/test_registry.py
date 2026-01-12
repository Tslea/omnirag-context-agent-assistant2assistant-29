"""
Unit Tests for Agent Registry

Tests the AgentRegistry and AgentLoader functionality.

Run:
    pytest backend/tests/agents/test_registry.py -v
"""

import pytest
from typing import Optional

from backend.core.interfaces.agent import (
    AgentBase,
    AgentMessage,
    AgentContext,
    AgentMetadata,
    MessageType,
)
from backend.agents.loader import AgentRegistry


# =============================================================================
# TEST AGENT IMPLEMENTATIONS
# =============================================================================

class TestAgent(AgentBase):
    """A simple test agent for registry tests."""
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="test-agent",
            name="Test Agent",
            description="A test agent",
            version="1.0.0",
        )
    
    async def initialize(self) -> None:
        pass
    
    async def shutdown(self) -> None:
        pass
    
    async def process(
        self,
        message: AgentMessage,
        context: Optional[AgentContext] = None,
    ) -> AgentMessage:
        return AgentMessage(
            content=f"Response from {self.metadata.name}: {message.content}",
            type=MessageType.TEXT,
            sender=self.metadata.id,
        )


class AnotherTestAgent(AgentBase):
    """Another test agent for registry tests."""
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="another-test-agent",
            name="Another Test Agent",
            description="Another test agent",
            version="2.0.0",
        )
    
    async def initialize(self) -> None:
        pass
    
    async def shutdown(self) -> None:
        pass
    
    async def process(
        self,
        message: AgentMessage,
        context: Optional[AgentContext] = None,
    ) -> AgentMessage:
        return AgentMessage(
            content=f"Another response: {message.content}",
            type=MessageType.TEXT,
            sender=self.metadata.id,
        )


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def registry() -> AgentRegistry:
    """Create a fresh AgentRegistry instance."""
    return AgentRegistry()


# =============================================================================
# TESTS
# =============================================================================

class TestAgentRegistryRegister:
    """Tests for agent registration functionality."""
    
    def test_register_agent_class(self, registry: AgentRegistry):
        """Should register an agent class."""
        registry.register(TestAgent)
        
        assert "test-agent" in registry.list_agents()
    
    def test_register_multiple_agents(self, registry: AgentRegistry):
        """Should register multiple agent classes."""
        registry.register(TestAgent)
        registry.register(AnotherTestAgent)
        
        agents = registry.list_agents()
        assert "test-agent" in agents
        assert "another-test-agent" in agents
    
    def test_register_duplicate_raises_error(self, registry: AgentRegistry):
        """Should raise error when registering duplicate agent."""
        registry.register(TestAgent)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(TestAgent)
    
    def test_register_with_custom_name(self, registry: AgentRegistry):
        """Should allow registering with custom name."""
        registry.register(TestAgent, name="custom-name")
        
        assert "custom-name" in registry.list_agents()
        assert "test-agent" not in registry.list_agents()


class TestAgentRegistryGet:
    """Tests for retrieving agents from registry."""
    
    def test_get_registered_agent(self, registry: AgentRegistry):
        """Should return agent instance for registered agent."""
        registry.register(TestAgent)
        
        agent = registry.get("test-agent")
        
        assert agent is not None
        assert isinstance(agent, TestAgent)
    
    def test_get_unregistered_agent_returns_none(self, registry: AgentRegistry):
        """Should return None for unregistered agent."""
        agent = registry.get("nonexistent-agent")
        
        assert agent is None
    
    def test_get_creates_new_instance(self, registry: AgentRegistry):
        """Should create new instance each time get is called."""
        registry.register(TestAgent)
        
        agent1 = registry.get("test-agent")
        agent2 = registry.get("test-agent")
        
        assert agent1 is not agent2


class TestAgentRegistryUnregister:
    """Tests for unregistering agents."""
    
    def test_unregister_agent(self, registry: AgentRegistry):
        """Should remove agent from registry."""
        registry.register(TestAgent)
        
        registry.unregister("test-agent")
        
        assert "test-agent" not in registry.list_agents()
    
    def test_unregister_nonexistent_agent(self, registry: AgentRegistry):
        """Should not raise error when unregistering nonexistent agent."""
        # Should not raise
        result = registry.unregister("nonexistent")
        
        assert result is False


class TestAgentRegistryEnableDisable:
    """Tests for enabling/disabling agents."""
    
    def test_agent_enabled_by_default(self, registry: AgentRegistry):
        """Newly registered agents should be enabled by default."""
        registry.register(TestAgent)
        
        assert registry.is_enabled("test-agent") is True
    
    def test_disable_agent(self, registry: AgentRegistry):
        """Should disable an agent."""
        registry.register(TestAgent)
        
        registry.disable("test-agent")
        
        assert registry.is_enabled("test-agent") is False
    
    def test_enable_disabled_agent(self, registry: AgentRegistry):
        """Should re-enable a disabled agent."""
        registry.register(TestAgent)
        registry.disable("test-agent")
        
        registry.enable("test-agent")
        
        assert registry.is_enabled("test-agent") is True
    
    def test_get_disabled_agent_returns_none(self, registry: AgentRegistry):
        """Should return None when getting a disabled agent."""
        registry.register(TestAgent)
        registry.disable("test-agent")
        
        agent = registry.get("test-agent")
        
        assert agent is None
    
    def test_list_only_enabled_agents(self, registry: AgentRegistry):
        """Should optionally list only enabled agents."""
        registry.register(TestAgent)
        registry.register(AnotherTestAgent)
        registry.disable("test-agent")
        
        enabled_agents = registry.list_agents(enabled_only=True)
        
        assert "test-agent" not in enabled_agents
        assert "another-test-agent" in enabled_agents
    
    def test_list_all_agents(self, registry: AgentRegistry):
        """Should list all agents regardless of enabled state."""
        registry.register(TestAgent)
        registry.register(AnotherTestAgent)
        registry.disable("test-agent")
        
        all_agents = registry.list_agents(enabled_only=False)
        
        assert "test-agent" in all_agents
        assert "another-test-agent" in all_agents


class TestAgentRegistryInfo:
    """Tests for getting agent information."""
    
    def test_get_agent_info(self, registry: AgentRegistry):
        """Should return agent metadata."""
        registry.register(TestAgent)
        
        info = registry.get_info("test-agent")
        
        assert info is not None
        assert info["name"] == "test-agent"
        assert info["description"] == "A test agent"
        assert info["version"] == "1.0.0"
    
    def test_get_info_nonexistent_returns_none(self, registry: AgentRegistry):
        """Should return None for nonexistent agent."""
        info = registry.get_info("nonexistent")
        
        assert info is None
    
    def test_get_all_agent_info(self, registry: AgentRegistry):
        """Should return info for all registered agents."""
        registry.register(TestAgent)
        registry.register(AnotherTestAgent)
        
        all_info = registry.get_all_info()
        
        assert len(all_info) == 2
        names = [info["name"] for info in all_info]
        assert "test-agent" in names
        assert "another-test-agent" in names

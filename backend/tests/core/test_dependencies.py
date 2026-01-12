"""
Tests for Agent Dependency Management

Tests dependency graph, validation, and topological sorting.
"""

import pytest
from dataclasses import dataclass
from typing import Any

from backend.core.dependencies import (
    DependencyGraph,
    DependencyStatus,
    DependencyInfo,
    MissingDependencyError,
    CircularDependencyError,
    DependencyValidationError,
    validate_dependencies,
    get_initialization_order,
)
from backend.core.interfaces.agent import (
    AgentBase,
    AgentMetadata,
    AgentMessage,
    AgentContext,
)


# === Test Fixtures ===

class MockAgent(AgentBase):
    """Mock agent for testing."""
    
    def __init__(
        self,
        agent_id: str,
        dependencies: list[str] = None,
        provides: list[str] = None,
    ):
        super().__init__()
        self._id = agent_id
        self._dependencies = dependencies or []
        self._provides = provides or []
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id=self._id,
            name=f"{self._id.title()} Agent",
            description=f"Mock agent {self._id}",
            dependencies=self._dependencies,
            provides=self._provides,
        )
    
    async def process(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        return AgentMessage(content="ok", sender=self._id)


class TestDependencyGraph:
    """Tests for DependencyGraph."""
    
    def test_add_agent(self):
        """Should add agent to graph."""
        graph = DependencyGraph()
        agent = MockAgent("security", dependencies=["context"], provides=["findings"])
        
        graph.add_agent(agent)
        
        assert "security" in graph.dependencies
        assert graph.dependencies["security"] == ["context"]
        assert graph.provides["security"] == ["findings"]
    
    def test_get_dependencies(self):
        """Should get dependencies for agent."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a", dependencies=["b", "c"]))
        
        assert graph.get_dependencies("a") == ["b", "c"]
        assert graph.get_dependencies("nonexistent") == []
    
    def test_get_dependents(self):
        """Should get agents that depend on given agent."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("context"))
        graph.add_agent(MockAgent("security", dependencies=["context"]))
        graph.add_agent(MockAgent("compliance", dependencies=["context"]))
        graph.add_agent(MockAgent("coding"))
        
        dependents = graph.get_dependents("context")
        
        assert set(dependents) == {"security", "compliance"}
    
    def test_get_provides(self):
        """Should get resources provided by agent."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("context", provides=["project_structure", "summary"]))
        
        assert graph.get_provides("context") == ["project_structure", "summary"]


class TestDependencyValidation:
    """Tests for dependency validation."""
    
    def test_valid_dependencies(self):
        """Should pass validation when all deps satisfied."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("context"))
        graph.add_agent(MockAgent("rag"))
        graph.add_agent(MockAgent("security", dependencies=["context", "rag"]))
        
        errors = graph.validate()
        
        assert errors == []
    
    def test_missing_dependency(self):
        """Should detect missing dependencies."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("security", dependencies=["context", "missing_agent"]))
        graph.add_agent(MockAgent("context"))
        
        errors = graph.validate()
        
        assert len(errors) == 1
        assert "missing_agent" in errors[0]
    
    def test_validate_strict_raises(self):
        """Should raise on validation failure."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("security", dependencies=["missing"]))
        
        with pytest.raises(DependencyValidationError) as exc:
            graph.validate_strict()
        
        assert "missing" in str(exc.value)
    
    def test_find_missing_dependencies(self):
        """Should find all missing deps for agent."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("security", dependencies=["a", "b", "c"]))
        graph.add_agent(MockAgent("a"))
        
        missing = graph.find_missing_dependencies("security")
        
        assert set(missing) == {"b", "c"}


class TestCircularDependencies:
    """Tests for circular dependency detection."""
    
    def test_no_cycles(self):
        """Should return None when no cycles."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a"))
        graph.add_agent(MockAgent("b", dependencies=["a"]))
        graph.add_agent(MockAgent("c", dependencies=["b"]))
        
        cycle = graph.detect_cycles()
        
        assert cycle is None
    
    def test_simple_cycle(self):
        """Should detect simple A -> B -> A cycle."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a", dependencies=["b"]))
        graph.add_agent(MockAgent("b", dependencies=["a"]))
        
        cycle = graph.detect_cycles()
        
        assert cycle is not None
        assert set(cycle) == {"a", "b"}
    
    def test_longer_cycle(self):
        """Should detect longer cycles."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a", dependencies=["b"]))
        graph.add_agent(MockAgent("b", dependencies=["c"]))
        graph.add_agent(MockAgent("c", dependencies=["a"]))
        
        cycle = graph.detect_cycles()
        
        assert cycle is not None
        assert len(cycle) == 3
    
    def test_self_dependency(self):
        """Should detect self-dependency as cycle."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a", dependencies=["a"]))
        
        cycle = graph.detect_cycles()
        
        assert cycle is not None
        assert "a" in cycle


class TestTopologicalSort:
    """Tests for initialization order."""
    
    def test_simple_order(self):
        """Should return correct initialization order."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("context"))
        graph.add_agent(MockAgent("rag"))
        graph.add_agent(MockAgent("security", dependencies=["context", "rag"]))
        
        order = graph.topological_sort()
        
        # context and rag should come before security
        assert order.index("context") < order.index("security")
        assert order.index("rag") < order.index("security")
    
    def test_complex_order(self):
        """Should handle complex dependency graph."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("context"))
        graph.add_agent(MockAgent("rag"))
        graph.add_agent(MockAgent("security", dependencies=["context", "rag"]))
        graph.add_agent(MockAgent("compliance", dependencies=["context", "rag"]))
        graph.add_agent(MockAgent("coding", dependencies=["context", "rag", "security"]))
        
        order = graph.topological_sort()
        
        # Verify all ordering constraints
        assert order.index("context") < order.index("security")
        assert order.index("context") < order.index("compliance")
        assert order.index("context") < order.index("coding")
        assert order.index("rag") < order.index("security")
        assert order.index("security") < order.index("coding")
    
    def test_topological_sort_raises_on_cycle(self):
        """Should raise on circular dependencies."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a", dependencies=["b"]))
        graph.add_agent(MockAgent("b", dependencies=["a"]))
        
        with pytest.raises(CircularDependencyError):
            graph.topological_sort()
    
    def test_get_initialization_order_alias(self):
        """get_initialization_order should work like topological_sort."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a"))
        graph.add_agent(MockAgent("b", dependencies=["a"]))
        
        order = graph.get_initialization_order()
        
        assert order.index("a") < order.index("b")


class TestTransitiveDependencies:
    """Tests for transitive dependency resolution."""
    
    def test_get_all_transitive_dependencies(self):
        """Should get all transitive deps."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a"))
        graph.add_agent(MockAgent("b", dependencies=["a"]))
        graph.add_agent(MockAgent("c", dependencies=["b"]))
        graph.add_agent(MockAgent("d", dependencies=["c"]))
        
        all_deps = graph.get_all_transitive_dependencies("d")
        
        assert all_deps == {"a", "b", "c"}
    
    def test_transitive_with_diamond(self):
        """Should handle diamond dependencies."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a"))
        graph.add_agent(MockAgent("b", dependencies=["a"]))
        graph.add_agent(MockAgent("c", dependencies=["a"]))
        graph.add_agent(MockAgent("d", dependencies=["b", "c"]))
        
        all_deps = graph.get_all_transitive_dependencies("d")
        
        assert all_deps == {"a", "b", "c"}


class TestDependencyVisualization:
    """Tests for dependency visualization."""
    
    def test_to_mermaid(self):
        """Should generate valid Mermaid diagram."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("context", provides=["project_structure"]))
        graph.add_agent(MockAgent("security", dependencies=["context"]))
        
        mermaid = graph.to_mermaid()
        
        assert "graph TD" in mermaid
        assert "context" in mermaid
        assert "security" in mermaid
        assert "context --> security" in mermaid
    
    def test_to_dot(self):
        """Should generate valid DOT diagram."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("a"))
        graph.add_agent(MockAgent("b", dependencies=["a"]))
        
        dot = graph.to_dot()
        
        assert "digraph" in dot
        assert '"a"' in dot
        assert '"b"' in dot
        assert '"a" -> "b"' in dot


class TestDependencyInfo:
    """Tests for detailed dependency info."""
    
    def test_get_dependency_info(self):
        """Should get detailed dependency info."""
        graph = DependencyGraph()
        graph.add_agent(MockAgent("context", provides=["project_structure"]))
        graph.add_agent(MockAgent("security", dependencies=["context", "missing"]))
        
        info = graph.get_dependency_info()
        
        assert "security" in info
        assert len(info["security"]) == 2
        
        # Find context dependency
        ctx_info = next(i for i in info["security"] if i.agent_id == "context")
        assert ctx_info.status == DependencyStatus.SATISFIED
        assert ctx_info.provided_resources == ["project_structure"]
        
        # Find missing dependency
        missing_info = next(i for i in info["security"] if i.agent_id == "missing")
        assert missing_info.status == DependencyStatus.MISSING


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_validate_dependencies_function(self):
        """Should validate and return graph."""
        agents = [
            MockAgent("context"),
            MockAgent("security", dependencies=["context"]),
        ]
        
        graph = validate_dependencies(agents)
        
        assert isinstance(graph, DependencyGraph)
        assert len(graph.dependencies) == 2
    
    def test_validate_dependencies_raises(self):
        """Should raise on invalid deps."""
        agents = [
            MockAgent("security", dependencies=["missing"]),
        ]
        
        with pytest.raises(DependencyValidationError):
            validate_dependencies(agents)
    
    def test_get_initialization_order_function(self):
        """Should return init order from agents."""
        agents = [
            MockAgent("context"),
            MockAgent("security", dependencies=["context"]),
        ]
        
        order = get_initialization_order(agents)
        
        assert order.index("context") < order.index("security")


class TestRealAgents:
    """Tests with real OMNI agents."""
    
    def test_omni_agent_dependencies(self):
        """Test that OMNI agents have valid dependencies."""
        # Import real agents
        from backend.agents.context_agent import ContextAgent
        from backend.agents.rag_agent import RAGAgent
        from backend.agents.security_agent import SecurityAgent
        from backend.agents.compliance_agent import ComplianceAgent
        from backend.agents.coding_agent import CodingAgent
        
        # Create instances (without full initialization)
        context = ContextAgent()
        rag = RAGAgent()
        security = SecurityAgent()
        compliance = ComplianceAgent()
        coding = CodingAgent()
        
        # Build graph
        graph = DependencyGraph()
        for agent in [context, rag, security, compliance, coding]:
            graph.add_agent(agent)
        
        # Validate - should pass
        errors = graph.validate()
        assert errors == [], f"Validation errors: {errors}"
        
        # Get init order
        order = graph.get_initialization_order()
        
        # context and rag should come first (no deps)
        assert "context_agent" in order[:2] or "rag_agent" in order[:2]
        
        # security, compliance, coding depend on context and rag
        for agent_id in ["security", "compliance", "coding"]:
            assert order.index("context_agent") < order.index(agent_id)
            assert order.index("rag_agent") < order.index(agent_id)

"""
Agent Dependency Management

Validates and manages dependencies between agents.
Provides dependency graph visualization and topological sorting.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .interfaces.agent import AgentBase, AgentMetadata


class DependencyError(Exception):
    """Base exception for dependency-related errors."""
    pass


class MissingDependencyError(DependencyError):
    """Raised when a required dependency is missing."""
    def __init__(self, agent_id: str, missing_deps: list[str]):
        self.agent_id = agent_id
        self.missing_deps = missing_deps
        super().__init__(
            f"Agent '{agent_id}' is missing required dependencies: {', '.join(missing_deps)}"
        )


class CircularDependencyError(DependencyError):
    """Raised when circular dependencies are detected."""
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle + [cycle[0]])  # Show the cycle closing
        super().__init__(f"Circular dependency detected: {cycle_str}")


class DependencyValidationError(DependencyError):
    """Raised when dependency validation fails."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Dependency validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


class DependencyStatus(str, Enum):
    """Status of a dependency."""
    SATISFIED = "satisfied"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"


@dataclass
class DependencyInfo:
    """Information about a single dependency."""
    agent_id: str
    required_by: str
    status: DependencyStatus
    provided_resources: list[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    """
    Represents the dependency graph between agents.
    
    Provides methods for:
    - Validating all dependencies are satisfied
    - Detecting circular dependencies
    - Computing initialization order (topological sort)
    - Generating dependency visualization
    """
    
    # agent_id -> list of agent_ids it depends on
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    # agent_id -> list of resources it provides
    provides: dict[str, list[str]] = field(default_factory=dict)
    # agent_id -> AgentMetadata
    metadata: dict[str, "AgentMetadata"] = field(default_factory=dict)
    
    def add_agent(self, agent: "AgentBase") -> None:
        """Add an agent to the dependency graph."""
        meta = agent.metadata
        self.dependencies[meta.id] = list(meta.dependencies)
        self.provides[meta.id] = list(meta.provides)
        self.metadata[meta.id] = meta
    
    def add_agent_metadata(self, meta: "AgentMetadata") -> None:
        """Add agent metadata directly to the graph."""
        self.dependencies[meta.id] = list(meta.dependencies)
        self.provides[meta.id] = list(meta.provides)
        self.metadata[meta.id] = meta
    
    def get_dependencies(self, agent_id: str) -> list[str]:
        """Get the dependencies for an agent."""
        return self.dependencies.get(agent_id, [])
    
    def get_dependents(self, agent_id: str) -> list[str]:
        """Get agents that depend on the given agent."""
        return [
            aid for aid, deps in self.dependencies.items()
            if agent_id in deps
        ]
    
    def get_provides(self, agent_id: str) -> list[str]:
        """Get resources provided by an agent."""
        return self.provides.get(agent_id, [])
    
    def validate(self) -> list[str]:
        """
        Validate the dependency graph.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors: list[str] = []
        all_agent_ids = set(self.dependencies.keys())
        
        # Check for missing dependencies
        for agent_id, deps in self.dependencies.items():
            for dep in deps:
                if dep not in all_agent_ids:
                    errors.append(
                        f"Agent '{agent_id}' depends on '{dep}' which is not registered"
                    )
        
        # Check for circular dependencies
        try:
            self.topological_sort()
        except CircularDependencyError as e:
            errors.append(str(e))
        
        return errors
    
    def validate_strict(self) -> None:
        """
        Validate and raise if invalid.
        
        Raises:
            DependencyValidationError: If validation fails
        """
        errors = self.validate()
        if errors:
            raise DependencyValidationError(errors)
    
    def find_missing_dependencies(self, agent_id: str) -> list[str]:
        """Find any missing dependencies for an agent."""
        all_agent_ids = set(self.dependencies.keys())
        deps = self.dependencies.get(agent_id, [])
        return [d for d in deps if d not in all_agent_ids]
    
    def detect_cycles(self) -> Optional[list[str]]:
        """
        Detect any circular dependencies.
        
        Returns:
            List of agent IDs forming a cycle, or None if no cycles
        """
        # Use DFS with coloring: WHITE (0), GRAY (1), BLACK (2)
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {aid: WHITE for aid in self.dependencies}
        parent = {aid: None for aid in self.dependencies}
        
        def dfs(node: str) -> Optional[list[str]]:
            color[node] = GRAY
            for neighbor in self.dependencies.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    # Found cycle - reconstruct it
                    cycle = [neighbor]
                    curr = node
                    while curr != neighbor:
                        cycle.append(curr)
                        curr = parent[curr]
                        if curr is None:
                            break
                    return list(reversed(cycle))
                elif color[neighbor] == WHITE:
                    parent[neighbor] = node
                    result = dfs(neighbor)
                    if result:
                        return result
            color[node] = BLACK
            return None
        
        for agent_id in self.dependencies:
            if color[agent_id] == WHITE:
                result = dfs(agent_id)
                if result:
                    return result
        return None
    
    def topological_sort(self) -> list[str]:
        """
        Return agents in initialization order (topological sort).
        
        Agents with no dependencies come first, then agents
        whose dependencies are already satisfied.
        
        Returns:
            List of agent IDs in initialization order
            
        Raises:
            CircularDependencyError: If circular dependencies exist
        """
        # Kahn's algorithm
        # in_degree[x] = number of agents that x depends on (that haven't been processed)
        in_degree = {aid: len([d for d in deps if d in self.dependencies]) 
                     for aid, deps in self.dependencies.items()}
        
        # Start with nodes that have no dependencies (in_degree = 0)
        queue = [aid for aid, deg in in_degree.items() if deg == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # For each agent that depends on this node, reduce their in_degree
            for dependent in self.get_dependents(node):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.dependencies):
            # Not all nodes visited - must have a cycle
            cycle = self.detect_cycles()
            if cycle:
                raise CircularDependencyError(cycle)
            # Fallback: list remaining nodes
            remaining = [aid for aid in self.dependencies if aid not in result]
            raise CircularDependencyError(remaining)
        
        return result
    
    def get_initialization_order(self) -> list[str]:
        """
        Get the order in which agents should be initialized.
        
        Alias for topological_sort() with clearer name.
        
        Returns:
            List of agent IDs in initialization order
        """
        return self.topological_sort()
    
    def to_mermaid(self) -> str:
        """
        Generate a Mermaid diagram of the dependency graph.
        
        Returns:
            Mermaid flowchart syntax
        """
        lines = ["graph TD"]
        
        # Add nodes with labels
        for agent_id, meta in self.metadata.items():
            provides = self.provides.get(agent_id, [])
            if provides:
                provides_str = f"<br/>Provides: {', '.join(provides)}"
            else:
                provides_str = ""
            lines.append(f'    {agent_id}["{meta.name}{provides_str}"]')
        
        # Add edges
        for agent_id, deps in self.dependencies.items():
            for dep in deps:
                lines.append(f"    {dep} --> {agent_id}")
        
        return "\n".join(lines)
    
    def to_dot(self) -> str:
        """
        Generate a DOT diagram of the dependency graph.
        
        Returns:
            DOT graph syntax
        """
        lines = ["digraph DependencyGraph {"]
        lines.append("    rankdir=TB;")
        lines.append("    node [shape=box];")
        
        # Add nodes
        for agent_id, meta in self.metadata.items():
            label = meta.name.replace('"', '\\"')
            lines.append(f'    "{agent_id}" [label="{label}"];')
        
        # Add edges
        for agent_id, deps in self.dependencies.items():
            for dep in deps:
                lines.append(f'    "{dep}" -> "{agent_id}";')
        
        lines.append("}")
        return "\n".join(lines)
    
    def get_all_transitive_dependencies(self, agent_id: str) -> set[str]:
        """
        Get all dependencies (direct and transitive) for an agent.
        
        Returns:
            Set of all agent IDs this agent depends on
        """
        visited = set()
        stack = list(self.dependencies.get(agent_id, []))
        
        while stack:
            dep = stack.pop()
            if dep not in visited:
                visited.add(dep)
                stack.extend(self.dependencies.get(dep, []))
        
        return visited
    
    def get_dependency_info(self) -> dict[str, list[DependencyInfo]]:
        """
        Get detailed dependency information for all agents.
        
        Returns:
            Dict mapping agent_id to list of DependencyInfo
        """
        all_agent_ids = set(self.dependencies.keys())
        result: dict[str, list[DependencyInfo]] = {}
        
        for agent_id, deps in self.dependencies.items():
            info_list = []
            for dep in deps:
                if dep in all_agent_ids:
                    status = DependencyStatus.SATISFIED
                    provided = self.provides.get(dep, [])
                else:
                    status = DependencyStatus.MISSING
                    provided = []
                
                info_list.append(DependencyInfo(
                    agent_id=dep,
                    required_by=agent_id,
                    status=status,
                    provided_resources=provided,
                ))
            result[agent_id] = info_list
        
        return result


def validate_dependencies(agents: list["AgentBase"]) -> DependencyGraph:
    """
    Create and validate a dependency graph from a list of agents.
    
    Args:
        agents: List of agent instances
        
    Returns:
        Validated DependencyGraph
        
    Raises:
        DependencyValidationError: If validation fails
    """
    graph = DependencyGraph()
    for agent in agents:
        graph.add_agent(agent)
    
    graph.validate_strict()
    return graph


def get_initialization_order(agents: list["AgentBase"]) -> list[str]:
    """
    Get the initialization order for a list of agents.
    
    Convenience function that creates a graph and returns the order.
    
    Args:
        agents: List of agent instances
        
    Returns:
        List of agent IDs in initialization order
    """
    graph = DependencyGraph()
    for agent in agents:
        graph.add_agent(agent)
    return graph.get_initialization_order()

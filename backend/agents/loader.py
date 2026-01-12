"""
Agent Loader and Registry

Handles dynamic loading of agent plugins and registration.
"""

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Optional, Type

from backend.core.interfaces.agent import AgentBase, AgentMetadata


class AgentRegistry:
    """
    Registry for agent plugins.
    
    Maintains a catalog of available agents and their metadata.
    Supports enabling/disabling agents without removing them.
    
    Example:
        ```python
        registry = AgentRegistry()
        registry.register(MyCustomAgent)
        
        agent_class = registry.get("my_custom_agent")
        agent = agent_class()
        
        # Disable agent
        registry.disable("my_custom_agent")
        ```
    """
    
    def __init__(self):
        self._agents: dict[str, Type[AgentBase]] = {}
        self._metadata: dict[str, AgentMetadata] = {}
        self._enabled: dict[str, bool] = {}
    
    def register(
        self,
        agent_class: Type[AgentBase],
        name: Optional[str] = None,
    ) -> None:
        """
        Register an agent class.
        
        Args:
            agent_class: Agent class to register
            name: Optional custom name (uses class name/id if not provided)
            
        Raises:
            ValueError: If agent with this name is already registered
        """
        # Create temporary instance to get metadata
        temp_instance = agent_class()
        metadata = temp_instance.metadata
        
        agent_id = name or metadata.id
        
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' is already registered")
        
        self._agents[agent_id] = agent_class
        self._metadata[agent_id] = metadata
        self._enabled[agent_id] = True
    
    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            agent_id: ID of agent to unregister
            
        Returns:
            True if unregistered, False if not found
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            del self._metadata[agent_id]
            del self._enabled[agent_id]
            return True
        return False
    
    def enable(self, agent_id: str) -> None:
        """
        Enable an agent.
        
        Args:
            agent_id: ID of agent to enable
        """
        if agent_id in self._agents:
            self._enabled[agent_id] = True
    
    def disable(self, agent_id: str) -> None:
        """
        Disable an agent without removing it.
        
        Args:
            agent_id: ID of agent to disable
        """
        if agent_id in self._agents:
            self._enabled[agent_id] = False
    
    def is_enabled(self, agent_id: str) -> bool:
        """
        Check if an agent is enabled.
        
        Args:
            agent_id: ID of agent to check
            
        Returns:
            True if enabled, False if disabled or not found
        """
        return self._enabled.get(agent_id, False)
    
    def get(
        self,
        agent_id: str,
        config: Optional[Any] = None,
    ) -> Optional[AgentBase]:
        """
        Get an agent instance by ID.
        
        Args:
            agent_id: ID of agent to get
            config: Optional configuration for the agent
            
        Returns:
            Agent instance or None if not found or disabled
        """
        if agent_id not in self._agents:
            return None
        
        if not self._enabled.get(agent_id, True):
            return None
        
        agent_class = self._agents[agent_id]
        return agent_class(config) if config else agent_class()
    
    def get_class(self, agent_id: str) -> Optional[Type[AgentBase]]:
        """Get an agent class by ID (regardless of enabled state)."""
        return self._agents.get(agent_id)
    
    def get_metadata(self, agent_id: str) -> Optional[AgentMetadata]:
        """Get agent metadata by ID."""
        return self._metadata.get(agent_id)
    
    def get_info(self, agent_id: str) -> Optional[dict]:
        """
        Get agent information as a dictionary.
        
        Args:
            agent_id: ID of agent
            
        Returns:
            Dictionary with agent info or None if not found
        """
        metadata = self._metadata.get(agent_id)
        if not metadata:
            return None
        
        return {
            "name": agent_id,
            "description": metadata.description,
            "version": metadata.version,
            "enabled": self._enabled.get(agent_id, True),
        }
    
    def get_all_info(self) -> list[dict]:
        """Get info for all registered agents."""
        return [
            self.get_info(agent_id)
            for agent_id in self._agents
            if self.get_info(agent_id) is not None
        ]
    
    def list_agents(self, enabled_only: bool = False) -> list[str]:
        """
        List all registered agent IDs.
        
        Args:
            enabled_only: If True, only return enabled agents
            
        Returns:
            List of agent IDs
        """
        if enabled_only:
            return [
                agent_id
                for agent_id in self._agents
                if self._enabled.get(agent_id, True)
            ]
        return list(self._agents.keys())
    
    def list_metadata(self) -> list[AgentMetadata]:
        """List all registered agents metadata."""
        return list(self._metadata.values())
    
    def has(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        return agent_id in self._agents
    
    def create_instance(self, agent_id: str) -> Optional[AgentBase]:
        """
        Create an instance of a registered agent.
        
        Args:
            agent_id: ID of agent to instantiate
            
        Returns:
            New agent instance or None if not found
        """
        agent_class = self.get_class(agent_id)
        if agent_class:
            return agent_class()
        return None
    
    def find_by_capability(self, capability: str) -> list[AgentMetadata]:
        """
        Find agents that have a specific capability.
        
        Args:
            capability: Capability name to search for
            
        Returns:
            List of agent metadata with that capability
        """
        results = []
        for metadata in self._metadata.values():
            if any(cap.name == capability for cap in metadata.capabilities):
                results.append(metadata)
        return results
    
    def find_by_tag(self, tag: str) -> list[AgentMetadata]:
        """
        Find agents with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of agent metadata with that tag
        """
        return [m for m in self._metadata.values() if tag in m.tags]


class AgentLoader:
    """
    Dynamic agent plugin loader.
    
    Loads agent plugins from:
    - Built-in agents directory
    - Custom plugin directories
    - Python modules
    
    Example:
        ```python
        loader = AgentLoader(registry)
        
        # Load built-in agents
        loader.load_builtin_agents()
        
        # Load from custom directory
        loader.load_from_directory("./my_agents")
        
        # Load specific module
        loader.load_module("my_package.agents.custom")
        ```
    """
    
    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or AgentRegistry()
        self._loaded_modules: set[str] = set()
    
    def load_builtin_agents(self) -> int:
        """
        Load all built-in agents.
        
        Returns:
            Number of agents loaded
        """
        from backend.agents.base_agents import (
            AssistantAgent,
            CodeAgent,
            PlannerAgent,
        )
        from backend.agents.security_agent import SecurityAgent
        from backend.agents.compliance_agent import ComplianceAgent
        from backend.agents.context_agent import ContextAgent
        from backend.agents.rag_agent import RAGAgent
        
        count = 0
        for agent_class in [
            AssistantAgent, 
            CodeAgent, 
            PlannerAgent,
            SecurityAgent,
            ComplianceAgent,
            ContextAgent,
            RAGAgent,
        ]:
            try:
                self.registry.register(agent_class)
                count += 1
            except Exception as e:
                pass
        
        return count
    
    def load_from_directory(self, directory: str) -> int:
        """
        Load all agent plugins from a directory.
        
        Looks for Python files with classes that inherit from AgentBase.
        
        Args:
            directory: Path to directory containing agent modules
            
        Returns:
            Number of agents loaded
        """
        path = Path(directory)
        if not path.exists():
            return 0
        
        count = 0
        for file in path.glob("*.py"):
            if file.name.startswith("_"):
                continue
            
            try:
                loaded = self.load_file(str(file))
                count += loaded
            except Exception:
                continue
        
        return count
    
    def load_file(self, file_path: str) -> int:
        """
        Load agents from a specific Python file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Number of agents loaded
        """
        path = Path(file_path)
        if not path.exists() or not path.suffix == ".py":
            return 0
        
        module_name = f"omni_agent_plugin_{path.stem}"
        
        if module_name in self._loaded_modules:
            return 0
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                return 0
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            self._loaded_modules.add(module_name)
            
            return self._register_agents_from_module(module)
            
        except Exception:
            return 0
    
    def load_module(self, module_name: str) -> int:
        """
        Load agents from an installed Python module.
        
        Args:
            module_name: Full module path (e.g., "my_package.agents")
            
        Returns:
            Number of agents loaded
        """
        if module_name in self._loaded_modules:
            return 0
        
        try:
            module = importlib.import_module(module_name)
            self._loaded_modules.add(module_name)
            return self._register_agents_from_module(module)
        except ImportError:
            return 0
    
    def _register_agents_from_module(self, module: Any) -> int:
        """
        Find and register all AgentBase subclasses in a module.
        
        Args:
            module: Python module to scan
            
        Returns:
            Number of agents registered
        """
        count = 0
        
        for name in dir(module):
            if name.startswith("_"):
                continue
            
            obj = getattr(module, name)
            
            # Check if it's a class that inherits from AgentBase
            if (
                isinstance(obj, type)
                and issubclass(obj, AgentBase)
                and obj is not AgentBase
            ):
                try:
                    self.registry.register(obj)
                    count += 1
                except Exception:
                    continue
        
        return count
    
    def reload_agent(self, agent_id: str, file_path: str) -> bool:
        """
        Reload a specific agent from file.
        
        Useful for hot-reloading during development.
        
        Args:
            agent_id: ID of agent to reload
            file_path: Path to agent file
            
        Returns:
            True if reloaded successfully
        """
        # Unregister existing
        self.registry.unregister(agent_id)
        
        # Remove from loaded modules tracking
        path = Path(file_path)
        module_name = f"omni_agent_plugin_{path.stem}"
        self._loaded_modules.discard(module_name)
        
        # Reload
        loaded = self.load_file(file_path)
        return loaded > 0 and self.registry.has(agent_id)
    
    def discover_plugins(self, search_paths: list[str]) -> dict[str, list[str]]:
        """
        Discover available agent plugins without loading them.
        
        Args:
            search_paths: List of directories to search
            
        Returns:
            Dict mapping directory to list of agent file paths
        """
        discovered: dict[str, list[str]] = {}
        
        for search_path in search_paths:
            path = Path(search_path)
            if not path.exists():
                continue
            
            discovered[search_path] = []
            
            for file in path.glob("*.py"):
                if file.name.startswith("_"):
                    continue
                
                # Quick check if file contains AgentBase
                try:
                    content = file.read_text()
                    if "AgentBase" in content or "from backend.core" in content:
                        discovered[search_path].append(str(file))
                except Exception:
                    continue
        
        return discovered

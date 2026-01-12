"""
Agent Orchestrator

Coordinates multiple agents using AutoGen patterns.
"""

import asyncio
import logging
from typing import Any, Callable, Optional
from uuid import uuid4

from backend.core.interfaces.agent import (
    AgentBase,
    AgentMessage,
    AgentContext,
    MessageType,
    AgentStatus,
)
from backend.core.interfaces.llm import LLMProvider
from backend.core.exceptions import (
    AgentError,
    AgentNotFoundError,
    AgentTimeoutError,
    WorkflowError,
    ErrorContext,
    is_recoverable,
    wrap_exception,
)
from backend.core.retry import (
    retry_async,
    RetryConfig,
    RETRY_FAST,
    RETRY_STANDARD,
)
from backend.agents.loader import AgentRegistry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates multi-agent conversations and workflows.
    
    Supports various patterns:
    - Sequential: Agents respond in order
    - Round-robin: Agents take turns
    - Selector: An agent selects the next speaker
    - Broadcast: All agents respond to a message
    
    Example:
        ```python
        orchestrator = AgentOrchestrator(registry, llm_provider)
        
        # Add agents to conversation
        orchestrator.add_agent("assistant")
        orchestrator.add_agent("code_agent")
        
        # Run conversation
        result = await orchestrator.run(
            initial_message="Help me write a Python function",
            max_turns=5
        )
        ```
    """
    
    def __init__(
        self,
        registry: AgentRegistry,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.registry = registry
        self.llm_provider = llm_provider
        self._agents: dict[str, AgentBase] = {}
        self._message_history: list[AgentMessage] = []
        self._hooks: dict[str, list[Callable]] = {
            "on_message": [],
            "on_agent_start": [],
            "on_agent_end": [],
            "on_error": [],
        }
    
    def add_agent(
        self,
        agent_id: str,
        config: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Add an agent to the orchestration.
        
        Args:
            agent_id: ID of registered agent
            config: Optional agent configuration
            
        Returns:
            True if added successfully
        """
        agent = self.registry.create_instance(agent_id)
        if not agent:
            return False
        
        # Set LLM provider if agent has the method
        if hasattr(agent, "set_llm") and self.llm_provider:
            agent.set_llm(self.llm_provider)
        
        # NEW: Wire up agent integrations for token efficiency
        self._wire_agent_integrations(agent_id, agent)
        
        self._agents[agent_id] = agent
        return True
    
    def _wire_agent_integrations(self, agent_id: str, agent: AgentBase) -> None:
        """
        Wire up agent integrations for the token-efficient memory system.
        
        - Context Agent: Provides project structure summary (~200 chars)
        - RAG Agent: Returns file summaries (~2k tokens) instead of raw code (~50k)
        - Security Agent: Uses Context + RAG for smarter validation
        - Compliance Agent: Uses Context + RAG for smarter validation
        """
        # Get Context Agent and RAG Agent if they exist
        context_agent = self._agents.get("context_agent")
        rag_agent = self._agents.get("rag_agent")
        
        # Wire Security Agent to use Context Agent and RAG Agent
        if agent_id == "security" or agent_id == "security_agent":
            if hasattr(agent, "set_context_agent") and context_agent:
                agent.set_context_agent(context_agent)
            if hasattr(agent, "set_rag_agent") and rag_agent:
                agent.set_rag_agent(rag_agent)
        
        # Wire Compliance Agent to use Context Agent and RAG Agent
        if agent_id == "compliance" or agent_id == "compliance_agent":
            if hasattr(agent, "set_context_agent") and context_agent:
                agent.set_context_agent(context_agent)
            if hasattr(agent, "set_rag_agent") and rag_agent:
                agent.set_rag_agent(rag_agent)
        
        # If this is Context Agent or RAG Agent, wire to existing agents
        if agent_id in ("context_agent", "rag_agent"):
            # Wire to Security Agent
            security_agent = self._agents.get("security") or self._agents.get("security_agent")
            if security_agent:
                if agent_id == "context_agent" and hasattr(security_agent, "set_context_agent"):
                    security_agent.set_context_agent(agent)
                elif agent_id == "rag_agent" and hasattr(security_agent, "set_rag_agent"):
                    security_agent.set_rag_agent(agent)
            
            # Wire to Compliance Agent
            compliance_agent = self._agents.get("compliance") or self._agents.get("compliance_agent")
            if compliance_agent:
                if agent_id == "context_agent" and hasattr(compliance_agent, "set_context_agent"):
                    compliance_agent.set_context_agent(agent)
                elif agent_id == "rag_agent" and hasattr(compliance_agent, "set_rag_agent"):
                    compliance_agent.set_rag_agent(agent)
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from orchestration."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False
    
    def add_hook(self, event: str, callback: Callable) -> None:
        """Add a callback hook for events."""
        if event in self._hooks:
            self._hooks[event].append(callback)
    
    async def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event to all registered hooks."""
        for callback in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                # Log but don't propagate hook errors
                logger.debug(f"Hook {event} error: {e}")
    
    def clear_history(self) -> None:
        """Clear message history."""
        self._message_history.clear()
    
    # === NEW: Token-Efficient Project Context ===
    
    def get_project_summary(self) -> str:
        """
        Get a compact project summary from Context Agent.
        
        This is the key to token efficiency:
        - Instead of re-reading 50k tokens of code
        - We get ~200 chars of summary like:
          "Project: fullstack | Backend: FastAPI | Frontend: React | Files: 15"
        """
        context_agent = self._agents.get("context_agent")
        if not context_agent or not hasattr(context_agent, "get_project_summary_for_prompt"):
            return "Project: Not analyzed"
        
        return context_agent.get_project_summary_for_prompt()
    
    def is_fullstack_project(self) -> bool:
        """
        Check if project is fullstack (needs both backend + frontend updates).
        
        When user says "metti il login", this tells us to generate:
        - Backend: /api/auth/login endpoint
        - Frontend: LoginPage component
        """
        context_agent = self._agents.get("context_agent")
        if not context_agent or not hasattr(context_agent, "requires_backend_and_frontend"):
            return False
        
        return context_agent.requires_backend_and_frontend()
    
    async def get_relevant_context(self, query: str) -> str:
        """
        Get token-efficient relevant context for a query.
        
        Uses RAG Agent summaries instead of raw code:
        - Raw code: ~50k tokens
        - Summaries: ~2k tokens
        """
        rag_agent = self._agents.get("rag_agent")
        if not rag_agent or not hasattr(rag_agent, "get_relevant_summaries"):
            return ""
        
        return await rag_agent.get_relevant_summaries(query)
    
    # === NEW: Code Validation API (for Copilot Integration) ===
    
    async def validate_code(
        self,
        code: str,
        file_path: str,
    ) -> dict[str, Any]:
        """
        Validate code from Copilot BEFORE it gets applied.
        
        This is the main API for "Assistant to the Assistant" pattern:
        1. Copilot generates code
        2. Extension intercepts before applying
        3. OMNI validates (security + compliance)
        4. Returns OK or issues
        
        Args:
            code: The code Copilot wants to write
            file_path: Where the code will be written
            
        Returns:
            {
                "approved": bool,
                "security": {...},
                "compliance": {...},
                "project_context": str,
                "summary": str,
            }
        """
        results = {
            "approved": True,
            "security": {"valid": True, "issues": []},
            "compliance": {"valid": True, "issues": []},
            "project_context": self.get_project_summary(),
            "summary": "",
        }
        
        issues = []
        
        # Run Security validation
        security_agent = self._agents.get("security") or self._agents.get("security_agent")
        if security_agent and hasattr(security_agent, "validate_code"):
            try:
                security_result = await security_agent.validate_code(code, file_path)
                results["security"] = security_result
                if not security_result.get("valid", True):
                    results["approved"] = False
                    issues.append(f"🔒 Security: {security_result.get('issue_count', 0)} issues")
            except asyncio.TimeoutError as e:
                err = AgentTimeoutError("Security validation timed out", context=ErrorContext(agent_id="security_agent", operation="validate_code"))
                logger.warning(str(err))
                # Timeout is recoverable - mark as not validated but don't fail hard
                results["security"] = {"valid": False, "issues": ["Validation timed out - please retry"], "error": str(err)}
            except AgentError as e:
                logger.error(f"Security validation failed: {e}")
                results["security"] = {"valid": False, "issues": [str(e)], "recoverable": e.recoverable}
            except Exception as e:
                wrapped = wrap_exception(e, "Security validation failed", AgentError, ErrorContext(agent_id="security_agent", operation="validate_code"))
                logger.error(str(wrapped))
                results["security"] = {"valid": False, "issues": [str(e)]}
        
        # Run Compliance validation
        compliance_agent = self._agents.get("compliance") or self._agents.get("compliance_agent")
        if compliance_agent and hasattr(compliance_agent, "validate_code"):
            try:
                compliance_result = await compliance_agent.validate_code(code, file_path)
                results["compliance"] = compliance_result
                if not compliance_result.get("valid", True):
                    results["approved"] = False
                    issues.append(f"📋 Compliance: {compliance_result.get('issue_count', 0)} issues")
            except asyncio.TimeoutError as e:
                err = AgentTimeoutError("Compliance validation timed out", context=ErrorContext(agent_id="compliance_agent", operation="validate_code"))
                logger.warning(str(err))
                results["compliance"] = {"valid": False, "issues": ["Validation timed out - please retry"], "error": str(err)}
            except AgentError as e:
                logger.error(f"Compliance validation failed: {e}")
                results["compliance"] = {"valid": False, "issues": [str(e)], "recoverable": e.recoverable}
            except Exception as e:
                wrapped = wrap_exception(e, "Compliance validation failed", AgentError, ErrorContext(agent_id="compliance_agent", operation="validate_code"))
                logger.error(str(wrapped))
                results["compliance"] = {"valid": False, "issues": [str(e)]}
        
        # Build summary
        if results["approved"]:
            results["summary"] = "✅ Code validated - no issues found"
        else:
            results["summary"] = f"⚠️ Issues found: {', '.join(issues)}"
        
        return results
    
    async def register_file(
        self,
        file_path: str,
        content: str,
    ) -> None:
        """
        Register a file after Copilot writes it.
        
        Called by the extension AFTER code is applied.
        Updates Context Agent and RAG Agent for memory.
        """
        # Register with Context Agent
        context_agent = self._agents.get("context_agent")
        if context_agent and hasattr(context_agent, "register_generated_file"):
            try:
                context_agent.register_generated_file(file_path, content)
            except AgentError as e:
                logger.warning(f"Failed to register with Context Agent: {e}")
            except Exception as e:
                wrapped = wrap_exception(e, f"Failed to register file {file_path}", AgentError, ErrorContext(agent_id="context_agent", operation="register_file"))
                logger.warning(str(wrapped))
        
        # Index with RAG Agent
        rag_agent = self._agents.get("rag_agent")
        if rag_agent and hasattr(rag_agent, "index_file_with_summary"):
            try:
                rag_agent.index_file_with_summary(file_path, content)
            except AgentError as e:
                logger.warning(f"Failed to index with RAG Agent: {e}")
            except Exception as e:
                wrapped = wrap_exception(e, f"Failed to index file {file_path}", AgentError, ErrorContext(agent_id="rag_agent", operation="index_file"))
                logger.warning(str(wrapped))

    async def send_to_agent(
        self,
        agent_id: str,
        message: AgentMessage,
        context: Optional[AgentContext] = None,
    ) -> AgentMessage:
        """
        Send a message to a specific agent.
        
        Args:
            agent_id: Target agent ID
            message: Message to send
            context: Optional context
            
        Returns:
            Agent's response
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return AgentMessage(
                content=f"Agent {agent_id} not found",
                type=MessageType.ERROR,
                sender="orchestrator",
            )
        
        if context is None:
            context = AgentContext(
                session_id=str(uuid4()),
                message_history=self._message_history.copy(),
            )
        
        await self._emit("on_agent_start", agent_id, message)
        
        try:
            response = await agent.process(message, context)
            self._message_history.append(message)
            self._message_history.append(response)
            
            await self._emit("on_message", response)
            await self._emit("on_agent_end", agent_id, response)
            
            return response
            
        except asyncio.TimeoutError as e:
            err = AgentTimeoutError(f"Agent {agent_id} timed out", context=ErrorContext(agent_id=agent_id, operation="process"))
            await self._emit("on_error", agent_id, err)
            return AgentMessage(
                content=str(err),
                type=MessageType.ERROR,
                sender="orchestrator",
            )
        except AgentError as e:
            await self._emit("on_error", agent_id, e)
            return AgentMessage(
                content=f"Agent error from {agent_id}: {str(e)} (recoverable: {e.recoverable})",
                type=MessageType.ERROR,
                sender="orchestrator",
            )
        except Exception as e:
            wrapped = wrap_exception(e, f"Error from agent {agent_id}", AgentError, ErrorContext(agent_id=agent_id, operation="process"))
            await self._emit("on_error", agent_id, wrapped)
            return AgentMessage(
                content=str(wrapped),
                type=MessageType.ERROR,
                sender="orchestrator",
            )
    
    async def send_to_agent_with_retry(
        self,
        agent_id: str,
        message: AgentMessage,
        context: Optional[AgentContext] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> AgentMessage:
        """
        Send a message to an agent with automatic retry on recoverable errors.
        
        Uses exponential backoff for transient failures like timeouts.
        
        Args:
            agent_id: Target agent ID
            message: Message to send
            context: Optional context
            retry_config: Retry configuration (default: RETRY_FAST)
            
        Returns:
            Agent's response
        """
        config = retry_config or RETRY_FAST
        
        async def _do_send():
            agent = self._agents.get(agent_id)
            if not agent:
                raise AgentNotFoundError(agent_id)
            
            if context is None:
                ctx = AgentContext(
                    session_id=str(uuid4()),
                    message_history=self._message_history.copy(),
                )
            else:
                ctx = context
            
            return await agent.process(message, ctx)
        
        def on_retry(exc: Exception, attempt: int):
            logger.info(f"Retrying agent {agent_id} (attempt {attempt}): {exc}")
            # Emit event for UI feedback
            asyncio.create_task(self._emit("on_retry", agent_id, attempt, exc))
        
        try:
            await self._emit("on_agent_start", agent_id, message)
            
            response = await retry_async(
                _do_send,
                config=config,
                on_retry=on_retry,
            )
            
            self._message_history.append(message)
            self._message_history.append(response)
            
            await self._emit("on_message", response)
            await self._emit("on_agent_end", agent_id, response)
            
            return response
            
        except AgentNotFoundError as e:
            return AgentMessage(
                content=str(e),
                type=MessageType.ERROR,
                sender="orchestrator",
            )
        except AgentError as e:
            await self._emit("on_error", agent_id, e)
            return AgentMessage(
                content=f"Agent error from {agent_id} after retries: {str(e)}",
                type=MessageType.ERROR,
                sender="orchestrator",
            )
        except Exception as e:
            wrapped = wrap_exception(e, f"Error from agent {agent_id}", AgentError)
            await self._emit("on_error", agent_id, wrapped)
            return AgentMessage(
                content=str(wrapped),
                type=MessageType.ERROR,
                sender="orchestrator",
            )
    
    async def run_sequential(
        self,
        initial_message: str,
        agent_order: list[str],
        max_turns: int = 10,
        stop_condition: Optional[Callable[[AgentMessage], bool]] = None,
    ) -> list[AgentMessage]:
        """
        Run agents in sequential order.
        
        Each agent receives the previous agent's output.
        
        Args:
            initial_message: Starting message
            agent_order: Order of agents to run
            max_turns: Maximum conversation turns
            stop_condition: Optional function to check if should stop
            
        Returns:
            List of all messages
        """
        self.clear_history()
        results: list[AgentMessage] = []
        
        current_message = AgentMessage(
            content=initial_message,
            type=MessageType.TEXT,
            sender="user",
        )
        results.append(current_message)
        
        context = AgentContext(
            session_id=str(uuid4()),
            message_history=[],
        )
        
        turn = 0
        agent_idx = 0
        
        while turn < max_turns:
            agent_id = agent_order[agent_idx % len(agent_order)]
            
            response = await self.send_to_agent(agent_id, current_message, context)
            results.append(response)
            
            if response.type == MessageType.ERROR:
                break
            
            if stop_condition and stop_condition(response):
                break
            
            current_message = response
            context.message_history = self._message_history.copy()
            
            turn += 1
            agent_idx += 1
        
        return results
    
    async def run_round_robin(
        self,
        initial_message: str,
        rounds: int = 3,
    ) -> list[AgentMessage]:
        """
        Run all agents in round-robin fashion.
        
        Each round, every agent gets a turn.
        
        Args:
            initial_message: Starting message
            rounds: Number of complete rounds
            
        Returns:
            List of all messages
        """
        agent_order = list(self._agents.keys()) * rounds
        return await self.run_sequential(
            initial_message=initial_message,
            agent_order=agent_order,
            max_turns=len(agent_order),
        )
    
    async def run_broadcast(
        self,
        message: str,
    ) -> dict[str, AgentMessage]:
        """
        Broadcast a message to all agents and collect responses.
        
        All agents respond independently to the same message.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Dict mapping agent ID to response
        """
        msg = AgentMessage(
            content=message,
            type=MessageType.TEXT,
            sender="user",
        )
        
        # Run all agents in parallel
        tasks = [
            self.send_to_agent(agent_id, msg)
            for agent_id in self._agents
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            agent_id: resp if isinstance(resp, AgentMessage) else AgentMessage(
                content=str(resp),
                type=MessageType.ERROR,
                sender=agent_id,
            )
            for agent_id, resp in zip(self._agents.keys(), responses)
        }
    
    async def run_with_selector(
        self,
        initial_message: str,
        selector_agent_id: str,
        max_turns: int = 10,
    ) -> list[AgentMessage]:
        """
        Run conversation with a selector agent choosing the next speaker.
        
        The selector agent decides which agent should respond next.
        
        Args:
            initial_message: Starting message
            selector_agent_id: Agent that selects next speaker
            max_turns: Maximum turns
            
        Returns:
            List of all messages
        """
        self.clear_history()
        results: list[AgentMessage] = []
        
        current_message = AgentMessage(
            content=initial_message,
            type=MessageType.TEXT,
            sender="user",
        )
        results.append(current_message)
        
        context = AgentContext(
            session_id=str(uuid4()),
            config={"available_agents": list(self._agents.keys())},
            message_history=[],
        )
        
        available = [a for a in self._agents.keys() if a != selector_agent_id]
        
        for turn in range(max_turns):
            # Ask selector which agent should respond
            selector_prompt = AgentMessage(
                content=f"Based on the conversation, which agent should respond next? Available: {available}. Reply with just the agent ID.",
                type=MessageType.TEXT,
                sender="orchestrator",
            )
            
            selector_response = await self.send_to_agent(
                selector_agent_id, selector_prompt, context
            )
            
            # Parse selected agent
            selected_agent = None
            for agent_id in available:
                if agent_id.lower() in selector_response.content.lower():
                    selected_agent = agent_id
                    break
            
            if not selected_agent:
                selected_agent = available[turn % len(available)]
            
            # Get response from selected agent
            response = await self.send_to_agent(selected_agent, current_message, context)
            results.append(response)
            
            if response.type == MessageType.ERROR:
                break
            
            current_message = response
            context.message_history = self._message_history.copy()
        
        return results
    
    def get_agent_statuses(self) -> dict[str, AgentStatus]:
        """Get current status of all agents."""
        return {
            agent_id: agent.status
            for agent_id, agent in self._agents.items()
        }
    
    async def initialize_agents(self, context: AgentContext) -> None:
        """Initialize all agents with context."""
        for agent in self._agents.values():
            await agent.initialize(context)
    
    async def shutdown_agents(self) -> None:
        """Shutdown all agents."""
        for agent in self._agents.values():
            await agent.shutdown()

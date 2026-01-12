"""
AutoGen Multi-Agent Runtime

Provides optional AutoGen integration for multi-agent conversations.
AutoGen is OPTIONAL - the system works without it.

This runtime:
- Wraps existing agents as AutoGen agents
- Enables group chat conversations
- Is completely disabled by default

Safety guarantees:
- If AutoGen is not installed, all operations are no-ops
- If autogen.enabled=false, existing behavior unchanged
- Existing agent interfaces are NOT modified
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from backend.core.interfaces.agent import (
    AgentBase,
    AgentMessage,
    AgentContext,
    MessageType,
)

logger = logging.getLogger(__name__)

# AutoGen imports are conditional
AUTOGEN_AVAILABLE = False
try:
    from autogen import AssistantAgent as AutoGenAssistant
    from autogen import UserProxyAgent as AutoGenUserProxy
    from autogen import GroupChat, GroupChatManager
    from autogen import ConversableAgent
    AUTOGEN_AVAILABLE = True
    logger.info("AutoGen is available")
except ImportError:
    logger.info("AutoGen not installed - multi-agent features disabled")


@dataclass
class AutoGenConfig:
    """Configuration for AutoGen runtime."""
    enabled: bool = False
    
    # Group chat settings
    max_rounds: int = 10
    speaker_selection_method: str = "auto"  # auto, round_robin, random
    allow_repeat_speaker: bool = True
    
    # LLM config for AutoGen (will be generated from our LLM settings)
    llm_config: Optional[dict] = None
    
    # Termination settings
    termination_msg: str = "TERMINATE"
    human_input_mode: str = "NEVER"  # NEVER, TERMINATE, ALWAYS


@dataclass
class GroupChatResult:
    """Result of a group chat session."""
    messages: list[dict[str, Any]]
    final_response: str
    rounds: int
    agents_participated: list[str]
    terminated_by: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "messages": self.messages,
            "final_response": self.final_response,
            "rounds": self.rounds,
            "agents_participated": self.agents_participated,
            "terminated_by": self.terminated_by,
            "timestamp": self.timestamp.isoformat(),
        }


class OmniAgentWrapper:
    """
    Wraps an OMNI agent as an AutoGen-compatible agent.
    
    This wrapper allows existing OMNI agents to participate
    in AutoGen group chats without modification.
    """
    
    def __init__(
        self,
        omni_agent: AgentBase,
        llm_config: Optional[dict] = None,
    ):
        self.omni_agent = omni_agent
        self._llm_config = llm_config
        self._autogen_agent: Optional[Any] = None
    
    @property
    def name(self) -> str:
        return self.omni_agent.metadata.id
    
    @property
    def description(self) -> str:
        return self.omni_agent.metadata.description
    
    def create_autogen_agent(self) -> Any:
        """Create AutoGen agent wrapper."""
        if not AUTOGEN_AVAILABLE:
            raise RuntimeError("AutoGen not installed")
        
        # Create a custom AutoGen agent that delegates to our agent
        system_message = f"""You are {self.omni_agent.metadata.name}.
{self.omni_agent.metadata.description}

Your capabilities:
{chr(10).join(f'- {c.name}: {c.description}' for c in self.omni_agent.metadata.capabilities)}

Respond based on your expertise and capabilities."""
        
        self._autogen_agent = AutoGenAssistant(
            name=self.name,
            system_message=system_message,
            llm_config=self._llm_config,
        )
        
        return self._autogen_agent
    
    async def process_message(
        self,
        message: str,
        context: AgentContext,
    ) -> str:
        """Process message through OMNI agent."""
        agent_message = AgentMessage(
            content=message,
            type=MessageType.TEXT,
            sender="autogen_runtime",
        )
        
        response = await self.omni_agent.process(agent_message, context)
        return str(response.content)


class AutoGenRuntime:
    """
    AutoGen Multi-Agent Runtime.
    
    This runtime:
    - Is completely optional (disabled by default)
    - Wraps existing OMNI agents for AutoGen compatibility
    - Enables multi-agent group conversations
    
    Example:
        ```python
        config = AutoGenConfig(enabled=True)
        runtime = AutoGenRuntime(config, llm_config={...})
        
        # Run group chat
        result = await runtime.run_group_chat(
            agents=[security_agent, coding_agent, compliance_agent],
            task="Review and fix security issues in auth.py",
        )
        ```
    """
    
    def __init__(
        self,
        config: Optional[AutoGenConfig] = None,
        llm_config: Optional[dict] = None,
    ):
        self.config = config or AutoGenConfig()
        self._llm_config = llm_config
        
        # Wrapped agents
        self._wrappers: dict[str, OmniAgentWrapper] = {}
        
        # User proxy for initiating conversations
        self._user_proxy: Optional[Any] = None
    
    def is_available(self) -> bool:
        """Check if AutoGen is available and enabled."""
        return self.config.enabled and AUTOGEN_AVAILABLE
    
    def wrap_agent(self, agent: AgentBase) -> OmniAgentWrapper:
        """
        Wrap an OMNI agent for AutoGen compatibility.
        
        Args:
            agent: OMNI agent to wrap
            
        Returns:
            Wrapped agent ready for AutoGen
        """
        if agent.metadata.id in self._wrappers:
            return self._wrappers[agent.metadata.id]
        
        wrapper = OmniAgentWrapper(agent, self._llm_config)
        self._wrappers[agent.metadata.id] = wrapper
        
        return wrapper
    
    def _get_user_proxy(self) -> Any:
        """Get or create user proxy agent."""
        if not AUTOGEN_AVAILABLE:
            raise RuntimeError("AutoGen not installed")
        
        if self._user_proxy is None:
            self._user_proxy = AutoGenUserProxy(
                name="user_proxy",
                human_input_mode=self.config.human_input_mode,
                code_execution_config={"use_docker": False},  # Disable code execution
                is_termination_msg=lambda msg: self.config.termination_msg in msg.get("content", ""),
            )
        
        return self._user_proxy
    
    async def run_group_chat(
        self,
        agents: list[AgentBase],
        task: str,
        context: Optional[AgentContext] = None,
    ) -> GroupChatResult:
        """
        Run a multi-agent group chat.
        
        Args:
            agents: List of OMNI agents to participate
            task: The task/question to discuss
            context: Optional shared context
            
        Returns:
            GroupChatResult with conversation history
        """
        if not self.is_available():
            logger.warning("AutoGen not available, returning empty result")
            return GroupChatResult(
                messages=[],
                final_response="AutoGen is not available or disabled",
                rounds=0,
                agents_participated=[],
            )
        
        try:
            # Wrap all agents
            autogen_agents = []
            for agent in agents:
                wrapper = self.wrap_agent(agent)
                autogen_agent = wrapper.create_autogen_agent()
                autogen_agents.append(autogen_agent)
            
            # Add user proxy
            user_proxy = self._get_user_proxy()
            
            # Create group chat
            group_chat = GroupChat(
                agents=[user_proxy] + autogen_agents,
                messages=[],
                max_round=self.config.max_rounds,
                speaker_selection_method=self.config.speaker_selection_method,
                allow_repeat_speaker=self.config.allow_repeat_speaker,
            )
            
            # Create manager
            manager = GroupChatManager(
                groupchat=group_chat,
                llm_config=self._llm_config,
            )
            
            # Run conversation
            await asyncio.to_thread(
                user_proxy.initiate_chat,
                manager,
                message=task,
            )
            
            # Extract results
            messages = [
                {"sender": msg.get("name", "unknown"), "content": msg.get("content", "")}
                for msg in group_chat.messages
            ]
            
            final_response = ""
            if messages:
                final_response = messages[-1].get("content", "")
            
            participated = list(set(msg["sender"] for msg in messages))
            
            return GroupChatResult(
                messages=messages,
                final_response=final_response,
                rounds=len(messages),
                agents_participated=participated,
            )
            
        except Exception as e:
            logger.error(f"Group chat failed: {e}")
            return GroupChatResult(
                messages=[],
                final_response=f"Group chat failed: {str(e)}",
                rounds=0,
                agents_participated=[],
            )
    
    async def run_two_agent_chat(
        self,
        agent1: AgentBase,
        agent2: AgentBase,
        initial_message: str,
        max_turns: int = 5,
    ) -> GroupChatResult:
        """
        Run a simple two-agent conversation.
        
        Args:
            agent1: First agent
            agent2: Second agent
            initial_message: Starting message
            max_turns: Maximum conversation turns
            
        Returns:
            Conversation result
        """
        if not self.is_available():
            return GroupChatResult(
                messages=[],
                final_response="AutoGen not available",
                rounds=0,
                agents_participated=[],
            )
        
        try:
            wrapper1 = self.wrap_agent(agent1)
            wrapper2 = self.wrap_agent(agent2)
            
            autogen1 = wrapper1.create_autogen_agent()
            autogen2 = wrapper2.create_autogen_agent()
            
            # Run conversation
            await asyncio.to_thread(
                autogen1.initiate_chat,
                autogen2,
                message=initial_message,
                max_turns=max_turns,
            )
            
            # Extract messages from conversation history
            messages = []
            for msg in autogen1.chat_messages.get(autogen2, []):
                messages.append({
                    "sender": msg.get("name", "unknown"),
                    "content": msg.get("content", ""),
                })
            
            final_response = messages[-1]["content"] if messages else ""
            
            return GroupChatResult(
                messages=messages,
                final_response=final_response,
                rounds=len(messages),
                agents_participated=[agent1.metadata.id, agent2.metadata.id],
            )
            
        except Exception as e:
            logger.error(f"Two-agent chat failed: {e}")
            return GroupChatResult(
                messages=[],
                final_response=f"Chat failed: {str(e)}",
                rounds=0,
                agents_participated=[],
            )


# =============================================================================
# PREDEFINED GROUP CHAT CONFIGURATIONS
# =============================================================================

async def run_security_review_chat(
    runtime: AutoGenRuntime,
    coding_agent: AgentBase,
    security_agent: AgentBase,
    compliance_agent: AgentBase,
    file_path: str,
) -> GroupChatResult:
    """
    Run a security review group chat.
    
    Three agents collaborate:
    1. Coding agent proposes changes
    2. Security agent reviews for vulnerabilities
    3. Compliance agent checks regulations
    
    Args:
        runtime: AutoGen runtime
        coding_agent: Agent to propose code changes
        security_agent: Agent to review security
        compliance_agent: Agent to check compliance
        file_path: File to review
        
    Returns:
        Group chat result with review findings
    """
    task = f"""Review the file: {file_path}

Each agent should:
1. Coding Agent: Identify potential improvements
2. Security Agent: Check for vulnerabilities
3. Compliance Agent: Verify compliance requirements

Discuss findings and reach consensus on required changes.
End with TERMINATE when review is complete."""
    
    return await runtime.run_group_chat(
        agents=[coding_agent, security_agent, compliance_agent],
        task=task,
    )


async def run_code_fix_chat(
    runtime: AutoGenRuntime,
    coding_agent: AgentBase,
    security_agent: AgentBase,
    issue_description: str,
    file_path: str,
) -> GroupChatResult:
    """
    Run a code fix collaboration chat.
    
    Two agents collaborate:
    1. Coding agent proposes fix
    2. Security agent validates fix is safe
    
    Args:
        runtime: AutoGen runtime
        coding_agent: Agent to propose fix
        security_agent: Agent to validate
        issue_description: Description of issue to fix
        file_path: File to fix
        
    Returns:
        Group chat result with proposed fix
    """
    task = f"""Fix the following issue in {file_path}:

{issue_description}

Coding Agent: Propose a fix as a unified diff
Security Agent: Review the fix for security issues

Iterate until fix is approved. End with TERMINATE when complete."""
    
    return await runtime.run_group_chat(
        agents=[coding_agent, security_agent],
        task=task,
    )

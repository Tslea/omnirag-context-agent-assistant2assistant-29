"""
Base Agent Implementations

Provides foundational agent types that can be extended.
"""

from typing import Any, Optional
import json

from backend.core.interfaces.agent import (
    AgentBase,
    AgentMetadata,
    AgentCapability,
    AgentMessage,
    AgentContext,
    AgentTool,
    MessageType,
    AgentStatus,
)
from backend.core.interfaces.llm import LLMProvider, LLMMessage, LLMRole, LLMConfig


class AssistantAgent(AgentBase):
    """
    General-purpose assistant agent.
    
    Provides conversational AI capabilities with tool use support.
    """
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        system_prompt: Optional[str] = None,
    ):
        super().__init__()
        self._llm = llm_provider
        self._custom_system_prompt = system_prompt
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="assistant",
            name="Assistant",
            description="General-purpose AI assistant for conversation and tasks",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="conversation",
                    description="Natural language conversation",
                ),
                AgentCapability(
                    name="tool_use",
                    description="Can use registered tools",
                ),
            ],
            tags=["general", "assistant", "conversation"],
        )
    
    def set_llm(self, provider: LLMProvider) -> None:
        """Set the LLM provider for this agent."""
        self._llm = provider
    
    def get_system_prompt(self) -> str:
        if self._custom_system_prompt:
            return self._custom_system_prompt
        return """You are a helpful AI assistant. You provide clear, accurate, and helpful responses.
When using tools, explain what you're doing and why.
Be concise but thorough in your explanations."""
    
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Process a message using the LLM."""
        if not self._llm:
            return AgentMessage(
                content="Error: No LLM provider configured",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
        
        self.status = AgentStatus.THINKING
        
        try:
            # Build conversation history
            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=self.get_system_prompt())
            ]
            
            # Add context history
            for hist_msg in context.message_history[-10:]:  # Last 10 messages
                role = LLMRole.USER if hist_msg.sender == "user" else LLMRole.ASSISTANT
                messages.append(LLMMessage(role=role, content=str(hist_msg.content)))
            
            # Add current message
            messages.append(LLMMessage(role=LLMRole.USER, content=str(message.content)))
            
            # Prepare tools if available
            config = LLMConfig(model=self._llm.default_model)
            if self._tools:
                config.tools = [tool.to_openai_format() for tool in self._tools]
            
            # Get completion
            response = await self._llm.complete(messages, config)
            
            # Handle tool calls
            if response.tool_calls:
                self.status = AgentStatus.EXECUTING
                tool_results = []
                
                for tool_call in response.tool_calls:
                    try:
                        args = json.loads(tool_call.arguments)
                        result = await self.handle_tool_call(tool_call.name, args, context)
                        tool_results.append({
                            "tool": tool_call.name,
                            "result": result,
                        })
                    except Exception as e:
                        tool_results.append({
                            "tool": tool_call.name,
                            "error": str(e),
                        })
                
                # Get final response with tool results
                messages.append(LLMMessage(
                    role=LLMRole.ASSISTANT,
                    content=response.content or "",
                    tool_calls=[{
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments}
                    } for tc in response.tool_calls],
                ))
                
                for i, tool_call in enumerate(response.tool_calls):
                    messages.append(LLMMessage(
                        role=LLMRole.TOOL,
                        content=json.dumps(tool_results[i]),
                        tool_call_id=tool_call.id,
                    ))
                
                response = await self._llm.complete(messages, config)
            
            self.status = AgentStatus.IDLE
            
            return AgentMessage(
                content=response.content or "No response generated",
                type=MessageType.TEXT,
                sender=self.metadata.id,
                metadata={
                    "model": response.model,
                    "usage": response.usage.__dict__ if response.usage else None,
                },
            )
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentMessage(
                content=f"Error processing message: {str(e)}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )


class CodeAgent(AgentBase):
    """
    Specialized agent for code-related tasks.
    
    Handles code generation, review, and analysis.
    """
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        language: str = "python",
    ):
        super().__init__()
        self._llm = llm_provider
        self._language = language
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="code_agent",
            name="Code Agent",
            description="Specialized agent for code generation, review, and analysis",
            version="1.0.0",
            capabilities=[
                AgentCapability(name="code_generation", description="Generate code from descriptions"),
                AgentCapability(name="code_review", description="Review code for issues"),
                AgentCapability(name="code_explanation", description="Explain code"),
                AgentCapability(name="refactoring", description="Suggest code improvements"),
            ],
            tags=["code", "development", "programming"],
        )
    
    def set_llm(self, provider: LLMProvider) -> None:
        self._llm = provider
    
    def get_system_prompt(self) -> str:
        return f"""You are an expert programmer specializing in {self._language}.
You write clean, efficient, well-documented code.
When generating code:
- Include type hints where appropriate
- Add docstrings and comments
- Follow best practices and conventions
- Consider edge cases and error handling

When reviewing code:
- Look for bugs, security issues, and performance problems
- Suggest improvements
- Explain your reasoning"""
    
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        if not self._llm:
            return AgentMessage(
                content="Error: No LLM provider configured",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
        
        self.status = AgentStatus.THINKING
        
        try:
            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=self.get_system_prompt()),
                LLMMessage(role=LLMRole.USER, content=str(message.content)),
            ]
            
            response = await self._llm.complete(messages)
            
            self.status = AgentStatus.IDLE
            
            return AgentMessage(
                content=response.content or "No response generated",
                type=MessageType.TEXT,
                sender=self.metadata.id,
                metadata={"language": self._language},
            )
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentMessage(
                content=f"Error: {str(e)}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )


class PlannerAgent(AgentBase):
    """
    Planning and orchestration agent.
    
    Breaks down complex tasks and coordinates other agents.
    """
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__()
        self._llm = llm_provider
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="planner",
            name="Planner Agent",
            description="Plans complex tasks and coordinates agent workflows",
            version="1.0.0",
            capabilities=[
                AgentCapability(name="task_decomposition", description="Break down complex tasks"),
                AgentCapability(name="agent_selection", description="Select appropriate agents"),
                AgentCapability(name="workflow_planning", description="Plan multi-step workflows"),
            ],
            tags=["planning", "orchestration", "workflow"],
        )
    
    def set_llm(self, provider: LLMProvider) -> None:
        self._llm = provider
    
    def get_system_prompt(self) -> str:
        return """You are a planning agent that breaks down complex tasks.
Given a task:
1. Analyze what needs to be done
2. Break it into smaller, actionable steps
3. Identify which type of agent/capability is needed for each step
4. Consider dependencies between steps
5. Provide a clear execution plan

Output your plan as a structured list of steps with:
- Step number
- Description
- Required capability/agent
- Dependencies (which steps must complete first)
- Expected output"""
    
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        if not self._llm:
            return AgentMessage(
                content="Error: No LLM provider configured",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
        
        self.status = AgentStatus.THINKING
        
        try:
            # Get available agents from context
            available_agents = context.get_config("available_agents", [])
            
            system_prompt = self.get_system_prompt()
            if available_agents:
                system_prompt += f"\n\nAvailable agents: {', '.join(available_agents)}"
            
            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=system_prompt),
                LLMMessage(role=LLMRole.USER, content=f"Plan this task: {message.content}"),
            ]
            
            response = await self._llm.complete(messages)
            
            self.status = AgentStatus.IDLE
            
            return AgentMessage(
                content=response.content or "Unable to create plan",
                type=MessageType.TEXT,
                sender=self.metadata.id,
                metadata={"type": "plan"},
            )
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentMessage(
                content=f"Error creating plan: {str(e)}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )

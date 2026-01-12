"""Core interfaces package."""

from backend.core.interfaces.llm import LLMProvider, LLMResponse, LLMConfig
from backend.core.interfaces.vectordb import VectorDBProvider, Document, SearchResult
from backend.core.interfaces.agent import AgentBase, AgentContext, AgentMessage
from backend.core.interfaces.workflow import WorkflowBase, WorkflowStep, WorkflowContext

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMConfig",
    "VectorDBProvider",
    "Document", 
    "SearchResult",
    "AgentBase",
    "AgentContext",
    "AgentMessage",
    "WorkflowBase",
    "WorkflowStep",
    "WorkflowContext",
]

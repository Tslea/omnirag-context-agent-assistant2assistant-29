"""
LLM Adapters Package

Provides concrete implementations of the LLMProvider interface
for various LLM providers (OpenAI, Anthropic, local LLMs, etc.)
"""

from backend.adapters.llm.base import BaseLLMAdapter
from backend.adapters.llm.openai_adapter import OpenAIAdapter
from backend.adapters.llm.anthropic_adapter import AnthropicAdapter
from backend.adapters.llm.local_adapter import LocalLLMAdapter
from backend.adapters.llm.factory import LLMFactory

__all__ = [
    "BaseLLMAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter", 
    "LocalLLMAdapter",
    "LLMFactory",
]

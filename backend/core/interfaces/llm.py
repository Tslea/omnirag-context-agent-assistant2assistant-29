"""
LLM Provider Interface

Defines the contract for all LLM adapters (OpenAI, Anthropic, local LLMs, etc.)
This interface ensures any LLM provider can be swapped without changing application code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional


class LLMRole(str, Enum):
    """Message roles for chat completions."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"

# Backward-compatibility alias used in tests
MessageRole = LLMRole


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: LLMRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None


@dataclass
class LLMConfig:
    """Configuration for LLM requests."""
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "default"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[list[str]] = None
    tools: Optional[list[dict[str, Any]]] = None
    tool_choice: Optional[str | dict[str, Any]] = None
    response_format: Optional[dict[str, str]] = None
    seed: Optional[int] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMUsage:
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMToolCall:
    """A tool/function call from the LLM."""
    id: str
    name: str
    arguments: str  # JSON string


@dataclass 
class LLMResponse:
    """Response from an LLM completion request."""
    content: Optional[str] = None
    tool_calls: Optional[list[LLMToolCall]] = None
    usage: Optional[LLMUsage] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM adapters (OpenAI, Anthropic, local LLMs, etc.) must implement this interface.
    This ensures consistent behavior across different providers and enables easy swapping.
    
    Example:
        ```python
        provider = OpenAIAdapter(api_key="...", model="gpt-4")
        response = await provider.complete([
            LLMMessage(role=LLMRole.USER, content="Hello!")
        ])
        print(response.content)
        ```
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider (e.g., 'openai', 'anthropic')."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is properly configured and available."""
        pass
    
    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """
        Generate a completion for the given messages.
        
        Args:
            messages: List of conversation messages
            config: Optional configuration overrides
            
        Returns:
            LLMResponse with the completion result
            
        Raises:
            LLMProviderError: If the request fails
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a completion for the given messages.
        
        Args:
            messages: List of conversation messages
            config: Optional configuration overrides
            
        Yields:
            String chunks as they arrive
            
        Raises:
            LLMProviderError: If the request fails
        """
        pass
    
    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for the given texts.
        
        Args:
            texts: List of texts to embed
            model: Optional embedding model override
            
        Returns:
            List of embedding vectors
            
        Raises:
            LLMProviderError: If the request fails
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Verify the provider is working correctly.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.complete([
                LLMMessage(role=LLMRole.USER, content="ping")
            ], LLMConfig(model=self.default_model, max_tokens=5))
            return response.content is not None
        except Exception:
            return False
    
    @property
    def default_model(self) -> str:
        """Return the default model for this provider."""
        return "default"
    
    @property
    def default_embedding_model(self) -> str:
        """Return the default embedding model for this provider."""
        return "default"


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        raw_error: Optional[Any] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.raw_error = raw_error


class LLMRateLimitError(LLMProviderError):
    """Raised when rate limited by the provider."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication fails."""
    pass


class LLMContextLengthError(LLMProviderError):
    """Raised when the context length is exceeded."""
    pass

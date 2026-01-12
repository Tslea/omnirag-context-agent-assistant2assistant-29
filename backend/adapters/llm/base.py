"""
Base LLM Adapter

Provides common functionality for all LLM adapters.
"""

from abc import ABC
from typing import Any, Optional

from backend.core.interfaces.llm import (
    LLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMProviderError,
)


class BaseLLMAdapter(LLMProvider, ABC):
    """
    Base class for LLM adapters with common functionality.
    
    Provides:
    - Configuration management
    - Request/response logging
    - Error handling utilities
    - Rate limiting support
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        default_embedding_model: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._default_model = default_model
        self._default_embedding_model = default_embedding_model
        self._timeout = timeout
        self._max_retries = max_retries
        self._extra_config = kwargs
        self._client: Any = None
    
    @property
    def default_model(self) -> str:
        return self._default_model or "default"
    
    @property
    def default_embedding_model(self) -> str:
        return self._default_embedding_model or "default"
    
    def _merge_config(self, config: Optional[LLMConfig]) -> LLMConfig:
        """Merge provided config with defaults."""
        if config is None:
            return LLMConfig(model=self.default_model)
        
        return LLMConfig(
            model=config.model or self.default_model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.frequency_penalty,
            presence_penalty=config.presence_penalty,
            stop=config.stop,
            tools=config.tools,
            tool_choice=config.tool_choice,
            response_format=config.response_format,
            seed=config.seed,
            extra=config.extra,
        )
    
    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert internal message format to provider format. Override if needed."""
        result = []
        for msg in messages:
            d = {
                "role": msg.role.value,
                "content": msg.content,
            }
            if msg.name:
                d["name"] = msg.name
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                d["tool_calls"] = msg.tool_calls
            result.append(d)
        return result
    
    def _handle_error(self, error: Exception, context: str = "") -> None:
        """Convert provider-specific errors to standard errors."""
        raise LLMProviderError(
            message=f"{context}: {str(error)}",
            provider=self.provider_name,
            raw_error=error,
        )

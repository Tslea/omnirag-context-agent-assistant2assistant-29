"""
Anthropic LLM Adapter

Implements the LLMProvider interface for Anthropic's Claude API.
"""

import os
from typing import Any, AsyncIterator, Optional

from backend.adapters.llm.base import BaseLLMAdapter
from backend.core.interfaces.llm import (
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMRole,
    LLMUsage,
    LLMToolCall,
    LLMProviderError,
    LLMRateLimitError,
    LLMAuthenticationError,
)


class AnthropicAdapter(BaseLLMAdapter):
    """
    Anthropic Claude adapter.
    
    Example:
        ```python
        adapter = AnthropicAdapter(
            api_key="sk-ant-...",
            default_model="claude-3-opus-20240229"
        )
        response = await adapter.complete([
            LLMMessage(role=LLMRole.USER, content="Hello!")
        ])
        ```
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "claude-3-sonnet-20240229",
        **kwargs: Any,
    ):
        super().__init__(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            base_url=base_url or os.getenv("ANTHROPIC_BASE_URL"),
            default_model=default_model,
            **kwargs,
        )
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def is_available(self) -> bool:
        return self._api_key is not None
    
    @property
    def default_embedding_model(self) -> str:
        # Anthropic doesn't have embeddings, would need to use another provider
        return "voyage-large-2"
    
    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(
                    api_key=self._api_key,
                    base_url=self._base_url,
                    timeout=self._timeout,
                    max_retries=self._max_retries,
                )
            except ImportError:
                raise LLMProviderError(
                    message="anthropic package not installed. Run: pip install anthropic",
                    provider=self.provider_name,
                )
        return self._client
    
    def _convert_messages_anthropic(
        self, messages: list[LLMMessage]
    ) -> tuple[Optional[str], list[dict[str, Any]]]:
        """Convert messages to Anthropic format (separate system message)."""
        system_message = None
        converted = []
        
        for msg in messages:
            if msg.role == LLMRole.SYSTEM:
                system_message = msg.content
            else:
                role = "user" if msg.role == LLMRole.USER else "assistant"
                converted.append({
                    "role": role,
                    "content": msg.content,
                })
        
        return system_message, converted
    
    async def complete(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate a completion using Anthropic's API."""
        config = self._merge_config(config)
        client = self._get_client()
        
        try:
            system_message, converted_messages = self._convert_messages_anthropic(messages)
            
            kwargs: dict[str, Any] = {
                "model": config.model,
                "messages": converted_messages,
                "max_tokens": config.max_tokens or 4096,
            }
            
            if system_message:
                kwargs["system"] = system_message
            if config.temperature != 0.7:  # Non-default
                kwargs["temperature"] = config.temperature
            if config.top_p != 1.0:
                kwargs["top_p"] = config.top_p
            if config.stop:
                kwargs["stop_sequences"] = config.stop
            
            # Handle tools (Anthropic format)
            if config.tools:
                kwargs["tools"] = self._convert_tools_anthropic(config.tools)
            
            response = await client.messages.create(**kwargs)
            
            # Parse response
            content = None
            tool_calls = None
            
            for block in response.content:
                if block.type == "text":
                    content = block.text
                elif block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    import json
                    tool_calls.append(LLMToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=json.dumps(block.input),
                    ))
            
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                usage=LLMUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                ),
                model=response.model,
                finish_reason=response.stop_reason,
                raw_response=response,
            )
            
        except Exception as e:
            self._handle_anthropic_error(e)
            raise
    
    async def stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[str]:
        """Stream a completion using Anthropic's API."""
        config = self._merge_config(config)
        client = self._get_client()
        
        try:
            system_message, converted_messages = self._convert_messages_anthropic(messages)
            
            kwargs: dict[str, Any] = {
                "model": config.model,
                "messages": converted_messages,
                "max_tokens": config.max_tokens or 4096,
            }
            
            if system_message:
                kwargs["system"] = system_message
            
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            self._handle_anthropic_error(e)
    
    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """
        Anthropic doesn't provide embeddings directly.
        This would need to use a different provider (e.g., Voyage AI).
        """
        raise LLMProviderError(
            message="Anthropic does not provide embeddings. Use a different provider.",
            provider=self.provider_name,
        )
    
    def _convert_tools_anthropic(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert OpenAI-style tools to Anthropic format."""
        converted = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                converted.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                })
        return converted
    
    def _handle_anthropic_error(self, error: Exception) -> None:
        """Convert Anthropic errors to standard errors."""
        error_str = str(error)
        
        if "rate_limit" in error_str.lower() or "429" in error_str:
            raise LLMRateLimitError(
                message="Rate limit exceeded",
                provider=self.provider_name,
                status_code=429,
                raw_error=error,
            )
        elif "authentication" in error_str.lower() or "401" in error_str:
            raise LLMAuthenticationError(
                message="Authentication failed - check your API key",
                provider=self.provider_name,
                status_code=401,
                raw_error=error,
            )
        else:
            raise LLMProviderError(
                message=error_str,
                provider=self.provider_name,
                raw_error=error,
            )

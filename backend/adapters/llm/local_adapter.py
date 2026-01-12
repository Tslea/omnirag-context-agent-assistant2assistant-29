"""
Local LLM Adapter

Implements the LLMProvider interface for local LLMs via:
- LM Studio (OpenAI-compatible API)
- Ollama
- llama.cpp server
"""

import os
from typing import Any, AsyncIterator, Optional

from backend.adapters.llm.base import BaseLLMAdapter
from backend.core.interfaces.llm import (
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    LLMToolCall,
    LLMProviderError,
)


class LocalLLMAdapter(BaseLLMAdapter):
    """
    Local LLM adapter supporting LM Studio, Ollama, and llama.cpp.
    
    All these tools provide OpenAI-compatible APIs, so we can use
    the OpenAI client with a custom base URL.
    
    Example:
        ```python
        # LM Studio (default port 1234)
        adapter = LocalLLMAdapter(
            base_url="http://localhost:1234/v1",
            default_model="local-model"
        )
        
        # Ollama
        adapter = LocalLLMAdapter(
            provider_type="ollama",
            base_url="http://localhost:11434/v1",
            default_model="llama2"
        )
        ```
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: str = "local-model",
        provider_type: str = "lmstudio",  # lmstudio, ollama, llamacpp
        **kwargs: Any,
    ):
        # Set default base URLs based on provider type
        if base_url is None:
            default_urls = {
                "lmstudio": "http://localhost:1234/v1",
                "ollama": "http://localhost:11434/v1",
                "llamacpp": "http://localhost:8080/v1",
            }
            base_url = default_urls.get(provider_type, "http://localhost:1234/v1")
        
        super().__init__(
            api_key="not-needed",  # Local LLMs don't need API keys
            base_url=base_url,
            default_model=default_model,
            **kwargs,
        )
        self._provider_type = provider_type
    
    @property
    def provider_name(self) -> str:
        return f"local-{self._provider_type}"
    
    @property
    def is_available(self) -> bool:
        """Check if local LLM server is running."""
        return self._base_url is not None
    
    def _get_client(self):
        """Get OpenAI-compatible client for local LLM."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key="not-needed",
                    base_url=self._base_url,
                    timeout=self._timeout,
                    max_retries=self._max_retries,
                )
            except ImportError:
                raise LLMProviderError(
                    message="openai package not installed. Run: pip install openai",
                    provider=self.provider_name,
                )
        return self._client
    
    async def complete(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate a completion using local LLM."""
        config = self._merge_config(config)
        client = self._get_client()
        
        try:
            kwargs: dict[str, Any] = {
                "model": config.model,
                "messages": self._convert_messages(messages),
                "temperature": config.temperature,
            }
            
            if config.max_tokens:
                kwargs["max_tokens"] = config.max_tokens
            if config.stop:
                kwargs["stop"] = config.stop
            
            # Tools support varies by local provider
            if config.tools and self._provider_type != "llamacpp":
                kwargs["tools"] = config.tools
                if config.tool_choice:
                    kwargs["tool_choice"] = config.tool_choice
            
            response = await client.chat.completions.create(**kwargs)
            
            choice = response.choices[0]
            message = choice.message
            
            # Parse tool calls if present
            tool_calls = None
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_calls = [
                    LLMToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                    for tc in message.tool_calls
                ]
            
            # Local LLMs may not return usage stats
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = LLMUsage(
                    prompt_tokens=response.usage.prompt_tokens or 0,
                    completion_tokens=response.usage.completion_tokens or 0,
                    total_tokens=response.usage.total_tokens or 0,
                )
            
            return LLMResponse(
                content=message.content,
                tool_calls=tool_calls,
                usage=usage,
                model=response.model if hasattr(response, 'model') else config.model,
                finish_reason=choice.finish_reason if hasattr(choice, 'finish_reason') else None,
                raw_response=response,
            )
            
        except Exception as e:
            self._handle_local_error(e)
            raise
    
    async def stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[str]:
        """Stream a completion using local LLM."""
        config = self._merge_config(config)
        client = self._get_client()
        
        try:
            kwargs: dict[str, Any] = {
                "model": config.model,
                "messages": self._convert_messages(messages),
                "temperature": config.temperature,
                "stream": True,
            }
            
            if config.max_tokens:
                kwargs["max_tokens"] = config.max_tokens
            
            stream = await client.chat.completions.create(**kwargs)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            self._handle_local_error(e)
    
    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """Generate embeddings using local LLM (if supported)."""
        client = self._get_client()
        model = model or self.default_embedding_model
        
        try:
            response = await client.embeddings.create(
                model=model,
                input=texts,
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            # Many local LLMs don't support embeddings
            raise LLMProviderError(
                message=f"Embeddings not supported by {self.provider_name}: {e}",
                provider=self.provider_name,
                raw_error=e,
            )
    
    async def health_check(self) -> bool:
        """Check if local LLM server is responsive."""
        try:
            client = self._get_client()
            # Try to list models - most OpenAI-compatible servers support this
            await client.models.list()
            return True
        except Exception:
            try:
                # Fallback: try a minimal completion
                return await super().health_check()
            except Exception:
                return False
    
    async def list_models(self) -> list[str]:
        """List available models from local server."""
        try:
            client = self._get_client()
            response = await client.models.list()
            return [model.id for model in response.data]
        except Exception:
            return []
    
    def _handle_local_error(self, error: Exception) -> None:
        """Convert local LLM errors to standard errors."""
        error_str = str(error)
        
        if "connection" in error_str.lower() or "refused" in error_str.lower():
            raise LLMProviderError(
                message=f"Cannot connect to local LLM at {self._base_url}. Is the server running?",
                provider=self.provider_name,
                raw_error=error,
            )
        else:
            raise LLMProviderError(
                message=error_str,
                provider=self.provider_name,
                raw_error=error,
            )

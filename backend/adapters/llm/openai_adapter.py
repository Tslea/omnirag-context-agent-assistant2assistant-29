"""
OpenAI LLM Adapter

Implements the LLMProvider interface for OpenAI's API.
Supports GPT-4, GPT-3.5, and embedding models.
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
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMContextLengthError,
)


class OpenAIAdapter(BaseLLMAdapter):
    """
    OpenAI LLM adapter supporting GPT-4, GPT-3.5, and embeddings.
    
    Example:
        ```python
        adapter = OpenAIAdapter(
            api_key="sk-...",
            default_model="gpt-4-turbo-preview"
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
        default_model: str = "gpt-4-turbo-preview",
        default_embedding_model: str = "text-embedding-3-small",
        organization: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            default_model=default_model,
            default_embedding_model=default_embedding_model,
            **kwargs,
        )
        self._organization = organization or os.getenv("OPENAI_ORGANIZATION")
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def is_available(self) -> bool:
        return self._api_key is not None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                    organization=self._organization,
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
        """Generate a completion using OpenAI's API."""
        config = self._merge_config(config)
        client = self._get_client()
        
        try:
            kwargs: dict[str, Any] = {
                "model": config.model,
                "messages": self._convert_messages(messages),
                "temperature": config.temperature,
                "top_p": config.top_p,
                "frequency_penalty": config.frequency_penalty,
                "presence_penalty": config.presence_penalty,
            }
            
            if config.max_tokens:
                kwargs["max_tokens"] = config.max_tokens
            if config.stop:
                kwargs["stop"] = config.stop
            if config.tools:
                kwargs["tools"] = config.tools
            if config.tool_choice:
                kwargs["tool_choice"] = config.tool_choice
            if config.response_format:
                kwargs["response_format"] = config.response_format
            if config.seed is not None:
                kwargs["seed"] = config.seed
            
            # Add any extra parameters
            kwargs.update(config.extra)
            
            response = await client.chat.completions.create(**kwargs)
            
            choice = response.choices[0]
            message = choice.message
            
            # Parse tool calls if present
            tool_calls = None
            if message.tool_calls:
                tool_calls = [
                    LLMToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                    for tc in message.tool_calls
                ]
            
            return LLMResponse(
                content=message.content,
                tool_calls=tool_calls,
                usage=LLMUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                ) if response.usage else None,
                model=response.model,
                finish_reason=choice.finish_reason,
                raw_response=response,
            )
            
        except Exception as e:
            self._handle_openai_error(e)
            raise  # Never reached but makes type checker happy
    
    async def stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[str]:
        """Stream a completion using OpenAI's API."""
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
            self._handle_openai_error(e)
    
    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """Generate embeddings using OpenAI's API."""
        client = self._get_client()
        model = model or self.default_embedding_model
        
        try:
            response = await client.embeddings.create(
                model=model,
                input=texts,
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            self._handle_openai_error(e)
            raise
    
    def _handle_openai_error(self, error: Exception) -> None:
        """Convert OpenAI errors to standard errors."""
        error_str = str(error)
        
        # Check for specific error types
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
        elif "context_length" in error_str.lower() or "maximum context" in error_str.lower():
            raise LLMContextLengthError(
                message="Context length exceeded",
                provider=self.provider_name,
                raw_error=error,
            )
        else:
            raise LLMProviderError(
                message=error_str,
                provider=self.provider_name,
                raw_error=error,
            )

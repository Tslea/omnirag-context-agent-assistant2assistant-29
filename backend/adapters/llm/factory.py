"""
LLM Factory

Creates LLM providers based on configuration.
Enables easy swapping between providers.
"""

from typing import Any, Optional

from backend.core.interfaces.llm import LLMProvider, LLMProviderError
from backend.adapters.llm.openai_adapter import OpenAIAdapter
from backend.adapters.llm.anthropic_adapter import AnthropicAdapter
from backend.adapters.llm.local_adapter import LocalLLMAdapter


class LLMFactory:
    """
    Factory for creating LLM providers.
    
    Supports dynamic provider selection based on configuration.
    
    Example:
        ```python
        # Create from config
        provider = LLMFactory.create("openai", api_key="sk-...")
        
        # Or from config dict
        provider = LLMFactory.from_config({
            "provider": "anthropic",
            "api_key": "sk-ant-...",
            "model": "claude-3-opus"
        })
        ```
    """
    
    # Registry of available providers
    _providers: dict[str, type[LLMProvider]] = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "claude": AnthropicAdapter,  # Alias
        "local": LocalLLMAdapter,
        "lmstudio": LocalLLMAdapter,
        "ollama": LocalLLMAdapter,
        "llamacpp": LocalLLMAdapter,
    }
    
    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]) -> None:
        """
        Register a new provider type.
        
        Args:
            name: Provider name (used in config)
            provider_class: Provider class implementing LLMProvider
        """
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def create(
        cls,
        provider: str,
        **kwargs: Any,
    ) -> LLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            provider: Provider name (openai, anthropic, local, etc.)
            **kwargs: Provider-specific configuration
            
        Returns:
            Configured LLMProvider instance
            
        Raises:
            LLMProviderError: If provider not found
        """
        provider_lower = provider.lower()
        
        if provider_lower not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise LLMProviderError(
                message=f"Unknown provider: {provider}. Available: {available}",
                provider=provider,
            )
        
        provider_class = cls._providers[provider_lower]
        
        # Handle local LLM provider types
        if provider_lower in ("lmstudio", "ollama", "llamacpp"):
            kwargs["provider_type"] = provider_lower
        
        return provider_class(**kwargs)
    
    @classmethod
    def from_config(cls, config: dict[str, Any]) -> LLMProvider:
        """
        Create an LLM provider from a configuration dictionary.
        
        Args:
            config: Configuration dictionary with 'provider' key
            
        Returns:
            Configured LLMProvider instance
        """
        config = config.copy()
        provider = config.pop("provider", "openai")
        
        # Map common config keys
        key_mapping = {
            "model": "default_model",
            "embedding_model": "default_embedding_model",
        }
        
        for old_key, new_key in key_mapping.items():
            if old_key in config and new_key not in config:
                config[new_key] = config.pop(old_key)
        
        return cls.create(provider, **config)
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(set(cls._providers.keys()))
    
    @classmethod
    async def create_with_health_check(
        cls,
        provider: str,
        **kwargs: Any,
    ) -> LLMProvider:
        """
        Create a provider and verify it's working.
        
        Args:
            provider: Provider name
            **kwargs: Provider configuration
            
        Returns:
            Verified LLMProvider instance
            
        Raises:
            LLMProviderError: If health check fails
        """
        instance = cls.create(provider, **kwargs)
        
        if not instance.is_available:
            raise LLMProviderError(
                message=f"Provider {provider} is not available (missing configuration)",
                provider=provider,
            )
        
        if not await instance.health_check():
            raise LLMProviderError(
                message=f"Provider {provider} health check failed",
                provider=provider,
            )
        
        return instance

"""
Vector Database Factory

Creates vector database providers based on configuration.
"""

from typing import Any, Optional

from backend.core.interfaces.vectordb import VectorDBProvider, VectorDBError
from backend.adapters.vectordb.qdrant_adapter import QdrantAdapter
from backend.adapters.vectordb.chroma_adapter import ChromaAdapter
from backend.adapters.vectordb.faiss_adapter import FAISSAdapter


class VectorDBFactory:
    """
    Factory for creating vector database providers.
    
    Example:
        ```python
        # Create from config
        db = VectorDBFactory.create("qdrant", url="localhost:6333")
        
        # Or from config dict
        db = VectorDBFactory.from_config({
            "provider": "chroma",
            "persist_path": "./data"
        })
        ```
    """
    
    _providers: dict[str, type[VectorDBProvider]] = {
        "qdrant": QdrantAdapter,
        "chroma": ChromaAdapter,
        "chromadb": ChromaAdapter,
        "faiss": FAISSAdapter,
    }
    
    @classmethod
    def register(cls, name: str, provider_class: type[VectorDBProvider]) -> None:
        """Register a new provider type."""
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def create(
        cls,
        provider: str,
        **kwargs: Any,
    ) -> VectorDBProvider:
        """
        Create a vector database provider instance.
        
        Args:
            provider: Provider name (qdrant, chroma, faiss)
            **kwargs: Provider-specific configuration
            
        Returns:
            Configured VectorDBProvider instance
        """
        provider_lower = provider.lower()
        
        if provider_lower not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise VectorDBError(
                message=f"Unknown provider: {provider}. Available: {available}",
                provider=provider,
            )
        
        return cls._providers[provider_lower](**kwargs)
    
    @classmethod
    def from_config(cls, config: dict[str, Any]) -> VectorDBProvider:
        """Create a provider from configuration dictionary."""
        config = config.copy()
        provider = config.pop("provider", "chroma")
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
    ) -> VectorDBProvider:
        """Create and verify a provider is working."""
        instance = cls.create(provider, **kwargs)
        
        if not instance.is_available:
            raise VectorDBError(
                message=f"Provider {provider} is not available",
                provider=provider,
            )
        
        if not await instance.health_check():
            raise VectorDBError(
                message=f"Provider {provider} health check failed",
                provider=provider,
            )
        
        return instance

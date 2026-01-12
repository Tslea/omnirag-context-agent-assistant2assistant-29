"""
Base Vector Database Adapter

Provides common functionality for all vector database adapters.
"""

from abc import ABC
from typing import Any, Optional

from backend.core.interfaces.vectordb import (
    VectorDBProvider,
    Document,
    SearchConfig,
    VectorDBError,
)


class BaseVectorDBAdapter(VectorDBProvider, ABC):
    """
    Base class for vector database adapters with common functionality.
    
    Provides:
    - Configuration management
    - Connection handling
    - Error handling utilities
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        persist_path: Optional[str] = None,
        **kwargs: Any,
    ):
        self._url = url
        self._api_key = api_key
        self._persist_path = persist_path
        self._extra_config = kwargs
        self._client: Any = None
    
    def _validate_documents(self, documents: list[Document]) -> None:
        """Validate documents have required fields."""
        for doc in documents:
            if not doc.id:
                raise VectorDBError(
                    message="Document must have an ID",
                    provider=self.provider_name,
                )
            if doc.embedding is None:
                raise VectorDBError(
                    message=f"Document {doc.id} must have an embedding",
                    provider=self.provider_name,
                )
    
    def _merge_search_config(self, config: Optional[SearchConfig]) -> SearchConfig:
        """Merge provided config with defaults."""
        if config is None:
            return SearchConfig()
        return config
    
    def _handle_error(self, error: Exception, context: str = "") -> None:
        """Convert provider-specific errors to standard errors."""
        raise VectorDBError(
            message=f"{context}: {str(error)}",
            provider=self.provider_name,
            raw_error=error,
        )

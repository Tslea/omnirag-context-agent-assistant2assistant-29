"""
Vector Database Provider Interface

Defines the contract for all vector database adapters (Qdrant, Chroma, FAISS, etc.)
This interface ensures consistent document storage and retrieval across providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class DistanceMetric(str, Enum):
    """Distance metrics for similarity search."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"


@dataclass
class Document:
    """
    A document to be stored in the vector database.
    
    Attributes:
        id: Unique identifier (auto-generated if not provided)
        content: The text content of the document
        embedding: Optional pre-computed embedding vector
        metadata: Additional metadata (source, timestamp, etc.)
    """
    content: str
    id: str = field(default_factory=lambda: str(uuid4()))
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())


@dataclass
class SearchResult:
    """
    A single search result from the vector database.
    
    Attributes:
        document: The matched document
        score: Similarity score (higher = more similar for cosine)
        distance: Raw distance value
    """
    document: Document
    score: float
    distance: Optional[float] = None


@dataclass
class CollectionConfig:
    """Configuration for creating a collection."""
    provider: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    name: Optional[str] = None
    collection_name: Optional[str] = None
    dimension: int = 1536
    distance_metric: DistanceMetric = DistanceMetric.COSINE
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Allow tests to pass collection_name instead of name
        if not self.name:
            self.name = self.collection_name or "default"


@dataclass
class SearchConfig:
    """Configuration for search queries."""
    top_k: int = 10
    score_threshold: Optional[float] = None
    filter: Optional[dict[str, Any]] = None
    include_metadata: bool = True
    include_embeddings: bool = False


class VectorDBProvider(ABC):
    """
    Abstract base class for vector database providers.
    
    All vector DB adapters (Qdrant, Chroma, FAISS, etc.) must implement this interface.
    This ensures consistent document storage and retrieval across providers.
    
    Example:
        ```python
        db = QdrantAdapter(url="localhost:6333")
        await db.create_collection(CollectionConfig(name="docs", dimension=1536))
        await db.upsert("docs", [Document(content="Hello world", embedding=[...])])
        results = await db.search("docs", query_embedding=[...], config=SearchConfig(top_k=5))
        ```
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider (e.g., 'qdrant', 'chroma')."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is properly configured and available."""
        pass
    
    @abstractmethod
    async def create_collection(self, config: CollectionConfig) -> bool:
        """
        Create a new collection/index.
        
        Args:
            config: Collection configuration
            
        Returns:
            True if created successfully
            
        Raises:
            VectorDBError: If creation fails
        """
        pass
    
    @abstractmethod
    async def delete_collection(self, name: str) -> bool:
        """
        Delete a collection/index.
        
        Args:
            name: Collection name
            
        Returns:
            True if deleted successfully
        """
        pass
    
    @abstractmethod
    async def collection_exists(self, name: str) -> bool:
        """
        Check if a collection exists.
        
        Args:
            name: Collection name
            
        Returns:
            True if exists
        """
        pass
    
    @abstractmethod
    async def list_collections(self) -> list[str]:
        """
        List all collections.
        
        Returns:
            List of collection names
        """
        pass
    
    @abstractmethod
    async def upsert(
        self,
        collection: str,
        documents: list[Document],
    ) -> list[str]:
        """
        Insert or update documents in a collection.
        
        Args:
            collection: Collection name
            documents: Documents to upsert (must have embeddings)
            
        Returns:
            List of document IDs that were upserted
            
        Raises:
            VectorDBError: If upsert fails
        """
        pass
    
    @abstractmethod
    async def delete(
        self,
        collection: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict[str, Any]] = None,
    ) -> int:
        """
        Delete documents from a collection.
        
        Args:
            collection: Collection name
            ids: Optional list of document IDs to delete
            filter: Optional metadata filter for deletion
            
        Returns:
            Number of documents deleted
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        config: Optional[SearchConfig] = None,
    ) -> list[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            collection: Collection name
            query_embedding: Query vector
            config: Search configuration
            
        Returns:
            List of search results ordered by similarity
        """
        pass
    
    @abstractmethod
    async def get(
        self,
        collection: str,
        ids: list[str],
    ) -> list[Document]:
        """
        Get documents by ID.
        
        Args:
            collection: Collection name
            ids: Document IDs to retrieve
            
        Returns:
            List of documents (empty if not found)
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Verify the provider is working correctly.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            await self.list_collections()
            return True
        except Exception:
            return False
    
    @abstractmethod
    async def count(self, collection: str) -> int:
        """
        Count documents in a collection.
        
        Args:
            collection: Collection name
            
        Returns:
            Number of documents
        """
        pass


class VectorDBError(Exception):
    """Base exception for vector database errors."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        collection: Optional[str] = None,
        raw_error: Optional[Any] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.collection = collection
        self.raw_error = raw_error


class CollectionNotFoundError(VectorDBError):
    """Raised when a collection does not exist."""
    pass


class CollectionExistsError(VectorDBError):
    """Raised when trying to create a collection that already exists."""
    pass

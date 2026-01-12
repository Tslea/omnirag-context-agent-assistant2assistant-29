"""
Qdrant Vector Database Adapter

Implements the VectorDBProvider interface for Qdrant.
"""

import os
from typing import Any, Optional

from backend.adapters.vectordb.base import BaseVectorDBAdapter
from backend.core.interfaces.vectordb import (
    Document,
    SearchResult,
    CollectionConfig,
    SearchConfig,
    DistanceMetric,
    VectorDBError,
    CollectionNotFoundError,
    CollectionExistsError,
)


class QdrantAdapter(BaseVectorDBAdapter):
    """
    Qdrant vector database adapter.
    
    Supports both local (in-memory/disk) and cloud Qdrant instances.
    
    Example:
        ```python
        # Cloud instance
        adapter = QdrantAdapter(
            url="https://your-cluster.qdrant.io",
            api_key="your-api-key"
        )
        
        # Local instance
        adapter = QdrantAdapter(url="http://localhost:6333")
        
        # In-memory (for testing)
        adapter = QdrantAdapter(location=":memory:")
        ```
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        location: Optional[str] = None,  # :memory: or path
        prefer_grpc: bool = False,
        **kwargs: Any,
    ):
        super().__init__(
            url=url or os.getenv("QDRANT_URL"),
            api_key=api_key or os.getenv("QDRANT_API_KEY"),
            **kwargs,
        )
        self._location = location
        self._prefer_grpc = prefer_grpc
    
    @property
    def provider_name(self) -> str:
        return "qdrant"
    
    @property
    def is_available(self) -> bool:
        return self._url is not None or self._location is not None
    
    def _get_client(self):
        """Lazy initialization of Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                
                if self._location:
                    # Local/in-memory mode
                    self._client = QdrantClient(location=self._location)
                else:
                    # Remote mode
                    self._client = QdrantClient(
                        url=self._url,
                        api_key=self._api_key,
                        prefer_grpc=self._prefer_grpc,
                    )
            except ImportError:
                raise VectorDBError(
                    message="qdrant-client not installed. Run: pip install qdrant-client",
                    provider=self.provider_name,
                )
        return self._client
    
    def _get_distance(self, metric: DistanceMetric):
        """Convert distance metric to Qdrant format."""
        from qdrant_client.models import Distance
        mapping = {
            DistanceMetric.COSINE: Distance.COSINE,
            DistanceMetric.EUCLIDEAN: Distance.EUCLID,
            DistanceMetric.DOT_PRODUCT: Distance.DOT,
        }
        return mapping.get(metric, Distance.COSINE)
    
    async def create_collection(self, config: CollectionConfig) -> bool:
        """Create a new collection in Qdrant."""
        client = self._get_client()
        
        try:
            from qdrant_client.models import VectorParams
            
            # Check if exists
            if await self.collection_exists(config.name):
                raise CollectionExistsError(
                    message=f"Collection {config.name} already exists",
                    provider=self.provider_name,
                    collection=config.name,
                )
            
            client.create_collection(
                collection_name=config.name,
                vectors_config=VectorParams(
                    size=config.dimension,
                    distance=self._get_distance(config.distance_metric),
                ),
            )
            return True
            
        except CollectionExistsError:
            raise
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to create collection: {e}",
                provider=self.provider_name,
                collection=config.name,
                raw_error=e,
            )
    
    async def delete_collection(self, name: str) -> bool:
        """Delete a collection from Qdrant."""
        client = self._get_client()
        
        try:
            client.delete_collection(collection_name=name)
            return True
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to delete collection: {e}",
                provider=self.provider_name,
                collection=name,
                raw_error=e,
            )
    
    async def collection_exists(self, name: str) -> bool:
        """Check if a collection exists."""
        client = self._get_client()
        
        try:
            collections = client.get_collections().collections
            return any(c.name == name for c in collections)
        except Exception:
            return False
    
    async def list_collections(self) -> list[str]:
        """List all collections."""
        client = self._get_client()
        
        try:
            collections = client.get_collections().collections
            return [c.name for c in collections]
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to list collections: {e}",
                provider=self.provider_name,
                raw_error=e,
            )
    
    async def upsert(
        self,
        collection: str,
        documents: list[Document],
    ) -> list[str]:
        """Insert or update documents in Qdrant."""
        self._validate_documents(documents)
        client = self._get_client()
        
        try:
            from qdrant_client.models import PointStruct
            
            points = [
                PointStruct(
                    id=doc.id,
                    vector=doc.embedding,
                    payload={
                        "content": doc.content,
                        **doc.metadata,
                    },
                )
                for doc in documents
            ]
            
            client.upsert(
                collection_name=collection,
                points=points,
            )
            
            return [doc.id for doc in documents]
            
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to upsert documents: {e}",
                provider=self.provider_name,
                collection=collection,
                raw_error=e,
            )
    
    async def delete(
        self,
        collection: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict[str, Any]] = None,
    ) -> int:
        """Delete documents from Qdrant."""
        client = self._get_client()
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            if ids:
                client.delete(
                    collection_name=collection,
                    points_selector=ids,
                )
                return len(ids)
            elif filter:
                # Convert filter to Qdrant format
                conditions = [
                    FieldCondition(key=k, match=MatchValue(value=v))
                    for k, v in filter.items()
                ]
                client.delete(
                    collection_name=collection,
                    points_selector=Filter(must=conditions),
                )
                return -1  # Unknown count for filter deletes
            
            return 0
            
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to delete documents: {e}",
                provider=self.provider_name,
                collection=collection,
                raw_error=e,
            )
    
    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        config: Optional[SearchConfig] = None,
    ) -> list[SearchResult]:
        """Search for similar documents in Qdrant."""
        config = self._merge_search_config(config)
        client = self._get_client()
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Build filter if provided
            qdrant_filter = None
            if config.filter:
                conditions = [
                    FieldCondition(key=k, match=MatchValue(value=v))
                    for k, v in config.filter.items()
                ]
                qdrant_filter = Filter(must=conditions)
            
            results = client.search(
                collection_name=collection,
                query_vector=query_embedding,
                limit=config.top_k,
                query_filter=qdrant_filter,
                score_threshold=config.score_threshold,
                with_payload=config.include_metadata,
                with_vectors=config.include_embeddings,
            )
            
            return [
                SearchResult(
                    document=Document(
                        id=str(hit.id),
                        content=hit.payload.get("content", "") if hit.payload else "",
                        embedding=hit.vector if config.include_embeddings else None,
                        metadata={k: v for k, v in (hit.payload or {}).items() if k != "content"},
                    ),
                    score=hit.score,
                )
                for hit in results
            ]
            
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to search: {e}",
                provider=self.provider_name,
                collection=collection,
                raw_error=e,
            )
    
    async def get(
        self,
        collection: str,
        ids: list[str],
    ) -> list[Document]:
        """Get documents by ID from Qdrant."""
        client = self._get_client()
        
        try:
            results = client.retrieve(
                collection_name=collection,
                ids=ids,
                with_payload=True,
                with_vectors=True,
            )
            
            return [
                Document(
                    id=str(point.id),
                    content=point.payload.get("content", "") if point.payload else "",
                    embedding=point.vector,
                    metadata={k: v for k, v in (point.payload or {}).items() if k != "content"},
                )
                for point in results
            ]
            
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to get documents: {e}",
                provider=self.provider_name,
                collection=collection,
                raw_error=e,
            )
    
    async def count(self, collection: str) -> int:
        """Count documents in a collection."""
        client = self._get_client()
        
        try:
            info = client.get_collection(collection_name=collection)
            return info.points_count
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to count documents: {e}",
                provider=self.provider_name,
                collection=collection,
                raw_error=e,
            )

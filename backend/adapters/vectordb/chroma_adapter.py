"""
ChromaDB Vector Database Adapter

Implements the VectorDBProvider interface for ChromaDB.
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


class ChromaAdapter(BaseVectorDBAdapter):
    """
    ChromaDB vector database adapter.
    
    Supports persistent and in-memory modes.
    
    Example:
        ```python
        # Persistent mode
        adapter = ChromaAdapter(persist_path="./chroma_data")
        
        # In-memory mode
        adapter = ChromaAdapter()
        
        # Server mode
        adapter = ChromaAdapter(
            url="http://localhost:8000",
            api_key="your-key"
        )
        ```
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        persist_path: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(
            url=url or os.getenv("CHROMA_URL"),
            api_key=api_key or os.getenv("CHROMA_API_KEY"),
            persist_path=persist_path or os.getenv("CHROMA_PERSIST_PATH"),
            **kwargs,
        )
        self._collections: dict[str, Any] = {}
    
    @property
    def provider_name(self) -> str:
        return "chroma"
    
    @property
    def is_available(self) -> bool:
        return True  # ChromaDB can always run in-memory
    
    def _get_client(self):
        """Lazy initialization of ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings
                
                if self._url:
                    # Server mode
                    self._client = chromadb.HttpClient(
                        host=self._url,
                        headers={"Authorization": f"Bearer {self._api_key}"} if self._api_key else None,
                    )
                elif self._persist_path:
                    # Persistent mode
                    self._client = chromadb.PersistentClient(
                        path=self._persist_path,
                    )
                else:
                    # In-memory mode
                    self._client = chromadb.Client()
                    
            except ImportError:
                raise VectorDBError(
                    message="chromadb not installed. Run: pip install chromadb",
                    provider=self.provider_name,
                )
        return self._client
    
    def _get_distance_fn(self, metric: DistanceMetric) -> str:
        """Convert distance metric to Chroma format."""
        mapping = {
            DistanceMetric.COSINE: "cosine",
            DistanceMetric.EUCLIDEAN: "l2",
            DistanceMetric.DOT_PRODUCT: "ip",
        }
        return mapping.get(metric, "cosine")
    
    async def create_collection(self, config: CollectionConfig) -> bool:
        """Create a new collection in ChromaDB."""
        client = self._get_client()
        
        try:
            # Check if exists
            existing = client.list_collections()
            if any(c.name == config.name for c in existing):
                raise CollectionExistsError(
                    message=f"Collection {config.name} already exists",
                    provider=self.provider_name,
                    collection=config.name,
                )
            
            collection = client.create_collection(
                name=config.name,
                metadata={
                    "hnsw:space": self._get_distance_fn(config.distance_metric),
                    "dimension": config.dimension,
                    **config.metadata,
                },
            )
            self._collections[config.name] = collection
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
        """Delete a collection from ChromaDB."""
        client = self._get_client()
        
        try:
            client.delete_collection(name=name)
            self._collections.pop(name, None)
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
            collections = client.list_collections()
            return any(c.name == name for c in collections)
        except Exception:
            return False
    
    async def list_collections(self) -> list[str]:
        """List all collections."""
        client = self._get_client()
        
        try:
            collections = client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to list collections: {e}",
                provider=self.provider_name,
                raw_error=e,
            )
    
    def _get_collection(self, name: str):
        """Get or create collection reference."""
        if name not in self._collections:
            client = self._get_client()
            try:
                self._collections[name] = client.get_collection(name=name)
            except Exception as e:
                raise CollectionNotFoundError(
                    message=f"Collection {name} not found",
                    provider=self.provider_name,
                    collection=name,
                    raw_error=e,
                )
        return self._collections[name]
    
    async def upsert(
        self,
        collection: str,
        documents: list[Document],
    ) -> list[str]:
        """Insert or update documents in ChromaDB."""
        self._validate_documents(documents)
        coll = self._get_collection(collection)
        
        try:
            coll.upsert(
                ids=[doc.id for doc in documents],
                embeddings=[doc.embedding for doc in documents],
                documents=[doc.content for doc in documents],
                metadatas=[doc.metadata for doc in documents] if any(doc.metadata for doc in documents) else None,
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
        """Delete documents from ChromaDB."""
        coll = self._get_collection(collection)
        
        try:
            if ids:
                coll.delete(ids=ids)
                return len(ids)
            elif filter:
                coll.delete(where=filter)
                return -1  # Unknown count
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
        """Search for similar documents in ChromaDB."""
        config = self._merge_search_config(config)
        coll = self._get_collection(collection)
        
        try:
            results = coll.query(
                query_embeddings=[query_embedding],
                n_results=config.top_k,
                where=config.filter,
                include=["documents", "metadatas", "distances", "embeddings"] if config.include_embeddings else ["documents", "metadatas", "distances"],
            )
            
            # Parse results
            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    # Convert distance to similarity score (Chroma returns distances)
                    distance = results["distances"][0][i] if results["distances"] else 0
                    score = 1 - distance if distance <= 1 else 1 / (1 + distance)
                    
                    if config.score_threshold and score < config.score_threshold:
                        continue
                    
                    search_results.append(SearchResult(
                        document=Document(
                            id=doc_id,
                            content=results["documents"][0][i] if results["documents"] else "",
                            embedding=results["embeddings"][0][i] if results.get("embeddings") and config.include_embeddings else None,
                            metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        ),
                        score=score,
                        distance=distance,
                    ))
            
            return search_results
            
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
        """Get documents by ID from ChromaDB."""
        coll = self._get_collection(collection)
        
        try:
            results = coll.get(
                ids=ids,
                include=["documents", "metadatas", "embeddings"],
            )
            
            documents = []
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"]):
                    documents.append(Document(
                        id=doc_id,
                        content=results["documents"][i] if results["documents"] else "",
                        embedding=results["embeddings"][i] if results.get("embeddings") else None,
                        metadata=results["metadatas"][i] if results["metadatas"] else {},
                    ))
            
            return documents
            
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to get documents: {e}",
                provider=self.provider_name,
                collection=collection,
                raw_error=e,
            )
    
    async def count(self, collection: str) -> int:
        """Count documents in a collection."""
        coll = self._get_collection(collection)
        
        try:
            return coll.count()
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to count documents: {e}",
                provider=self.provider_name,
                collection=collection,
                raw_error=e,
            )

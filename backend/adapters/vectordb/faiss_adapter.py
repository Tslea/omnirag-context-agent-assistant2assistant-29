"""
FAISS Vector Database Adapter

Implements the VectorDBProvider interface for FAISS.
FAISS is primarily for in-memory/local use with optional disk persistence.
"""

import os
import json
import pickle
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass

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


@dataclass
class FAISSCollection:
    """Internal representation of a FAISS collection."""
    name: str
    dimension: int
    index: Any  # FAISS index
    id_to_doc: dict[str, Document]  # ID -> Document mapping
    id_to_idx: dict[str, int]  # ID -> FAISS index position
    idx_to_id: dict[int, str]  # FAISS index position -> ID


class FAISSAdapter(BaseVectorDBAdapter):
    """
    FAISS vector database adapter.
    
    Supports in-memory and disk-persisted indexes.
    
    Example:
        ```python
        # In-memory mode
        adapter = FAISSAdapter()
        
        # Persistent mode
        adapter = FAISSAdapter(persist_path="./faiss_data")
        ```
    """
    
    def __init__(
        self,
        persist_path: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(
            persist_path=persist_path or os.getenv("FAISS_PERSIST_PATH"),
            **kwargs,
        )
        self._collections: dict[str, FAISSCollection] = {}
        self._faiss = None
        
        # Load existing collections from disk if persist_path is set
        if self._persist_path:
            self._load_collections()
    
    @property
    def provider_name(self) -> str:
        return "faiss"
    
    @property
    def is_available(self) -> bool:
        try:
            import faiss
            return True
        except ImportError:
            return False
    
    def _get_faiss(self):
        """Lazy import of FAISS."""
        if self._faiss is None:
            try:
                import faiss
                self._faiss = faiss
            except ImportError:
                raise VectorDBError(
                    message="faiss not installed. Run: pip install faiss-cpu",
                    provider=self.provider_name,
                )
        return self._faiss
    
    def _get_index_type(self, dimension: int, metric: DistanceMetric):
        """Create appropriate FAISS index based on metric."""
        faiss = self._get_faiss()
        
        if metric == DistanceMetric.COSINE:
            # For cosine, we use inner product on normalized vectors
            index = faiss.IndexFlatIP(dimension)
        elif metric == DistanceMetric.EUCLIDEAN:
            index = faiss.IndexFlatL2(dimension)
        elif metric == DistanceMetric.DOT_PRODUCT:
            index = faiss.IndexFlatIP(dimension)
        else:
            index = faiss.IndexFlatL2(dimension)
        
        return index
    
    def _collection_path(self, name: str) -> Path:
        """Get the file path for a collection."""
        if not self._persist_path:
            return None
        path = Path(self._persist_path)
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{name}.faiss"
    
    def _metadata_path(self, name: str) -> Path:
        """Get the metadata file path for a collection."""
        if not self._persist_path:
            return None
        path = Path(self._persist_path)
        return path / f"{name}.meta"
    
    def _save_collection(self, name: str) -> None:
        """Save collection to disk."""
        if not self._persist_path:
            return
        
        faiss = self._get_faiss()
        coll = self._collections.get(name)
        if not coll:
            return
        
        # Save FAISS index
        index_path = self._collection_path(name)
        faiss.write_index(coll.index, str(index_path))
        
        # Save metadata
        meta_path = self._metadata_path(name)
        metadata = {
            "dimension": coll.dimension,
            "id_to_doc": {k: {"id": v.id, "content": v.content, "metadata": v.metadata} 
                        for k, v in coll.id_to_doc.items()},
            "id_to_idx": coll.id_to_idx,
            "idx_to_id": {str(k): v for k, v in coll.idx_to_id.items()},
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f)
    
    def _load_collections(self) -> None:
        """Load all collections from disk."""
        if not self._persist_path:
            return
        
        faiss = self._get_faiss()
        path = Path(self._persist_path)
        
        if not path.exists():
            return
        
        for index_file in path.glob("*.faiss"):
            name = index_file.stem
            meta_file = path / f"{name}.meta"
            
            if not meta_file.exists():
                continue
            
            try:
                # Load index
                index = faiss.read_index(str(index_file))
                
                # Load metadata
                with open(meta_file, "r") as f:
                    metadata = json.load(f)
                
                # Reconstruct documents
                id_to_doc = {
                    k: Document(id=v["id"], content=v["content"], metadata=v["metadata"])
                    for k, v in metadata["id_to_doc"].items()
                }
                
                self._collections[name] = FAISSCollection(
                    name=name,
                    dimension=metadata["dimension"],
                    index=index,
                    id_to_doc=id_to_doc,
                    id_to_idx=metadata["id_to_idx"],
                    idx_to_id={int(k): v for k, v in metadata["idx_to_id"].items()},
                )
            except Exception:
                continue  # Skip corrupted collections
    
    async def create_collection(self, config: CollectionConfig) -> bool:
        """Create a new collection."""
        if config.name in self._collections:
            raise CollectionExistsError(
                message=f"Collection {config.name} already exists",
                provider=self.provider_name,
                collection=config.name,
            )
        
        index = self._get_index_type(config.dimension, config.distance_metric)
        
        self._collections[config.name] = FAISSCollection(
            name=config.name,
            dimension=config.dimension,
            index=index,
            id_to_doc={},
            id_to_idx={},
            idx_to_id={},
        )
        
        self._save_collection(config.name)
        return True
    
    async def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        if name in self._collections:
            del self._collections[name]
        
        # Remove from disk
        if self._persist_path:
            index_path = self._collection_path(name)
            meta_path = self._metadata_path(name)
            if index_path and index_path.exists():
                index_path.unlink()
            if meta_path and meta_path.exists():
                meta_path.unlink()
        
        return True
    
    async def collection_exists(self, name: str) -> bool:
        """Check if collection exists."""
        return name in self._collections
    
    async def list_collections(self) -> list[str]:
        """List all collections."""
        return list(self._collections.keys())
    
    async def upsert(
        self,
        collection: str,
        documents: list[Document],
    ) -> list[str]:
        """Insert or update documents."""
        self._validate_documents(documents)
        
        if collection not in self._collections:
            raise CollectionNotFoundError(
                message=f"Collection {collection} not found",
                provider=self.provider_name,
                collection=collection,
            )
        
        import numpy as np
        coll = self._collections[collection]
        
        # Prepare vectors for batch insert
        new_vectors = []
        new_docs = []
        
        for doc in documents:
            # Remove old version if exists
            if doc.id in coll.id_to_idx:
                # FAISS doesn't support true updates, we track via metadata
                pass
            
            new_vectors.append(doc.embedding)
            new_docs.append(doc)
        
        if new_vectors:
            vectors = np.array(new_vectors, dtype=np.float32)
            
            # Normalize for cosine similarity
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            vectors = vectors / norms
            
            # Add to index
            start_idx = coll.index.ntotal
            coll.index.add(vectors)
            
            # Update mappings
            for i, doc in enumerate(new_docs):
                idx = start_idx + i
                coll.id_to_doc[doc.id] = doc
                coll.id_to_idx[doc.id] = idx
                coll.idx_to_id[idx] = doc.id
        
        self._save_collection(collection)
        return [doc.id for doc in documents]
    
    async def delete(
        self,
        collection: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict[str, Any]] = None,
    ) -> int:
        """Delete documents (marks as deleted, doesn't remove from index)."""
        if collection not in self._collections:
            raise CollectionNotFoundError(
                message=f"Collection {collection} not found",
                provider=self.provider_name,
                collection=collection,
            )
        
        coll = self._collections[collection]
        deleted = 0
        
        if ids:
            for doc_id in ids:
                if doc_id in coll.id_to_doc:
                    del coll.id_to_doc[doc_id]
                    deleted += 1
        
        self._save_collection(collection)
        return deleted
    
    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        config: Optional[SearchConfig] = None,
    ) -> list[SearchResult]:
        """Search for similar documents."""
        config = self._merge_search_config(config)
        
        if collection not in self._collections:
            raise CollectionNotFoundError(
                message=f"Collection {collection} not found",
                provider=self.provider_name,
                collection=collection,
            )
        
        import numpy as np
        coll = self._collections[collection]
        
        if coll.index.ntotal == 0:
            return []
        
        # Normalize query vector for cosine similarity
        query = np.array([query_embedding], dtype=np.float32)
        query = query / np.linalg.norm(query)
        
        # Search
        k = min(config.top_k, coll.index.ntotal)
        distances, indices = coll.index.search(query, k)
        
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0:  # FAISS returns -1 for not found
                continue
            
            doc_id = coll.idx_to_id.get(idx)
            if not doc_id or doc_id not in coll.id_to_doc:
                continue
            
            doc = coll.id_to_doc[doc_id]
            
            # Convert distance to score (for cosine, higher is better)
            score = float(dist)
            
            if config.score_threshold and score < config.score_threshold:
                continue
            
            # Apply metadata filter
            if config.filter:
                match = all(doc.metadata.get(k) == v for k, v in config.filter.items())
                if not match:
                    continue
            
            results.append(SearchResult(
                document=Document(
                    id=doc.id,
                    content=doc.content,
                    embedding=doc.embedding if config.include_embeddings else None,
                    metadata=doc.metadata if config.include_metadata else {},
                ),
                score=score,
                distance=1 - score,  # Convert back to distance
            ))
        
        return results
    
    async def get(
        self,
        collection: str,
        ids: list[str],
    ) -> list[Document]:
        """Get documents by ID."""
        if collection not in self._collections:
            raise CollectionNotFoundError(
                message=f"Collection {collection} not found",
                provider=self.provider_name,
                collection=collection,
            )
        
        coll = self._collections[collection]
        return [coll.id_to_doc[doc_id] for doc_id in ids if doc_id in coll.id_to_doc]
    
    async def count(self, collection: str) -> int:
        """Count documents in collection."""
        if collection not in self._collections:
            raise CollectionNotFoundError(
                message=f"Collection {collection} not found",
                provider=self.provider_name,
                collection=collection,
            )
        
        return len(self._collections[collection].id_to_doc)

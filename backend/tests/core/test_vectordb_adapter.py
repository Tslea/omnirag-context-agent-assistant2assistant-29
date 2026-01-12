"""
Unit Tests for VectorDB Adapter Interface

Tests the FakeVectorStore and validates the VectorDBProvider interface contract.

Run:
    pytest backend/tests/core/test_vectordb_adapter.py -v
"""

import pytest
from typing import List

from backend.core.interfaces.vectordb import Document, SearchResult
from backend.tests.conftest import FakeVectorStore


class TestFakeVectorStoreHealth:
    """Tests for vector store health check functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_returns_false_before_init(self, fake_vectordb: FakeVectorStore):
        """Health check should return False before initialization."""
        result = await fake_vectordb.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_returns_true_after_init(self, fake_vectordb: FakeVectorStore):
        """Health check should return True after initialization."""
        await fake_vectordb.initialize()
        
        result = await fake_vectordb.health_check()
        assert result is True
        
        await fake_vectordb.shutdown()
    
    @pytest.mark.asyncio
    async def test_health_check_can_be_set_unhealthy(self, fake_vectordb: FakeVectorStore):
        """Health check should return False when explicitly set unhealthy."""
        await fake_vectordb.initialize()
        fake_vectordb.set_healthy(False)
        
        result = await fake_vectordb.health_check()
        assert result is False
        
        await fake_vectordb.shutdown()


class TestFakeVectorStoreCollections:
    """Tests for vector store collection management."""
    
    @pytest.mark.asyncio
    async def test_create_collection(self, fake_vectordb: FakeVectorStore):
        """Should create a new collection."""
        await fake_vectordb.initialize()
        
        await fake_vectordb.create_collection("test_collection", 384)
        
        collections = await fake_vectordb.list_collections()
        assert "test_collection" in collections
        
        await fake_vectordb.shutdown()
    
    @pytest.mark.asyncio
    async def test_delete_collection(self, fake_vectordb: FakeVectorStore):
        """Should delete an existing collection."""
        await fake_vectordb.initialize()
        await fake_vectordb.create_collection("to_delete", 384)
        
        await fake_vectordb.delete_collection("to_delete")
        
        collections = await fake_vectordb.list_collections()
        assert "to_delete" not in collections
        
        await fake_vectordb.shutdown()
    
    @pytest.mark.asyncio
    async def test_list_collections_empty(self, fake_vectordb: FakeVectorStore):
        """Should return empty list when no collections exist."""
        await fake_vectordb.initialize()
        
        collections = await fake_vectordb.list_collections()
        
        assert collections == []
        
        await fake_vectordb.shutdown()


class TestFakeVectorStoreDocuments:
    """Tests for vector store document operations."""
    
    @pytest.mark.asyncio
    async def test_upsert_documents(
        self,
        fake_vectordb: FakeVectorStore,
        sample_documents: List[Document],
    ):
        """Should insert documents into collection."""
        await fake_vectordb.initialize()
        
        await fake_vectordb.upsert("docs", sample_documents)
        
        assert fake_vectordb.get_document_count("docs") == len(sample_documents)
        
        await fake_vectordb.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_documents_by_id(
        self,
        fake_vectordb: FakeVectorStore,
        sample_documents: List[Document],
    ):
        """Should retrieve documents by ID."""
        await fake_vectordb.initialize()
        await fake_vectordb.upsert("docs", sample_documents)
        
        result = await fake_vectordb.get("docs", ["doc1", "doc2"])
        
        assert len(result) == 2
        assert result[0].id in ["doc1", "doc2"]
        
        await fake_vectordb.shutdown()
    
    @pytest.mark.asyncio
    async def test_delete_documents(
        self,
        fake_vectordb: FakeVectorStore,
        sample_documents: List[Document],
    ):
        """Should delete documents by ID."""
        await fake_vectordb.initialize()
        await fake_vectordb.upsert("docs", sample_documents)
        
        await fake_vectordb.delete("docs", ["doc1"])
        
        assert fake_vectordb.get_document_count("docs") == len(sample_documents) - 1
        result = await fake_vectordb.get("docs", ["doc1"])
        assert len(result) == 0
        
        await fake_vectordb.shutdown()


class TestFakeVectorStoreSearch:
    """Tests for vector store search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_returns_results(
        self,
        fake_vectordb: FakeVectorStore,
        sample_documents: List[Document],
    ):
        """Should return search results."""
        await fake_vectordb.initialize()
        await fake_vectordb.upsert("docs", sample_documents)
        
        query_embedding = [0.1] * 384
        results = await fake_vectordb.search("docs", query_embedding, top_k=2)
        
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)
        
        await fake_vectordb.shutdown()
    
    @pytest.mark.asyncio
    async def test_search_with_filter(
        self,
        fake_vectordb: FakeVectorStore,
        sample_documents: List[Document],
    ):
        """Should filter results by metadata."""
        await fake_vectordb.initialize()
        await fake_vectordb.upsert("docs", sample_documents)
        
        query_embedding = [0.1] * 384
        results = await fake_vectordb.search(
            "docs",
            query_embedding,
            top_k=10,
            filter={"category": "programming"},
        )
        
        assert all(r.document.metadata.get("category") == "programming" for r in results)
        
        await fake_vectordb.shutdown()
    
    @pytest.mark.asyncio
    async def test_search_empty_collection(self, fake_vectordb: FakeVectorStore):
        """Should return empty results for non-existent collection."""
        await fake_vectordb.initialize()
        
        query_embedding = [0.1] * 384
        results = await fake_vectordb.search("nonexistent", query_embedding)
        
        assert results == []
        
        await fake_vectordb.shutdown()

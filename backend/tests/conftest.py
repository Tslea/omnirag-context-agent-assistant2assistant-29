"""
Pytest Configuration and Shared Fixtures

This file is automatically loaded by pytest and provides:
- Fake provider implementations for isolated testing
- Shared fixtures for common test scenarios
- Environment variable overrides for test configuration

Run tests:
    pytest backend/tests/ -v
    pytest backend/tests/ -v --cov=backend  # with coverage
"""

import os
import pytest
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field

# Set test environment before importing backend modules
os.environ["OMNI_LLM__PROVIDER"] = "fake"
os.environ["OMNI_VECTORDB__PROVIDER"] = "fake"
os.environ["OMNI_ENV"] = "test"

from backend.core.interfaces.llm import (
    LLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMRole,
)
# Alias for compatibility
MessageRole = LLMRole
from backend.core.interfaces.vectordb import (
    VectorDBProvider,
    CollectionConfig,
    Document,
    SearchResult,
)
# Alias for compatibility
VectorDBConfig = CollectionConfig
from backend.core.interfaces.agent import AgentConfig


# =============================================================================
# FAKE LLM PROVIDER
# =============================================================================

class FakeLLMProvider(LLMProvider):
    """
    Fake LLM provider for testing purposes.
    
    This provider returns predictable, configurable responses
    without making any external API calls.
    
    Usage:
        provider = FakeLLMProvider(config)
        provider.set_response("Hello, I'm a fake assistant!")
        response = await provider.complete([...])
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._initialized = False
        self._healthy = True
        self._response_text = "This is a fake response."
        self._stream_chunks = ["This ", "is ", "a ", "streamed ", "response."]
        self._embeddings: Dict[str, List[float]] = {}
        self._call_count = 0
        self._last_messages: List[LLMMessage] = []
    
    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "fake"
    
    @property
    def is_available(self) -> bool:
        """Always available for testing."""
        return True
    
    # Test helpers
    def set_response(self, text: str) -> None:
        """Set the response text for complete() calls."""
        self._response_text = text
    
    def set_stream_chunks(self, chunks: List[str]) -> None:
        """Set the chunks for stream() calls."""
        self._stream_chunks = chunks
    
    def set_healthy(self, healthy: bool) -> None:
        """Set the health status."""
        self._healthy = healthy
    
    def set_embedding(self, text: str, embedding: List[float]) -> None:
        """Set a specific embedding for a text."""
        self._embeddings[text] = embedding
    
    def get_call_count(self) -> int:
        """Get the number of times complete() was called."""
        return self._call_count
    
    def get_last_messages(self) -> List[LLMMessage]:
        """Get the messages from the last complete() call."""
        return self._last_messages
    
    # LLMProvider interface implementation
    async def initialize(self) -> None:
        """Initialize the fake provider."""
        self._initialized = True
    
    async def shutdown(self) -> None:
        """Shutdown the fake provider."""
        self._initialized = False
    
    async def health_check(self) -> bool:
        """Return configured health status."""
        return self._healthy and self._initialized
    
    async def complete(
        self,
        messages: List[LLMMessage],
        config: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Return the configured fake response."""
        self._call_count += 1
        self._last_messages = messages
        
        return LLMResponse(
            content=self._response_text,
            model=self.config.model,
            usage={
                "prompt_tokens": sum(len(m.content.split()) for m in messages),
                "completion_tokens": len(self._response_text.split()),
                "total_tokens": 0,  # Will be calculated
            },
            finish_reason="stop",
        )
    
    async def stream(
        self,
        messages: List[LLMMessage],
        config: Optional[Any] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream the configured chunks."""
        self._call_count += 1
        self._last_messages = messages
        
        for chunk in self._stream_chunks:
            yield chunk
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Return configured or default embeddings."""
        results = []
        for text in texts:
            if text in self._embeddings:
                results.append(self._embeddings[text])
            else:
                # Default: 384-dimensional zero vector with hash-based variation
                embedding = [0.0] * 384
                for i, char in enumerate(text[:384]):
                    embedding[i] = ord(char) / 1000.0
                results.append(embedding)
        return results


# =============================================================================
# FAKE VECTOR STORE
# =============================================================================

class FakeVectorStore(VectorDBProvider):
    """
    Fake vector store for testing purposes.
    
    This provider stores documents in memory and provides
    basic similarity search using exact match on embeddings.
    
    Usage:
        store = FakeVectorStore(config)
        await store.upsert("collection", [doc1, doc2])
        results = await store.search("collection", [0.1, 0.2, ...])
    """
    
    def __init__(self, config: VectorDBConfig):
        self.config = config
        self._initialized = False
        self._healthy = True
        self._collections: Dict[str, Dict[str, Document]] = {}
        self._embeddings: Dict[str, Dict[str, List[float]]] = {}
    
    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "fake"
    
    @property
    def is_available(self) -> bool:
        """Always available for testing."""
        return True
    
    async def collection_exists(self, name: str) -> bool:
        """Check if collection exists."""
        return name in self._collections
    
    async def count(self, collection: str) -> int:
        """Count documents in collection."""
        return len(self._collections.get(collection, {}))
    
    # Test helpers
    def set_healthy(self, healthy: bool) -> None:
        """Set the health status."""
        self._healthy = healthy
    
    def get_collection_count(self) -> int:
        """Get the number of collections."""
        return len(self._collections)
    
    def get_document_count(self, collection: str) -> int:
        """Get the number of documents in a collection."""
        return len(self._collections.get(collection, {}))
    
    # VectorDBProvider interface implementation
    async def initialize(self) -> None:
        """Initialize the fake store."""
        self._initialized = True
    
    async def shutdown(self) -> None:
        """Shutdown the fake store."""
        self._initialized = False
        self._collections.clear()
        self._embeddings.clear()
    
    async def health_check(self) -> bool:
        """Return configured health status."""
        return self._healthy and self._initialized
    
    async def create_collection(
        self,
        name: str,
        dimension: int,
        **kwargs: Any,
    ) -> None:
        """Create a new collection."""
        if name not in self._collections:
            self._collections[name] = {}
            self._embeddings[name] = {}
    
    async def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        self._collections.pop(name, None)
        self._embeddings.pop(name, None)
    
    async def list_collections(self) -> List[str]:
        """List all collections."""
        return list(self._collections.keys())
    
    async def upsert(
        self,
        collection: str,
        documents: List[Document],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """Insert or update documents."""
        if collection not in self._collections:
            await self.create_collection(collection, 384)
        
        for i, doc in enumerate(documents):
            self._collections[collection][doc.id] = doc
            if embeddings and i < len(embeddings):
                self._embeddings[collection][doc.id] = embeddings[i]
    
    async def search(
        self,
        collection: str,
        query_embedding: List[float] = None,
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        query_text: str = None,
    ) -> List[SearchResult]:
        """Search for similar documents."""
        if collection not in self._collections:
            return []
        
        results = []
        for doc_id, doc in self._collections[collection].items():
            # Simple scoring: inverse of embedding distance or metadata match
            score = 0.5  # Default score
            
            # If query_text provided, do simple text matching
            if query_text and query_text.lower() in doc.content.lower():
                score = 0.9
            
            if query_embedding and doc_id in self._embeddings.get(collection, {}):
                stored_emb = self._embeddings[collection][doc_id]
                # Simple cosine-like similarity
                if len(stored_emb) == len(query_embedding):
                    dot_product = sum(a * b for a, b in zip(stored_emb, query_embedding))
                    score = min(1.0, max(0.0, dot_product / 100.0))
            
            # Apply filter if provided
            if filter:
                matches_filter = all(
                    doc.metadata.get(k) == v
                    for k, v in filter.items()
                )
                if not matches_filter:
                    continue
            
            results.append(SearchResult(document=doc, score=score))
        
        # Sort by score descending and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
    
    async def delete(
        self,
        collection: str,
        ids: List[str],
    ) -> None:
        """Delete documents by ID."""
        if collection in self._collections:
            for doc_id in ids:
                self._collections[collection].pop(doc_id, None)
                self._embeddings.get(collection, {}).pop(doc_id, None)
    
    async def get(
        self,
        collection: str,
        ids: List[str],
    ) -> List[Document]:
        """Get documents by ID."""
        if collection not in self._collections:
            return []
        
        return [
            self._collections[collection][doc_id]
            for doc_id in ids
            if doc_id in self._collections[collection]
        ]


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture
def llm_config() -> LLMConfig:
    """Create a test LLM configuration."""
    return LLMConfig(
        provider="fake",
        model="fake-model",
        api_key="fake-api-key",
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture
def fake_llm(llm_config: LLMConfig) -> FakeLLMProvider:
    """Create a FakeLLMProvider instance."""
    return FakeLLMProvider(llm_config)


@pytest.fixture
def vectordb_config() -> VectorDBConfig:
    """Create a test VectorDB configuration."""
    return VectorDBConfig(
        provider="fake",
        host="localhost",
        port=6333,
        collection_name="test_collection",
    )


@pytest.fixture
def fake_vectordb(vectordb_config: VectorDBConfig) -> FakeVectorStore:
    """Create a FakeVectorStore instance."""
    return FakeVectorStore(vectordb_config)


@pytest.fixture
def agent_config() -> AgentConfig:
    """Create a test agent configuration."""
    return AgentConfig(
        name="test-agent",
        description="A test agent",
        system_prompt="You are a helpful test assistant.",
        model="fake-model",
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture
def sample_documents() -> List[Document]:
    """Create sample documents for testing."""
    return [
        Document(
            id="doc1",
            content="Python is a programming language.",
            metadata={"category": "programming", "lang": "en"},
        ),
        Document(
            id="doc2",
            content="Machine learning uses algorithms to learn from data.",
            metadata={"category": "ml", "lang": "en"},
        ),
        Document(
            id="doc3",
            content="Vector databases store embeddings for similarity search.",
            metadata={"category": "databases", "lang": "en"},
        ),
    ]


@pytest.fixture
def sample_messages() -> List[LLMMessage]:
    """Create sample LLM messages for testing."""
    return [
        LLMMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        LLMMessage(role=MessageRole.USER, content="Hello, how are you?"),
    ]

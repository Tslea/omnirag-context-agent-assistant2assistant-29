"""
Fake Provider Implementations for Testing

These providers simulate real backends without external dependencies,
enabling fast, isolated, and deterministic tests.

Usage:
    from backend.tests.fakes import FakeLLMProvider, FakeVectorStore
    
    # Create providers with test config
    llm = FakeLLMProvider(config)
    llm.set_response("Custom response")
    
    vectordb = FakeVectorStore(config)
    await vectordb.upsert("collection", documents)
"""

from backend.tests.conftest import FakeLLMProvider, FakeVectorStore

__all__ = ["FakeLLMProvider", "FakeVectorStore"]

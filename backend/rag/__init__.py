"""
RAG (Retrieval-Augmented Generation) Module

Provides optional RAG functionality using LlamaIndex as an orchestration layer.
This module is completely optional and disabled by default.

Key features:
- Domain-based indices (code, security, compliance)
- Context versioning on file save
- Works with existing VectorDB adapters

Usage:
    from backend.rag import RAGService
    
    # Initialize (will be no-op if disabled)
    rag = RAGService(settings)
    if rag.is_available():
        context = await rag.query("security", "authentication patterns")
"""

from backend.rag.service import RAGService, RAGConfig

__all__ = ["RAGService", "RAGConfig"]

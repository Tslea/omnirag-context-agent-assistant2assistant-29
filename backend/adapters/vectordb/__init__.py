"""
Vector Database Adapters Package

Provides concrete implementations of the VectorDBProvider interface
for various vector databases (Qdrant, Chroma, FAISS, etc.)
"""

from backend.adapters.vectordb.base import BaseVectorDBAdapter
from backend.adapters.vectordb.qdrant_adapter import QdrantAdapter
from backend.adapters.vectordb.chroma_adapter import ChromaAdapter
from backend.adapters.vectordb.faiss_adapter import FAISSAdapter
from backend.adapters.vectordb.factory import VectorDBFactory

__all__ = [
    "BaseVectorDBAdapter",
    "QdrantAdapter",
    "ChromaAdapter",
    "FAISSAdapter",
    "VectorDBFactory",
]

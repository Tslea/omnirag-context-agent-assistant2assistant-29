"""
RAG Service using LlamaIndex

Provides retrieval-augmented generation using LlamaIndex as an orchestration layer.
LlamaIndex is OPTIONAL - the system works without it.

This service:
- Uses existing VectorDB adapters (no changes to adapter interface)
- Supports domain-based indices (code, security, compliance)
- Tracks context versions per file
- Is completely disabled by default

Safety guarantees:
- If LlamaIndex is not installed, service returns empty results (no crash)
- If rag.enabled=false, all operations are no-ops
- Existing VectorDB adapters are NOT modified
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from backend.utils.gitignore import load_gitignore, should_ignore

logger = logging.getLogger(__name__)

# LlamaIndex imports are conditional
LLAMAINDEX_AVAILABLE = False
try:
    from llama_index.core import (
        VectorStoreIndex,
        Document as LlamaDocument,
        Settings as LlamaSettings,
        StorageContext,
    )
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.core.retrievers import VectorIndexRetriever
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.schema import TextNode
    LLAMAINDEX_AVAILABLE = True
    logger.info("LlamaIndex is available")
except ImportError:
    logger.info("LlamaIndex not installed - RAG features disabled")


@dataclass
class RAGConfig:
    """RAG configuration."""
    enabled: bool = False
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    score_threshold: float = 0.7
    index_persist_path: str = "./data/rag_indices"
    
    # Domain-specific settings
    domains: dict[str, dict[str, Any]] = field(default_factory=lambda: {
        "code": {
            "enabled": True,
            "file_patterns": ["*.py", "*.ts", "*.js", "*.java", "*.go"],
            "chunk_size": 256,  # Smaller chunks for code
        },
        "security": {
            "enabled": True,
            "file_patterns": ["*.md", "*.txt", "*.yaml", "*.json"],
            "chunk_size": 512,
        },
        "compliance": {
            "enabled": True,
            "file_patterns": ["*.md", "*.txt", "*.yaml"],
            "chunk_size": 1024,  # Larger chunks for policy docs
        },
    })


@dataclass
class ContextVersion:
    """Tracks version of indexed content."""
    file_path: str
    content_hash: str
    indexed_at: datetime
    domain: str
    node_ids: list[str] = field(default_factory=list)


@dataclass
class RAGResult:
    """Result from RAG query."""
    content: str
    source: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class RAGService:
    """
    RAG Service using LlamaIndex for orchestration.
    
    This service is:
    - Completely optional (disabled by default)
    - Safe if LlamaIndex is not installed
    - Uses existing VectorDB adapters via LlamaIndex adapters
    
    Example:
        ```python
        config = RAGConfig(enabled=True)
        rag = RAGService(config, vectordb_provider)
        
        # Ingest documents
        await rag.ingest_file("code", "/path/to/file.py")
        
        # Query
        results = await rag.query("code", "authentication logic")
        ```
    """
    
    def __init__(
        self,
        config: RAGConfig,
        vectordb_provider: Optional[Any] = None,
        llm_provider: Optional[Any] = None,
    ):
        self.config = config
        self._vectordb = vectordb_provider
        self._llm = llm_provider
        
        # Domain indices (LlamaIndex VectorStoreIndex per domain)
        self._indices: dict[str, Any] = {}
        
        # Context versioning
        self._versions: dict[str, ContextVersion] = {}
        
        # Initialization state
        self._initialized = False
    
    def is_available(self) -> bool:
        """Check if RAG functionality is available."""
        return self.config.enabled and LLAMAINDEX_AVAILABLE
    
    async def initialize(self) -> None:
        """Initialize RAG service."""
        if not self.is_available():
            logger.info("RAG not available (disabled or LlamaIndex not installed)")
            return
        
        logger.info("Initializing RAG service...")
        
        # Create persist directory
        persist_path = Path(self.config.index_persist_path)
        persist_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize domain indices
        for domain, domain_config in self.config.domains.items():
            if domain_config.get("enabled", False):
                await self._init_domain_index(domain, domain_config)
        
        self._initialized = True
        logger.info(f"RAG initialized with domains: {list(self._indices.keys())}")
    
    async def _init_domain_index(
        self,
        domain: str,
        domain_config: dict[str, Any],
    ) -> None:
        """Initialize a domain-specific index."""
        if not LLAMAINDEX_AVAILABLE:
            return
        
        persist_path = Path(self.config.index_persist_path) / domain
        
        try:
            if persist_path.exists():
                # Load existing index
                storage_context = StorageContext.from_defaults(
                    persist_dir=str(persist_path)
                )
                self._indices[domain] = VectorStoreIndex.from_storage_context(
                    storage_context
                )
                logger.info(f"Loaded existing index for domain: {domain}")
            else:
                # Create new empty index
                persist_path.mkdir(parents=True, exist_ok=True)
                self._indices[domain] = VectorStoreIndex([])
                logger.info(f"Created new index for domain: {domain}")
        except Exception as e:
            logger.error(f"Failed to initialize domain index '{domain}': {e}")
    
    async def ingest_file(
        self,
        domain: str,
        file_path: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Ingest a file into a domain index.
        
        Performs content versioning - only re-indexes if content changed.
        
        Args:
            domain: Target domain (code, security, compliance)
            file_path: Path to file to ingest
            metadata: Optional additional metadata
            
        Returns:
            True if file was ingested, False if skipped or failed
        """
        if not self.is_available():
            return False
        
        if domain not in self._indices:
            logger.warning(f"Domain '{domain}' not initialized")
            return False
        
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                return False
            
            # Read content and compute hash
            content = path.read_text(encoding="utf-8", errors="ignore")
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Check if content has changed
            version_key = f"{domain}:{file_path}"
            existing_version = self._versions.get(version_key)
            
            if existing_version and existing_version.content_hash == content_hash:
                logger.debug(f"Skipping unchanged file: {file_path}")
                return False
            
            # Remove old nodes if re-indexing
            if existing_version:
                await self._remove_nodes(domain, existing_version.node_ids)
            
            # Chunk content
            domain_config = self.config.domains.get(domain, {})
            chunk_size = domain_config.get("chunk_size", self.config.chunk_size)
            chunk_overlap = domain_config.get("chunk_overlap", self.config.chunk_overlap)
            
            splitter = SentenceSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            
            # Create document and nodes
            doc = LlamaDocument(
                text=content,
                metadata={
                    "file_path": str(path.absolute()),
                    "file_name": path.name,
                    "domain": domain,
                    **(metadata or {}),
                },
            )
            
            nodes = splitter.get_nodes_from_documents([doc])
            
            # Add to index
            index = self._indices[domain]
            index.insert_nodes(nodes)
            
            # Update version tracking
            self._versions[version_key] = ContextVersion(
                file_path=str(file_path),
                content_hash=content_hash,
                indexed_at=datetime.utcnow(),
                domain=domain,
                node_ids=[n.node_id for n in nodes],
            )
            
            logger.info(f"Ingested {len(nodes)} nodes from {file_path} into {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            return False
    
    async def _remove_nodes(self, domain: str, node_ids: list[str]) -> None:
        """Remove nodes from a domain index."""
        if domain not in self._indices:
            return
        
        try:
            index = self._indices[domain]
            for node_id in node_ids:
                index.delete_ref_doc(node_id, delete_from_docstore=True)
        except Exception as e:
            logger.warning(f"Failed to remove some nodes: {e}")
    
    async def ingest_directory(
        self,
        domain: str,
        directory: str,
        recursive: bool = True,
    ) -> int:
        """
        Ingest all matching files from a directory.
        
        Args:
            domain: Target domain
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            Number of files ingested
        """
        if not self.is_available():
            return 0
        
        domain_config = self.config.domains.get(domain, {})
        patterns = domain_config.get("file_patterns", ["*.*"])
        
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Directory not found: {directory}")
            return 0
        
        ignore_spec = load_gitignore(dir_path)
        seen: set[Path] = set()
        count = 0
        for pattern in patterns:
            glob_method = dir_path.rglob if recursive else dir_path.glob
            for file_path in glob_method(pattern):
                if not file_path.is_file():
                    continue

                if file_path in seen:
                    continue

                if should_ignore(file_path, dir_path, ignore_spec):
                    logger.debug(f"Skipping ignored file during ingest: {file_path}")
                    continue

                seen.add(file_path)

                if await self.ingest_file(domain, str(file_path)):
                    count += 1
        
        return count
    
    async def query(
        self,
        domain: str,
        query_text: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[RAGResult]:
        """
        Query a domain index for relevant context.
        
        Args:
            domain: Domain to query
            query_text: Query string
            top_k: Number of results (default from config)
            score_threshold: Minimum relevance score
            filters: Optional metadata filters
            
        Returns:
            List of RAG results sorted by relevance
        """
        if not self.is_available():
            return []
        
        if domain not in self._indices:
            logger.warning(f"Domain '{domain}' not initialized")
            return []
        
        try:
            index = self._indices[domain]
            
            # Create retriever
            retriever = VectorIndexRetriever(
                index=index,
                similarity_top_k=top_k or self.config.top_k,
            )
            
            # Retrieve nodes
            nodes = retriever.retrieve(query_text)
            
            # Apply score threshold
            threshold = score_threshold or self.config.score_threshold
            
            results = []
            for node in nodes:
                if node.score >= threshold:
                    results.append(RAGResult(
                        content=node.text,
                        source=node.metadata.get("file_path", "unknown"),
                        score=node.score,
                        metadata=dict(node.metadata),
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"Query failed for domain '{domain}': {e}")
            return []
    
    async def query_multiple_domains(
        self,
        domains: list[str],
        query_text: str,
        top_k: Optional[int] = None,
    ) -> list[RAGResult]:
        """
        Query multiple domains and merge results.
        
        Args:
            domains: List of domains to query
            query_text: Query string
            top_k: Total number of results
            
        Returns:
            Merged results sorted by score
        """
        all_results = []
        
        for domain in domains:
            results = await self.query(domain, query_text, top_k=top_k)
            all_results.extend(results)
        
        # Sort by score and limit
        all_results.sort(key=lambda r: r.score, reverse=True)
        
        if top_k:
            all_results = all_results[:top_k]
        
        return all_results
    
    def get_context_for_prompt(
        self,
        results: list[RAGResult],
        max_tokens: int = 2000,
    ) -> str:
        """
        Format RAG results as context for LLM prompt.
        
        Args:
            results: RAG query results
            max_tokens: Approximate token limit
            
        Returns:
            Formatted context string
        """
        if not results:
            return ""
        
        context_parts = ["## Relevant Context\n"]
        
        # Rough token estimate: 4 chars per token
        max_chars = max_tokens * 4
        current_chars = len(context_parts[0])
        
        for i, result in enumerate(results, 1):
            entry = f"\n### Source: {result.source}\n```\n{result.content}\n```\n"
            
            if current_chars + len(entry) > max_chars:
                break
            
            context_parts.append(entry)
            current_chars += len(entry)
        
        return "".join(context_parts)
    
    async def persist(self) -> None:
        """Persist all indices to disk."""
        if not self.is_available():
            return
        
        for domain, index in self._indices.items():
            try:
                persist_path = Path(self.config.index_persist_path) / domain
                index.storage_context.persist(persist_dir=str(persist_path))
                logger.info(f"Persisted index for domain: {domain}")
            except Exception as e:
                logger.error(f"Failed to persist domain '{domain}': {e}")
    
    async def shutdown(self) -> None:
        """Shutdown RAG service."""
        if self._initialized:
            await self.persist()
            self._indices.clear()
            self._versions.clear()
            self._initialized = False
            logger.info("RAG service shutdown complete")


# Singleton instance management
_rag_service: Optional[RAGService] = None


def get_rag_service() -> Optional[RAGService]:
    """Get the global RAG service instance."""
    return _rag_service


def set_rag_service(service: RAGService) -> None:
    """Set the global RAG service instance."""
    global _rag_service
    _rag_service = service

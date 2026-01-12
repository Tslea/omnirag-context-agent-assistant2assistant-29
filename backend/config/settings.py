"""
Settings Model

Pydantic-based settings with YAML and environment variable support.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ServerSettings(BaseModel):
    """WebSocket server settings."""
    host: str = "localhost"
    port: int = 8765
    cors_origins: list[str] = ["vscode-webview://*", "http://localhost:*"]
    debug: bool = False
    log_level: str = "INFO"


class OpenAISettings(BaseModel):
    """OpenAI provider settings."""
    api_key: Optional[str] = None
    model: str = "gpt-4-turbo-preview"
    embedding_model: str = "text-embedding-3-small"
    max_tokens: int = 4096
    temperature: float = 0.7


class AnthropicSettings(BaseModel):
    """Anthropic provider settings."""
    api_key: Optional[str] = None
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7


class LocalLLMSettings(BaseModel):
    """Local LLM provider settings."""
    provider_type: str = "lmstudio"
    base_url: str = "http://localhost:1234/v1"
    model: str = "local-model"
    temperature: float = 0.7


class LLMSettings(BaseModel):
    """LLM configuration."""
    provider: str = "openai"
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)
    local: LocalLLMSettings = Field(default_factory=LocalLLMSettings)


class QdrantSettings(BaseModel):
    """Qdrant settings."""
    url: Optional[str] = None
    api_key: Optional[str] = None
    prefer_grpc: bool = False


class ChromaSettings(BaseModel):
    """ChromaDB settings."""
    persist_path: str = "./data/chroma"


class FAISSSettings(BaseModel):
    """FAISS settings."""
    persist_path: str = "./data/faiss"


class VectorDBSettings(BaseModel):
    """Vector database configuration."""
    provider: str = "chroma"
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    faiss: FAISSSettings = Field(default_factory=FAISSSettings)
    default_collection: str = "omni_documents"
    default_dimension: int = 1536


class RAGSettings(BaseModel):
    """RAG configuration."""
    enabled: bool = True
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    score_threshold: float = 0.7


class AgentSettings(BaseModel):
    """Agent configuration."""
    plugin_dirs: list[str] = ["./plugins/agents"]
    default_agents: list[str] = [
        "context_agent",
        "rag_agent",
        "security",
        "compliance",
        "assistant",
        "code_agent",
        "planner",
    ]


class WorkflowSettings(BaseModel):
    """Workflow configuration."""
    plugin_dirs: list[str] = ["./plugins/workflows"]
    default_timeout: int = 300
    step_timeout: int = 60


class LoggingSettings(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = "./logs/omni.log"
    max_size: int = 10485760
    backup_count: int = 5


class SecuritySettings(BaseModel):
    """Security configuration."""
    api_key: Optional[str] = None
    require_auth: bool = False
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]


class FeatureFlags(BaseModel):
    """Feature flags."""
    enable_streaming: bool = True
    enable_tool_use: bool = True
    enable_multi_agent: bool = True
    enable_rag: bool = True
    enable_code_execution: bool = False


class Settings(BaseSettings):
    """
    Main settings class.
    
    Loads configuration from:
    1. Default values
    2. YAML config file
    3. Environment variables (OMNI_ prefix)
    
    Example:
        ```python
        settings = get_settings()
        print(settings.llm.provider)
        print(settings.server.port)
        ```
    """
    
    server: ServerSettings = Field(default_factory=ServerSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    vectordb: VectorDBSettings = Field(default_factory=VectorDBSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    agents: AgentSettings = Field(default_factory=AgentSettings)
    workflows: WorkflowSettings = Field(default_factory=WorkflowSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    
    model_config = {
        "env_prefix": "OMNI_",
        "env_nested_delimiter": "__",
        "extra": "ignore",
    }
    
    @classmethod
    def from_yaml(cls, path: str) -> "Settings":
        """Load settings from YAML file."""
        from backend.config.loader import ConfigLoader
        
        loader = ConfigLoader()
        data = loader.load_yaml(path)
        return cls(**data)
    
    def get_llm_config(self) -> dict[str, Any]:
        """Get configuration for the active LLM provider."""
        provider = self.llm.provider.lower()
        
        if provider == "openai":
            return {
                "provider": "openai",
                "api_key": self.llm.openai.api_key or os.getenv("OPENAI_API_KEY"),
                "default_model": self.llm.openai.model,
                "default_embedding_model": self.llm.openai.embedding_model,
            }
        elif provider == "anthropic":
            return {
                "provider": "anthropic",
                "api_key": self.llm.anthropic.api_key or os.getenv("ANTHROPIC_API_KEY"),
                "default_model": self.llm.anthropic.model,
            }
        elif provider == "local":
            return {
                "provider": "local",
                "provider_type": self.llm.local.provider_type,
                "base_url": self.llm.local.base_url,
                "default_model": self.llm.local.model,
            }
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    def get_vectordb_config(self) -> dict[str, Any]:
        """Get configuration for the active vector database."""
        provider = self.vectordb.provider.lower()
        
        if provider == "qdrant":
            return {
                "provider": "qdrant",
                "url": self.vectordb.qdrant.url or os.getenv("QDRANT_URL"),
                "api_key": self.vectordb.qdrant.api_key or os.getenv("QDRANT_API_KEY"),
                "prefer_grpc": self.vectordb.qdrant.prefer_grpc,
            }
        elif provider == "chroma":
            return {
                "provider": "chroma",
                "persist_path": self.vectordb.chroma.persist_path,
            }
        elif provider == "faiss":
            return {
                "provider": "faiss",
                "persist_path": self.vectordb.faiss.persist_path,
            }
        else:
            raise ValueError(f"Unknown vector DB provider: {provider}")


# Singleton settings instance
_settings: Optional[Settings] = None


def get_settings(config_path: Optional[str] = None) -> Settings:
    """
    Get the settings singleton.
    
    Args:
        config_path: Optional path to YAML config file
        
    Returns:
        Settings instance
    """
    global _settings
    
    if _settings is None:
        if config_path and Path(config_path).exists():
            _settings = Settings.from_yaml(config_path)
        else:
            # Try default config path
            default_path = Path(__file__).parent / "default.yaml"
            if default_path.exists():
                _settings = Settings.from_yaml(str(default_path))
            else:
                _settings = Settings()
    
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (for testing)."""
    global _settings
    _settings = None

"""
Context Agent

Manages global session context, memory, and inter-agent coordination.
This agent is always active and processes every message to maintain state.

This agent:
- Extracts important information from messages
- Maintains session summary and memory
- Coordinates findings between agents
- Manages conversation history intelligently

Safety guarantees:
- Read-only: Does not write files
- Passive: Does not initiate actions
- Optional LLM: Works without LLM (uses pattern matching)
- Non-blocking: Failures don't stop other agents
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from backend.core.interfaces.agent import (
    AgentBase,
    AgentMetadata,
    AgentCapability,
    AgentMessage,
    AgentContext,
    MessageType,
    AgentStatus,
)
from backend.core.interfaces.llm import LLMProvider, LLMMessage, LLMRole, LLMConfig
from backend.core.state import StateVersion
from backend.utils.gitignore import load_gitignore, should_ignore

logger = logging.getLogger(__name__)


@dataclass
class DetailedFileSummary:
    """
    Detailed summary of a single file - the UNIFIED format.
    
    This replaces the old short summaries (~200 chars) with comprehensive
    information that's useful for both runtime queries and Copilot files.
    
    Memory cost: ~1-2KB per file vs ~200 bytes for short summaries.
    For a 500-file project: ~1MB vs ~100KB - acceptable tradeoff for utility.
    """
    file_path: str
    relative_path: str
    language: str
    lines_of_code: int
    
    # Structure
    classes: list[dict] = field(default_factory=list)  # [{name, methods, docstring, base_classes}]
    functions: list[dict] = field(default_factory=list)  # [{name, params, returns, docstring, is_async}]
    imports: dict[str, list[str]] = field(default_factory=dict)  # {internal: [], external: []}
    exports: list[str] = field(default_factory=list)
    constants: list[str] = field(default_factory=list)
    
    # Purpose (semantic understanding)
    purpose: str = ""
    key_responsibilities: list[str] = field(default_factory=list)
    module_docstring: str = ""
    
    # Quality indicators
    has_type_hints: bool = False
    has_docstrings: bool = False
    is_test_file: bool = False
    
    # Security/Compliance flags
    security_flags: list[str] = field(default_factory=list)
    compliance_flags: list[str] = field(default_factory=list)
    
    # Metadata
    last_analyzed: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return {
            "file_path": self.file_path,
            "relative_path": self.relative_path,
            "language": self.language,
            "lines_of_code": self.lines_of_code,
            "classes": self.classes,
            "functions": self.functions,
            "imports": self.imports,
            "exports": self.exports,
            "constants": self.constants,
            "purpose": self.purpose,
            "key_responsibilities": self.key_responsibilities,
            "module_docstring": self.module_docstring,
            "has_type_hints": self.has_type_hints,
            "has_docstrings": self.has_docstrings,
            "is_test_file": self.is_test_file,
            "security_flags": self.security_flags,
            "compliance_flags": self.compliance_flags,
            "last_analyzed": self.last_analyzed.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DetailedFileSummary":
        """Deserialize from dict."""
        last_analyzed = data.get("last_analyzed")
        if isinstance(last_analyzed, str):
            try:
                last_analyzed = datetime.fromisoformat(last_analyzed)
            except (ValueError, TypeError):
                last_analyzed = datetime.utcnow()
        else:
            last_analyzed = datetime.utcnow()
            
        return cls(
            file_path=data.get("file_path", ""),
            relative_path=data.get("relative_path", ""),
            language=data.get("language", "unknown"),
            lines_of_code=data.get("lines_of_code", 0),
            classes=data.get("classes", []),
            functions=data.get("functions", []),
            imports=data.get("imports", {}),
            exports=data.get("exports", []),
            constants=data.get("constants", []),
            purpose=data.get("purpose", ""),
            key_responsibilities=data.get("key_responsibilities", []),
            module_docstring=data.get("module_docstring", ""),
            has_type_hints=data.get("has_type_hints", False),
            has_docstrings=data.get("has_docstrings", False),
            is_test_file=data.get("is_test_file", False),
            security_flags=data.get("security_flags", []),
            compliance_flags=data.get("compliance_flags", []),
            last_analyzed=last_analyzed,
        )
    
    def to_compact_string(self) -> str:
        """Generate compact string for quick lookups (backwards compatibility)."""
        parts = [f"{self.language}, {self.lines_of_code} lines"]
        if self.classes:
            class_names = [c.get("name", "?") for c in self.classes[:3]]
            parts.append(f"classes: {', '.join(class_names)}")
        if self.functions:
            func_names = [f.get("name", "?") for f in self.functions[:5]]
            parts.append(f"funcs: {', '.join(func_names)}")
        if self.purpose:
            parts.append(self.purpose[:100])
        return " | ".join(parts)[:300]
    
    def to_compact_dict(self) -> dict[str, Any]:
        """
        Generate a smaller dict for JSON (omits empty/default values).
        
        Reduces JSON size by ~40-60%.
        """
        d: dict[str, Any] = {
            "p": self.relative_path,  # shortened key
            "l": self.language,
            "n": self.lines_of_code,
        }
        if self.purpose:
            d["pu"] = self.purpose
        if self.classes:
            # Only name and method count
            d["c"] = [{"n": c.get("name"), "m": len(c.get("methods", []))} for c in self.classes]
        if self.functions:
            # Only name and params
            d["f"] = [{"n": f.get("name"), "p": len(f.get("params", []))} for f in self.functions]
        if self.security_flags:
            d["sf"] = self.security_flags
        if self.compliance_flags:
            d["cf"] = self.compliance_flags
        return d
    
    def to_markdown(self) -> str:
        """Generate markdown summary for Copilot files."""
        lines = [f"### `{self.relative_path}`"]
        lines.append(f"**Language:** {self.language} | **Lines:** {self.lines_of_code}")
        
        if self.purpose:
            lines.append(f"\n**Purpose:** {self.purpose}")
        
        if self.key_responsibilities:
            lines.append("\n**Responsibilities:**")
            for resp in self.key_responsibilities[:5]:
                lines.append(f"- {resp}")
        
        if self.classes:
            lines.append("\n**Classes:**")
            for cls in self.classes[:5]:
                methods = ", ".join(cls.get("methods", [])[:5])
                if len(cls.get("methods", [])) > 5:
                    methods += f" (+{len(cls['methods']) - 5} more)"
                lines.append(f"- `{cls.get('name', '?')}`: {cls.get('docstring', '')[:80]}")
                if methods:
                    lines.append(f"  - Methods: {methods}")
        
        if self.functions:
            lines.append("\n**Functions:**")
            for func in self.functions[:10]:
                params = ", ".join(func.get("params", []))
                returns = func.get("returns", "")
                sig = f"`{func.get('name', '?')}({params})`"
                if returns:
                    sig += f" → `{returns}`"
                lines.append(f"- {sig}")
            if len(self.functions) > 10:
                lines.append(f"- ... and {len(self.functions) - 10} more functions")
        
        if self.imports.get("external"):
            key_imports = [i for i in self.imports["external"] if not i.startswith("__")][:5]
            if key_imports:
                lines.append(f"\n**Key Imports:** {', '.join(key_imports)}")
        
        if self.imports.get("internal"):
            lines.append(f"\n**Depends on:** {', '.join(self.imports['internal'][:5])}")
        
        if self.security_flags:
            lines.append("\n**⚠️ Security Notes:**")
            for flag in self.security_flags:
                lines.append(f"- {flag}")
        
        if self.compliance_flags:
            lines.append("\n**📋 Compliance Notes:**")
            for flag in self.compliance_flags:
                lines.append(f"- {flag}")
        
        lines.append("")
        return "\n".join(lines)


@dataclass
class ContextAgentConfig:
    """Configuration for Context Agent."""
    enabled: bool = True
    max_history: int = 100
    summarize_after: int = 20
    max_facts: int = 50
    use_llm_for_extraction: bool = False  # Disabled by default
    use_llm_for_summarization: bool = False  # Disabled by default
    
    # NEW: Project structure awareness
    track_project_structure: bool = True
    auto_detect_stack: bool = True  # Detect if fullstack, backend-only, etc.
    persist_memory: bool = True  # Keep memory between sessions



@dataclass
class ProjectStructure:
    """
    Persistent knowledge about the project structure.
    
    UNIFIED APPROACH: Uses DetailedFileSummary for ALL files instead of
    separate short summaries. This provides:
    - Complete semantic information for runtime queries
    - Same data used for Copilot file generation
    - JSON persistence between sessions
    - VERSION TRACKING for change detection
    
    Memory cost: ~1-2KB per file (acceptable for utility gained).
    """
    project_type: str = "unknown"  # fullstack, backend, frontend, library, cli
    backend_framework: Optional[str] = None  # FastAPI, Django, Flask, Express
    frontend_framework: Optional[str] = None  # React, Vue, Angular, Svelte
    database: Optional[str] = None  # PostgreSQL, MySQL, MongoDB, SQLite
    
    # UNIFIED: All files with detailed summaries (replaces backend_files, frontend_files, shared_files)
    files: dict[str, DetailedFileSummary] = field(default_factory=dict)  # relative_path -> DetailedFileSummary
    
    # Architecture knowledge
    api_patterns: list[str] = field(default_factory=list)  # "/api/v1/{resource}"
    component_patterns: list[str] = field(default_factory=list)  # "PascalCase.tsx"
    conventions: dict[str, str] = field(default_factory=dict)
    
    # Feature tracking
    completed_features: list[dict[str, Any]] = field(default_factory=list)
    pending_features: list[str] = field(default_factory=list)
    
    # VERSION TRACKING
    version: int = 0  # Increments on every change
    last_updated: datetime = field(default_factory=datetime.utcnow)
    last_modifier: str = "system"  # Who made the last change: copilot, user, scan, etc.
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Change history (last N changes)
    change_history: list[dict[str, Any]] = field(default_factory=list)
    
    # Persistence path (set when loading)
    _workspace_path: Optional[str] = field(default=None, repr=False)
    
    # Callbacks for change notifications
    _on_change_callbacks: list[Callable] = field(default_factory=list, repr=False)
    
    def increment_version(self, modifier: str = "system", change_description: str = "") -> None:
        """Increment version and record change."""
        self.version += 1
        self.last_updated = datetime.utcnow()
        self.last_modifier = modifier
        
        # Record in history (keep last 50 changes)
        self.change_history.append({
            "version": self.version,
            "timestamp": self.last_updated.isoformat(),
            "modifier": modifier,
            "description": change_description,
        })
        if len(self.change_history) > 50:
            self.change_history = self.change_history[-50:]
        
        # Notify callbacks
        for callback in self._on_change_callbacks:
            try:
                callback(self, self.version, modifier)
            except Exception as e:
                logger.warning(f"Error in change callback: {e}")
    
    def on_change(self, callback: Callable) -> None:
        """Register a callback for version changes."""
        self._on_change_callbacks.append(callback)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return {
            "version": self.version,
            "last_modifier": self.last_modifier,
            "project_type": self.project_type,
            "backend_framework": self.backend_framework,
            "frontend_framework": self.frontend_framework,
            "database": self.database,
            "files": {
                path: summary.to_dict() 
                for path, summary in self.files.items()
            },
            "api_patterns": self.api_patterns,
            "component_patterns": self.component_patterns,
            "conventions": self.conventions,
            "completed_features": self.completed_features,
            "pending_features": self.pending_features,
            "change_history": self.change_history,
            "last_updated": self.last_updated.isoformat(),
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any], workspace_path: Optional[str] = None) -> "ProjectStructure":
        """Reconstruct from dict (for persistence)."""
        # Parse timestamps
        last_updated = data.get("last_updated")
        created_at = data.get("created_at")
        
        if isinstance(last_updated, str):
            try:
                last_updated = datetime.fromisoformat(last_updated)
            except (ValueError, TypeError):
                last_updated = datetime.utcnow()
        else:
            last_updated = datetime.utcnow()
            
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except (ValueError, TypeError):
                created_at = datetime.utcnow()
        else:
            created_at = datetime.utcnow()
        
        # Parse files (DetailedFileSummary objects)
        files_data = data.get("files", {})
        files = {}
        for path, file_data in files_data.items():
            if isinstance(file_data, dict):
                files[path] = DetailedFileSummary.from_dict(file_data)
            elif isinstance(file_data, str):
                # Legacy: old short summary format - create minimal DetailedFileSummary
                files[path] = DetailedFileSummary(
                    file_path=path,
                    relative_path=path,
                    language=cls._guess_language(path),
                    lines_of_code=0,
                    purpose=file_data,  # Use old summary as purpose
                )
        
        # Handle legacy backend_files/frontend_files/shared_files
        for legacy_key in ["backend_files", "frontend_files", "shared_files"]:
            legacy_data = data.get(legacy_key, {})
            for path, summary in legacy_data.items():
                if path not in files:
                    files[path] = DetailedFileSummary(
                        file_path=path,
                        relative_path=path,
                        language=cls._guess_language(path),
                        lines_of_code=0,
                        purpose=summary if isinstance(summary, str) else "",
                    )
        
        return cls(
            project_type=data.get("project_type", "unknown"),
            backend_framework=data.get("backend_framework"),
            frontend_framework=data.get("frontend_framework"),
            database=data.get("database"),
            files=files,
            api_patterns=data.get("api_patterns", []),
            component_patterns=data.get("component_patterns", []),
            conventions=data.get("conventions", {}),
            completed_features=data.get("completed_features", []),
            pending_features=data.get("pending_features", []),
            version=data.get("version", 0),
            last_modifier=data.get("last_modifier", "system"),
            change_history=data.get("change_history", []),
            last_updated=last_updated,
            created_at=created_at,
            _workspace_path=workspace_path,
        )
    
    @staticmethod
    def _guess_language(file_path: str) -> str:
        """Guess language from file extension."""
        ext_map = {
            ".py": "python", ".ts": "typescript", ".tsx": "typescript",
            ".js": "javascript", ".jsx": "javascript", ".java": "java",
            ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
            ".cs": "csharp", ".swift": "swift", ".kt": "kotlin",
            ".dart": "dart", ".vue": "vue", ".svelte": "svelte",
            ".yaml": "yaml", ".yml": "yaml", ".json": "json",
        }
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        return "unknown"
    
    def get_summary_for_prompt(self) -> str:
        """
        Generate a COMPACT summary for LLM prompts.
        This is the key to saving tokens - summary instead of raw code.
        """
        parts = []
        
        # Project type
        parts.append(f"Project: {self.project_type}")
        
        # Stack
        if self.backend_framework:
            parts.append(f"Backend: {self.backend_framework}")
        if self.frontend_framework:
            parts.append(f"Frontend: {self.frontend_framework}")
        if self.database:
            parts.append(f"Database: {self.database}")
        
        # File counts by category
        backend_count = sum(1 for f in self.files.values() if self._is_backend_file(f.relative_path))
        frontend_count = sum(1 for f in self.files.values() if self._is_frontend_file(f.relative_path))
        
        if backend_count:
            parts.append(f"Backend files: {backend_count}")
        if frontend_count:
            parts.append(f"Frontend files: {frontend_count}")
        
        # Patterns
        if self.api_patterns:
            parts.append(f"API pattern: {self.api_patterns[0]}")
        
        # Features
        if self.completed_features:
            feature_names = [f.get("name", "?") for f in self.completed_features[-5:]]
            parts.append(f"Features: {', '.join(feature_names)}")
        
        return " | ".join(parts)
    
    @staticmethod
    def _is_backend_file(path: str) -> bool:
        """Check if file is backend."""
        backend_indicators = ["backend/", "server/", "api/", "services/", "models/"]
        backend_extensions = [".py", ".go", ".rs", ".java", ".rb", ".php"]
        path_lower = path.lower()
        return (
            any(ind in path_lower for ind in backend_indicators) or
            any(path_lower.endswith(ext) for ext in backend_extensions)
        )
    
    @staticmethod
    def _is_frontend_file(path: str) -> bool:
        """Check if file is frontend."""
        frontend_indicators = ["frontend/", "client/", "src/", "components/", "views/", "pages/"]
        frontend_extensions = [".tsx", ".jsx", ".vue", ".svelte"]
        path_lower = path.lower()
        return (
            any(ind in path_lower for ind in frontend_indicators) or
            any(path_lower.endswith(ext) for ext in frontend_extensions)
        )
    
    def requires_both_tiers(self) -> bool:
        """Check if changes typically need both backend and frontend."""
        return self.project_type == "fullstack"
    
    def get_file(self, relative_path: str) -> Optional[DetailedFileSummary]:
        """Get detailed summary for a specific file."""
        return self.files.get(relative_path)
    
    def get_files_by_language(self, language: str) -> list[DetailedFileSummary]:
        """Get all files of a specific language."""
        return [f for f in self.files.values() if f.language == language]
    
    def get_files_with_security_issues(self) -> list[DetailedFileSummary]:
        """Get all files with security flags."""
        return [f for f in self.files.values() if f.security_flags]
    
    def get_files_with_compliance_issues(self) -> list[DetailedFileSummary]:
        """Get all files with compliance flags."""
        return [f for f in self.files.values() if f.compliance_flags]
    
    def search_by_class(self, class_name: str) -> list[DetailedFileSummary]:
        """Find files containing a specific class."""
        results = []
        for f in self.files.values():
            for cls in f.classes:
                if cls.get("name", "").lower() == class_name.lower():
                    results.append(f)
                    break
        return results
    
    def search_by_function(self, func_name: str) -> list[DetailedFileSummary]:
        """Find files containing a specific function."""
        results = []
        for f in self.files.values():
            for func in f.functions:
                if func.get("name", "").lower() == func_name.lower():
                    results.append(f)
                    break
        return results
    
    # ==================== QUERY API ====================
    
    def query(self, q: str) -> dict[str, Any]:
        """
        Unified query API for searching project context.
        
        Query formats:
        - "file:auth.py" - Get specific file
        - "class:UserService" - Find files with class
        - "func:authenticate" - Find files with function
        - "lang:python" - Files by language
        - "sec:" - Files with security issues
        - "comp:" - Files with compliance issues
        - "pattern:api" - Files matching pattern
        
        Returns:
            dict with "results" list and "count"
        """
        q = q.strip()
        results: list[dict[str, Any]] = []
        
        if q.startswith("file:"):
            name = q[5:].strip()
            for path, f in self.files.items():
                if name.lower() in path.lower():
                    results.append({"path": path, "summary": f.to_compact_dict()})
        
        elif q.startswith("class:"):
            class_name = q[6:].strip()
            for f in self.search_by_class(class_name):
                results.append({"path": f.relative_path, "summary": f.to_compact_dict()})
        
        elif q.startswith("func:"):
            func_name = q[5:].strip()
            for f in self.search_by_function(func_name):
                results.append({"path": f.relative_path, "summary": f.to_compact_dict()})
        
        elif q.startswith("lang:"):
            lang = q[5:].strip()
            for f in self.get_files_by_language(lang):
                results.append({"path": f.relative_path, "summary": f.to_compact_dict()})
        
        elif q.startswith("sec:"):
            for f in self.get_files_with_security_issues():
                results.append({"path": f.relative_path, "flags": f.security_flags, "summary": f.to_compact_dict()})
        
        elif q.startswith("comp:"):
            for f in self.get_files_with_compliance_issues():
                results.append({"path": f.relative_path, "flags": f.compliance_flags, "summary": f.to_compact_dict()})
        
        elif q.startswith("pattern:"):
            pattern = q[8:].strip().lower()
            for path, f in self.files.items():
                if pattern in path.lower() or pattern in f.purpose.lower():
                    results.append({"path": path, "summary": f.to_compact_dict()})
        
        else:
            # Free text search across all fields
            q_lower = q.lower()
            for path, f in self.files.items():
                if (q_lower in path.lower() or 
                    q_lower in f.purpose.lower() or
                    any(q_lower in c.get("name", "").lower() for c in f.classes) or
                    any(q_lower in fn.get("name", "").lower() for fn in f.functions)):
                    results.append({"path": path, "summary": f.to_compact_dict()})
        
        return {"results": results[:50], "count": len(results)}  # Limit to 50
    
    def to_compact_json(self) -> str:
        """
        Generate a smaller JSON representation.
        
        Uses compact file summaries to reduce size by ~50%.
        """
        data = {
            "v": self.version,
            "type": self.project_type,
            "be": self.backend_framework,
            "fe": self.frontend_framework,
            "db": self.database,
            "files": {path: f.to_compact_dict() for path, f in self.files.items()},
            "updated": self.last_updated.isoformat(),
        }
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


@dataclass
class ImportantFact:
    """An important fact extracted from conversation."""
    type: str  # file_mention, error, decision, vulnerability, task, etc.
    content: str
    source_message_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "content": self.content,
            "source_message_id": self.source_message_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class CurrentTask:
    """Tracks the current task being worked on."""
    type: str  # security_review, code_generation, compliance_check, etc.
    description: str
    status: str = "in_progress"  # in_progress, completed, blocked
    started_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "metadata": self.metadata,
        }


class ContextAgent(AgentBase):
    """
    Agent that manages global session context.
    
    This agent is responsible for:
    1. Extracting important information from every message
    2. Maintaining a summary of the conversation
    3. Coordinating information between agents
    4. Managing memory and history intelligently
    
    It should be called for EVERY message (pre and post processing).
    
    Example:
        ```python
        context_agent = ContextAgent()
        
        # Pre-process every message
        await context_agent.process(user_message, context)
        
        # Process with target agent
        response = await target_agent.process(user_message, context)
        
        # Post-process response
        await context_agent.process(response, context)
        ```
    """
    
    # Patterns for extracting information without LLM
    FILE_PATTERN = re.compile(r'[\w/\\.-]+\.(py|ts|js|java|go|rs|yaml|yml|json|md|txt)', re.IGNORECASE)
    ERROR_PATTERN = re.compile(r'(error|exception|failed|failure|bug|issue|problem)', re.IGNORECASE)
    SECURITY_PATTERN = re.compile(r'(vulnerab|security|inject|xss|csrf|auth|password|secret|token)', re.IGNORECASE)
    COMPLIANCE_PATTERN = re.compile(r'(gdpr|hipaa|pci|compliance|privacy|regulation|policy)', re.IGNORECASE)
    TASK_PATTERNS = {
        "security_review": re.compile(r'(verifica|check|scan|audit|review).*(security|sicurezza|vulnerab)', re.IGNORECASE),
        "compliance_check": re.compile(r'(verifica|check|comply|compliance|gdpr|privacy)', re.IGNORECASE),
        "code_generation": re.compile(r'(genera|create|write|implement|add|build).*(code|function|class|method)', re.IGNORECASE),
        "code_review": re.compile(r'(review|analyz|check).*(code|implementation)', re.IGNORECASE),
        "bug_fix": re.compile(r'(fix|resolve|debug|repair).*(bug|error|issue)', re.IGNORECASE),
        # NEW: App creation patterns
        "app_creation": re.compile(r'(crea|create|build|genera).*(app|application|progetto|project)', re.IGNORECASE),
        "feature_addition": re.compile(r'(aggiungi|add|metti|put|insert).*(login|auth|notification|feature)', re.IGNORECASE),
    }
    
    # NEW: Stack detection patterns
    BACKEND_PATTERNS = {
        "fastapi": re.compile(r'(fastapi|FastAPI|from fastapi)', re.IGNORECASE),
        "django": re.compile(r'(django|Django|from django)', re.IGNORECASE),
        "flask": re.compile(r'(flask|Flask|from flask)', re.IGNORECASE),
        "express": re.compile(r'(express|Express|require.*express)', re.IGNORECASE),
    }
    
    FRONTEND_PATTERNS = {
        "react": re.compile(r'(react|React|from ["\']react["\']|import React)', re.IGNORECASE),
        "vue": re.compile(r'(vue|Vue|from ["\']vue["\']|\.vue)', re.IGNORECASE),
        "angular": re.compile(r'(angular|Angular|@angular)', re.IGNORECASE),
        "svelte": re.compile(r'(svelte|Svelte|\.svelte)', re.IGNORECASE),
    }
    
    DATABASE_PATTERNS = {
        "postgresql": re.compile(r'(postgres|postgresql|psycopg)', re.IGNORECASE),
        "mysql": re.compile(r'(mysql|MySQL|pymysql)', re.IGNORECASE),
        "mongodb": re.compile(r'(mongo|MongoDB|pymongo)', re.IGNORECASE),
        "sqlite": re.compile(r'(sqlite|SQLite)', re.IGNORECASE),
    }
    
    def __init__(
        self,
        config: Optional[ContextAgentConfig] = None,
        llm_provider: Optional[LLMProvider] = None,
        workspace_path: Optional[str] = None,
    ):
        super().__init__()
        self.config = config or ContextAgentConfig()
        self._llm = llm_provider
        self._workspace_path = workspace_path
        # NEW: Persistent project structure (memory)
        self._project_structure: Optional[ProjectStructure] = None
        
        # Auto-load persisted structure if workspace is provided
        if workspace_path and self.config.persist_memory:
            self._load_project_structure(workspace_path)
    
    # ==================== PERSISTENCE METHODS ====================
    
    def _get_persistence_path(self, workspace_path: str) -> Path:
        """Get the path to the persistence JSON file."""
        return Path(workspace_path) / ".omni" / "context" / "project-structure.json"
    
    def _load_project_structure(self, workspace_path: str) -> bool:
        """
        Load project structure from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        persistence_path = self._get_persistence_path(workspace_path)
        
        if not persistence_path.exists():
            logger.debug(f"[CONTEXT] No persisted structure at {persistence_path}")
            return False
        
        try:
            data = json.loads(persistence_path.read_text(encoding="utf-8"))
            self._project_structure = ProjectStructure.from_dict(data, workspace_path)
            self._project_structure._workspace_path = workspace_path
            
            file_count = len(self._project_structure.files)
            logger.info(f"[CONTEXT] Loaded project structure: {file_count} files from {persistence_path}")
            return True
            
        except json.JSONDecodeError as e:
            logger.warning(f"[CONTEXT] Invalid JSON in {persistence_path}: {e}")
            return False
        except Exception as e:
            logger.warning(f"[CONTEXT] Failed to load project structure: {e}")
            return False
    
    def _save_project_structure(self, workspace_path: Optional[str] = None) -> bool:
        """
        Save project structure to disk.
        
        Args:
            workspace_path: Override workspace path (uses stored path if not provided)
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not self._project_structure:
            logger.debug("[CONTEXT] No project structure to save")
            return False
        
        # Determine workspace path
        ws_path = workspace_path or self._workspace_path
        if not ws_path and self._project_structure._workspace_path:
            ws_path = self._project_structure._workspace_path
        
        if not ws_path:
            logger.warning("[CONTEXT] No workspace path for persistence")
            return False
        
        persistence_path = self._get_persistence_path(ws_path)
        
        try:
            # Ensure directory exists
            persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize and write
            data = self._project_structure.to_dict()
            persistence_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            
            file_count = len(self._project_structure.files)
            logger.info(f"[CONTEXT] Saved project structure: {file_count} files to {persistence_path}")
            return True
            
        except Exception as e:
            logger.error(f"[CONTEXT] Failed to save project structure: {e}")
            return False
    
    def set_workspace(self, workspace_path: str, auto_load: bool = True) -> None:
        """
        Set the workspace path and optionally load persisted structure.
        
        Args:
            workspace_path: Path to the workspace root
            auto_load: Whether to auto-load persisted structure
        """
        self._workspace_path = workspace_path
        
        if auto_load and self.config.persist_memory:
            self._load_project_structure(workspace_path)
    
    def reload_project_structure(self) -> bool:
        """Force reload project structure from disk."""
        if self._workspace_path:
            return self._load_project_structure(self._workspace_path)
        return False
    
    def save_project_structure(self) -> bool:
        """Explicitly save project structure to disk."""
        return self._save_project_structure()
    
    # ==================== END PERSISTENCE METHODS ====================
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="context_agent",
            name="Context Agent",
            description="Manages session context, memory, and inter-agent coordination",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="memory",
                    description="Extracts and stores important information",
                ),
                AgentCapability(
                    name="summarization",
                    description="Summarizes long conversations",
                ),
                AgentCapability(
                    name="coordination",
                    description="Coordinates information between agents",
                ),
                AgentCapability(
                    name="task_detection",
                    description="Detects current task from conversation",
                ),
            ],
            tags=["system", "context", "memory", "coordination"],
            dependencies=[],  # Context agent has no dependencies
            provides=["project_structure", "conversation_summary", "task_context"],
        )
    
    def set_llm(self, provider: LLMProvider) -> None:
        """Set LLM provider (optional)."""
        self._llm = provider
    
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """
        Process a message to update context.
        
        Should be called for every message in the conversation.
        Updates shared_state with extracted information.
        """
        if not self.config.enabled:
            return AgentMessage(
                content="Context agent disabled",
                type=MessageType.STATUS,
                sender=self.metadata.id,
            )
        
        self.status = AgentStatus.EXECUTING
        updates = []
        
        try:
            content = str(message.content)
            
            # 1. Extract important facts
            facts = await self._extract_facts(message)
            if facts:
                self._store_facts(context, facts)
                updates.append(f"facts:{len(facts)}")
            
            # 2. Detect current task
            task = await self._detect_task(message, context)
            if task:
                context.set_shared("current_task", task.to_dict())
                updates.append(f"task:{task.type}")
            
            # 3. Summarize if history is long
            history_len = len(context.message_history)
            if history_len > self.config.summarize_after:
                summary = await self._summarize_history(context)
                if summary:
                    context.set_shared("session_summary", summary)
                    updates.append("summary")
            
            # 4. Update agent findings if this is from an agent
            if message.sender not in ["user", "system", "context_agent"]:
                self._process_agent_response(message, context)
                updates.append(f"findings:{message.sender}")
            
            self.status = AgentStatus.IDLE
            
            return AgentMessage(
                content=f"Context updated: {', '.join(updates) if updates else 'no changes'}",
                type=MessageType.STATUS,
                sender=self.metadata.id,
                metadata={
                    "updates": updates,
                    "facts_count": len(context.get_shared("important_facts", [])),
                    "has_summary": context.get_shared("session_summary") is not None,
                    "current_task": context.get_shared("current_task"),
                },
            )
            
        except Exception as e:
            logger.error(f"Context agent error: {e}")
            self.status = AgentStatus.ERROR
            return AgentMessage(
                content=f"Context update failed: {str(e)}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
    
    async def _extract_facts(self, message: AgentMessage) -> list[ImportantFact]:
        """Extract important facts from a message."""
        facts = []
        content = str(message.content)
        
        # Extract file mentions
        files = self.FILE_PATTERN.findall(content)
        for file_ext in files:
            # Find full filename
            match = re.search(rf'[\w/\\.-]+\.{file_ext}', content, re.IGNORECASE)
            if match:
                facts.append(ImportantFact(
                    type="file_mention",
                    content=match.group(0),
                    source_message_id=message.id,
                    metadata={"extension": file_ext},
                ))
        
        # Extract error mentions
        if self.ERROR_PATTERN.search(content):
            # Get context around error mention
            match = self.ERROR_PATTERN.search(content)
            if match:
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 100)
                facts.append(ImportantFact(
                    type="error_mention",
                    content=content[start:end].strip(),
                    source_message_id=message.id,
                ))
        
        # Extract security concerns
        if self.SECURITY_PATTERN.search(content):
            match = self.SECURITY_PATTERN.search(content)
            if match:
                start = max(0, match.start() - 30)
                end = min(len(content), match.end() + 80)
                facts.append(ImportantFact(
                    type="security_concern",
                    content=content[start:end].strip(),
                    source_message_id=message.id,
                ))
        
        # Extract compliance mentions
        if self.COMPLIANCE_PATTERN.search(content):
            match = self.COMPLIANCE_PATTERN.search(content)
            if match:
                start = max(0, match.start() - 30)
                end = min(len(content), match.end() + 80)
                facts.append(ImportantFact(
                    type="compliance_mention",
                    content=content[start:end].strip(),
                    source_message_id=message.id,
                ))
        
        # Use LLM for more sophisticated extraction if enabled
        if self.config.use_llm_for_extraction and self._llm:
            llm_facts = await self._extract_facts_with_llm(message)
            facts.extend(llm_facts)
        
        return facts
    
    async def _extract_facts_with_llm(self, message: AgentMessage) -> list[ImportantFact]:
        """Use LLM to extract facts (optional, disabled by default)."""
        if not self._llm:
            return []
        
        try:
            prompt = f"""Extract important facts from this message. 
Return JSON array with objects having: type, content
Types: decision, requirement, constraint, preference

Message: {message.content}

Return only valid JSON array:"""
            
            response = await self._llm.complete(
                [LLMMessage(role=LLMRole.USER, content=prompt)],
                LLMConfig(model=self._llm.default_model, temperature=0),
            )
            
            import json
            data = json.loads(response.content)
            return [
                ImportantFact(
                    type=item.get("type", "unknown"),
                    content=item.get("content", ""),
                    source_message_id=message.id,
                )
                for item in data
                if isinstance(item, dict)
            ]
        except Exception as e:
            logger.debug(f"LLM fact extraction failed: {e}")
            return []
    
    def _store_facts(self, context: AgentContext, facts: list[ImportantFact]) -> None:
        """Store facts in shared state, maintaining max limit."""
        existing = context.get_shared("important_facts", [])
        
        # Convert existing dicts back to facts if needed
        if existing and isinstance(existing[0], dict):
            existing = [existing]  # Keep as dicts
        
        # Add new facts as dicts
        for fact in facts:
            existing.append(fact.to_dict())
        
        # Keep only recent facts
        if len(existing) > self.config.max_facts:
            existing = existing[-self.config.max_facts:]
        
        context.set_shared("important_facts", existing)
    
    async def _detect_task(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> Optional[CurrentTask]:
        """Detect the current task from message content."""
        content = str(message.content).lower()
        
        # Only detect tasks from user messages
        if message.sender != "user":
            return None
        
        # Pattern-based detection
        for task_type, pattern in self.TASK_PATTERNS.items():
            if pattern.search(content):
                return CurrentTask(
                    type=task_type,
                    description=content[:200],  # First 200 chars as description
                    metadata={"detected_by": "pattern"},
                )
        
        return None
    
    async def _summarize_history(self, context: AgentContext) -> Optional[str]:
        """Summarize conversation history."""
        history = context.message_history
        
        if not history:
            return None
        
        # Without LLM: Simple extraction of key points
        if not self.config.use_llm_for_summarization or not self._llm:
            # Extract last N messages as summary
            recent = history[-5:]
            summary_parts = []
            for msg in recent:
                content = str(msg.content)[:100]
                summary_parts.append(f"[{msg.sender}]: {content}...")
            return "\n".join(summary_parts)
        
        # With LLM: Intelligent summarization
        try:
            history_text = "\n".join([
                f"{msg.sender}: {str(msg.content)[:200]}"
                for msg in history[-20:]  # Last 20 messages
            ])
            
            prompt = f"""Summarize this conversation in 3-5 bullet points:

{history_text}

Summary:"""
            
            response = await self._llm.complete(
                [LLMMessage(role=LLMRole.USER, content=prompt)],
                LLMConfig(model=self._llm.default_model, temperature=0),
            )
            
            return response.content
        except Exception as e:
            logger.debug(f"LLM summarization failed: {e}")
            return None
    
    def _process_agent_response(self, message: AgentMessage, context: AgentContext) -> None:
        """Process response from another agent to extract findings."""
        findings = context.get_shared("agent_findings", {})
        
        agent_id = message.sender
        if agent_id not in findings:
            findings[agent_id] = []
        
        # Extract structured data from metadata if present
        if message.metadata:
            finding = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": message.type.value,
                "summary": str(message.content)[:200],
            }
            
            # Copy relevant metadata
            for key in ["findings", "count", "severity", "vulnerabilities", "violations"]:
                if key in message.metadata:
                    finding[key] = message.metadata[key]
            
            findings[agent_id].append(finding)
            context.set_shared("agent_findings", findings)
    
    # === Public API for other agents ===
    
    def register_finding(
        self,
        context: AgentContext,
        agent_id: str,
        finding: dict[str, Any],
    ) -> None:
        """
        Register a finding from another agent.
        
        Args:
            context: Current agent context
            agent_id: ID of the agent registering the finding
            finding: Finding data to register
        """
        findings = context.get_shared("agent_findings", {})
        
        if agent_id not in findings:
            findings[agent_id] = []
        
        finding["timestamp"] = datetime.utcnow().isoformat()
        findings[agent_id].append(finding)
        context.set_shared("agent_findings", findings)
    
    def get_findings_for_agent(
        self,
        context: AgentContext,
        agent_id: str,
    ) -> list[dict[str, Any]]:
        """Get all findings registered by a specific agent."""
        findings = context.get_shared("agent_findings", {})
        return findings.get(agent_id, [])
    
    def get_all_findings(self, context: AgentContext) -> dict[str, list[dict[str, Any]]]:
        """Get all findings from all agents."""
        return context.get_shared("agent_findings", {})
    
    def get_current_task(self, context: AgentContext) -> Optional[dict[str, Any]]:
        """Get the current task being worked on."""
        return context.get_shared("current_task")
    
    def get_session_summary(self, context: AgentContext) -> Optional[str]:
        """Get the session summary."""
        return context.get_shared("session_summary")
    
    def get_important_facts(self, context: AgentContext) -> list[dict[str, Any]]:
        """Get all important facts extracted from conversation."""
        return context.get_shared("important_facts", [])
    
    def get_context_snapshot(self, context: AgentContext) -> dict[str, Any]:
        """
        Get a complete snapshot of the current context.
        
        Useful for other agents to understand the current state.
        """
        snapshot = {
            "session_id": context.session_id,
            "workspace_path": context.workspace_path,
            "current_task": self.get_current_task(context),
            "session_summary": self.get_session_summary(context),
            "important_facts": self.get_important_facts(context),
            "agent_findings": self.get_all_findings(context),
            "history_length": len(context.message_history),
        }
        
        # NEW: Include project structure summary (not raw code!)
        if self._project_structure:
            snapshot["project_structure"] = self._project_structure.to_dict()
            snapshot["project_summary"] = self._project_structure.get_summary_for_prompt()
        
        return snapshot
    
    # === NEW: Project Structure Management ===
    
    def get_project_structure(self) -> Optional[ProjectStructure]:
        """Get the persistent project structure."""
        return self._project_structure
    
    def get_project_summary_for_prompt(self) -> str:
        """
        Get a COMPACT summary suitable for LLM prompts.
        This is the key to saving tokens - we return ~200 chars instead of 50k of raw code.
        """
        if not self._project_structure:
            return "Project: Not analyzed yet"
        return self._project_structure.get_summary_for_prompt()
    
    def requires_backend_and_frontend(self) -> bool:
        """Check if changes typically need both backend and frontend."""
        if not self._project_structure:
            return False
        return self._project_structure.requires_both_tiers()
    
    def register_generated_file(
        self,
        file_path: str,
        content: str,
        file_type: str = "code",
        workspace_path: Optional[str] = None,
        auto_save: bool = True,
        modifier: str = "copilot",
    ) -> None:
        """
        Register a newly generated file with a DETAILED summary.
        Called by Coding Agent after generating code.
        
        Now uses DetailedFileSummary instead of short summaries.
        Includes VERSION TRACKING.
        
        Args:
            file_path: Absolute or relative path to the file
            content: Full file content
            file_type: Type hint (code, config, etc.)
            workspace_path: Workspace root for relative path calculation
            auto_save: Whether to auto-save to disk after registering
            modifier: Who is making this change (copilot, user, scan, etc.)
        """
        if not self._project_structure:
            self._project_structure = ProjectStructure()
        
        # Determine workspace path
        ws_path = workspace_path or self._workspace_path
        
        # Calculate relative path
        if ws_path and file_path.startswith(ws_path):
            relative_path = file_path[len(ws_path):].lstrip("/\\")
        else:
            relative_path = file_path
        
        # Generate DETAILED summary using FileAnalyzer
        try:
            from backend.integrations.file_analyzer import FileAnalyzer
            
            analyzer = FileAnalyzer(project_root=ws_path)
            analysis = analyzer.analyze_file(file_path, content)
            
            detailed_summary = DetailedFileSummary(
                file_path=file_path,
                relative_path=relative_path,
                language=analysis.language,
                lines_of_code=analysis.lines_of_code,
                classes=[
                    {
                        "name": cls.name,
                        "methods": cls.methods[:15],  # Limit to 15 methods
                        "docstring": cls.docstring[:200] if cls.docstring else "",
                        "base_classes": cls.base_classes,
                        "is_dataclass": cls.is_dataclass,
                        "is_abstract": cls.is_abstract,
                    }
                    for cls in analysis.classes
                ],
                functions=[
                    {
                        "name": func.name,
                        "params": func.params,
                        "returns": func.returns,
                        "docstring": func.docstring[:150] if func.docstring else "",
                        "is_async": func.is_async,
                        "is_private": func.is_private,
                    }
                    for func in analysis.functions
                ],
                imports={
                    "internal": analysis.internal_deps,
                    "external": list(set(analysis.external_deps)),
                },
                exports=analysis.exports,
                constants=analysis.constants[:20],  # Limit constants
                purpose=analysis.purpose,
                key_responsibilities=analysis.key_responsibilities,
                module_docstring=analysis.module_docstring[:300] if analysis.module_docstring else "",
                has_type_hints=analysis.has_type_hints,
                has_docstrings=analysis.has_docstrings,
                is_test_file=analysis.test_related,
                security_flags=analysis.security_flags,
                compliance_flags=analysis.compliance_flags,
                last_analyzed=datetime.utcnow(),
            )
            
        except Exception as e:
            logger.warning(f"Detailed analysis failed for {file_path}: {e}")
            # Fallback to minimal summary
            lines = content.split("\n")
            detailed_summary = DetailedFileSummary(
                file_path=file_path,
                relative_path=relative_path,
                language=self._guess_language(file_path),
                lines_of_code=len(lines),
                purpose=f"File with {len(lines)} lines",
                last_analyzed=datetime.utcnow(),
            )
        
        # Check if file already exists (update vs create)
        is_update = relative_path in self._project_structure.files
        
        # Store in unified files dict
        self._project_structure.files[relative_path] = detailed_summary
        
        # Detect stack from content
        self._detect_backend_framework(content)
        self._detect_frontend_framework(content)
        self._detect_database(content)
        
        # Update project type
        self._update_project_type()
        
        # INCREMENT VERSION with change tracking
        change_desc = f"{'Updated' if is_update else 'Added'} {relative_path}"
        self._project_structure.increment_version(modifier, change_desc)
        
        # Auto-save if enabled
        if auto_save and self.config.persist_memory:
            self._save_project_structure()
        
        logger.info(f"[v{self._project_structure.version}] Registered file: {relative_path} by {modifier}")
    
    def _guess_language(self, file_path: str) -> str:
        """Guess language from file extension."""
        return ProjectStructure._guess_language(file_path)
    
    def register_completed_feature(
        self,
        feature_name: str,
        files_modified: list[str],
        description: str = "",
    ) -> None:
        """
        Register a completed feature.
        This helps track what the app can do.
        """
        if not self._project_structure:
            self._project_structure = ProjectStructure()
        
        self._project_structure.completed_features.append({
            "name": feature_name,
            "files": files_modified,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        logger.info(f"Registered feature: {feature_name}")
    
    def _generate_file_summary(self, file_path: str, content: str) -> str:
        """
        Generate a COMPACT summary of a file.
        This is critical - we store ~200 chars instead of potentially 50k.
        """
        lines = content.split("\n")
        
        # Extract key info based on file type
        if file_path.endswith(".py"):
            return self._summarize_python_file(lines)
        elif file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            return self._summarize_js_file(lines)
        elif file_path.endswith((".yaml", ".yml")):
            return f"Config file ({len(lines)} lines)"
        elif file_path.endswith(".json"):
            return f"JSON file ({len(lines)} lines)"
        else:
            return f"File ({len(lines)} lines)"
    
    def generate_detailed_file_summary(
        self,
        file_path: str,
        content: str,
        workspace_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate a DETAILED summary suitable for senior developers.
        
        This provides comprehensive information about:
        - All classes with methods and docstrings
        - All functions with parameters and return types
        - All imports (internal vs external)
        - File purpose and responsibilities
        - Security/Compliance flags
        
        Returns:
            Dictionary with detailed file information
        """
        try:
            from backend.integrations.file_analyzer import FileAnalyzer
            
            analyzer = FileAnalyzer(project_root=workspace_path)
            analysis = analyzer.analyze_file(file_path, content)
            
            return {
                "file_path": analysis.file_path,
                "relative_path": analysis.relative_path,
                "language": analysis.language,
                "lines_of_code": analysis.lines_of_code,
                "purpose": analysis.purpose,
                "key_responsibilities": analysis.key_responsibilities,
                "classes": [
                    {
                        "name": cls.name,
                        "docstring": cls.docstring[:200] if cls.docstring else "",
                        "methods": cls.methods[:10],  # Top 10 methods
                        "base_classes": cls.base_classes,
                        "is_dataclass": cls.is_dataclass,
                        "is_abstract": cls.is_abstract,
                    }
                    for cls in analysis.classes
                ],
                "functions": [
                    {
                        "name": func.name,
                        "params": func.params,
                        "returns": func.returns,
                        "docstring": func.docstring[:150] if func.docstring else "",
                        "is_async": func.is_async,
                        "is_private": func.is_private,
                    }
                    for func in analysis.functions
                ],
                "imports": {
                    "internal": analysis.internal_deps,
                    "external": list(set(analysis.external_deps)),
                },
                "exports": analysis.exports,
                "constants": analysis.constants,
                "module_docstring": analysis.module_docstring[:300] if analysis.module_docstring else "",
                "quality": {
                    "has_type_hints": analysis.has_type_hints,
                    "has_docstrings": analysis.has_docstrings,
                    "is_test_file": analysis.test_related,
                },
                "security_flags": analysis.security_flags,
                "compliance_flags": analysis.compliance_flags,
            }
        except Exception as e:
            logger.warning(f"Detailed analysis failed for {file_path}: {e}")
            # Fallback to simple summary
            return {
                "file_path": file_path,
                "summary": self._generate_file_summary(file_path, content),
                "error": str(e),
            }
    
    async def analyze_workspace_detailed(
        self,
        workspace_path: str,
        file_patterns: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Analyze an entire workspace and return detailed summaries.
        
        This is the main entry point for comprehensive project analysis.
        
        Args:
            workspace_path: Path to the workspace root
            file_patterns: Optional glob patterns to match files
            
        Returns:
            Complete workspace analysis with file summaries
        """
        import os
        from pathlib import Path
        
        logger.info(f"[CONTEXT] analyze_workspace_detailed called for: {workspace_path}")
        
        if file_patterns is None:
            file_patterns = [
                # Python
                "*.py",
                # JavaScript/TypeScript
                "*.ts", "*.tsx", "*.js", "*.jsx",
                # Mobile
                "*.dart", "*.kt", "*.kts", "*.swift",
                # JVM
                "*.java", "*.scala",
                # Other backend
                "*.go", "*.rs", "*.rb", "*.php", "*.cs",
                # Frontend frameworks
                "*.vue", "*.svelte",
                # Config/Data
                "*.yaml", "*.yml",
            ]
        
        workspace = Path(workspace_path)
        ignore_spec = load_gitignore(workspace)
        results = {
            "workspace_path": workspace_path,
            "files": [],
            "summary": {
                "total_files": 0,
                "total_lines": 0,
                "languages": {},
                "total_classes": 0,
                "total_functions": 0,
            },
            "security_issues": [],
            "compliance_issues": [],
        }
        
        # Collect all matching files
        all_files: set[Path] = set()
        for pattern in file_patterns:
            for candidate in workspace.rglob(pattern):
                if not candidate.is_file():
                    continue
                if should_ignore(candidate, workspace, ignore_spec):
                    logger.debug(f"[CONTEXT] Skipping ignored file: {candidate}")
                    continue
                all_files.add(candidate)
        
        logger.info(f"[CONTEXT] Found {len(all_files)} matching files in workspace")
        
        # Analyze each file
        for file_path in all_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                logger.debug(f"[CONTEXT] Analyzing: {file_path.name} ({len(content)} chars)")
                analysis = self.generate_detailed_file_summary(
                    str(file_path),
                    content,
                    workspace_path
                )
                
                results["files"].append(analysis)
                
                # Update summary stats
                results["summary"]["total_files"] += 1
                results["summary"]["total_lines"] += analysis.get("lines_of_code", 0)
                
                lang = analysis.get("language", "unknown")
                results["summary"]["languages"][lang] = (
                    results["summary"]["languages"].get(lang, 0) + 1
                )
                
                results["summary"]["total_classes"] += len(analysis.get("classes", []))
                results["summary"]["total_functions"] += len(analysis.get("functions", []))
                
                # Collect security/compliance issues
                if analysis.get("security_flags"):
                    results["security_issues"].append({
                        "file": analysis["relative_path"],
                        "flags": analysis["security_flags"],
                    })
                
                if analysis.get("compliance_flags"):
                    results["compliance_issues"].append({
                        "file": analysis["relative_path"],
                        "flags": analysis["compliance_flags"],
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")
                continue
        
        logger.info(f"[CONTEXT] Detailed analysis complete: {results['summary']['total_files']} files, "
                   f"{results['summary']['total_classes']} classes, {results['summary']['total_functions']} functions")
        
        return results
    
    def _summarize_python_file(self, lines: list[str]) -> str:
        """Summarize a Python file."""
        classes = []
        functions = []
        imports = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("class "):
                match = re.match(r"class\s+(\w+)", line)
                if match:
                    classes.append(match.group(1))
            elif line.startswith("def "):
                match = re.match(r"def\s+(\w+)", line)
                if match:
                    functions.append(match.group(1))
            elif line.startswith(("from ", "import ")):
                imports.append(line[:50])
        
        parts = []
        if classes:
            parts.append(f"Classes: {', '.join(classes[:5])}")
        if functions:
            parts.append(f"Functions: {', '.join(functions[:5])}")
        if len(imports) > 0:
            parts.append(f"Imports: {len(imports)}")
        
        return " | ".join(parts) if parts else f"Python ({len(lines)} lines)"
    
    def _summarize_js_file(self, lines: list[str]) -> str:
        """Summarize a JavaScript/TypeScript file."""
        components = []
        functions = []
        exports = []
        
        for line in lines:
            line = line.strip()
            if "function " in line or "const " in line and "=>" in line:
                match = re.search(r"(?:function|const)\s+(\w+)", line)
                if match:
                    functions.append(match.group(1))
            elif line.startswith("export "):
                exports.append(line[:30])
            elif "React" in line or "Component" in line:
                match = re.search(r"(?:function|const|class)\s+(\w+)", line)
                if match:
                    components.append(match.group(1))
        
        parts = []
        if components:
            parts.append(f"Components: {', '.join(components[:5])}")
        if functions:
            parts.append(f"Functions: {', '.join(functions[:5])}")
        if exports:
            parts.append(f"Exports: {len(exports)}")
        
        return " | ".join(parts) if parts else f"JS/TS ({len(lines)} lines)"
    
    def _is_backend_file(self, file_path: str) -> bool:
        """Check if file is backend (delegates to ProjectStructure)."""
        return ProjectStructure._is_backend_file(file_path)
    
    def _is_frontend_file(self, file_path: str) -> bool:
        """Check if file is frontend (delegates to ProjectStructure)."""
        return ProjectStructure._is_frontend_file(file_path)
    
    def _detect_backend_framework(self, content: str) -> None:
        """Detect backend framework from content."""
        if self._project_structure.backend_framework:
            return  # Already detected
        
        for framework, pattern in self.BACKEND_PATTERNS.items():
            if pattern.search(content):
                self._project_structure.backend_framework = framework
                logger.info(f"Detected backend framework: {framework}")
                return
    
    def _detect_frontend_framework(self, content: str) -> None:
        """Detect frontend framework from content."""
        if self._project_structure.frontend_framework:
            return  # Already detected
        
        for framework, pattern in self.FRONTEND_PATTERNS.items():
            if pattern.search(content):
                self._project_structure.frontend_framework = framework
                logger.info(f"Detected frontend framework: {framework}")
                return
    
    def _detect_database(self, content: str) -> None:
        """Detect database from content."""
        if self._project_structure.database:
            return  # Already detected
        
        for db, pattern in self.DATABASE_PATTERNS.items():
            if pattern.search(content):
                self._project_structure.database = db
                logger.info(f"Detected database: {db}")
                return
    
    def _update_project_type(self) -> None:
        """Update project type based on detected files."""
        ps = self._project_structure
        
        # Count backend vs frontend files using the unified files dict
        backend_count = sum(
            1 for f in ps.files.values() 
            if ProjectStructure._is_backend_file(f.relative_path)
        )
        frontend_count = sum(
            1 for f in ps.files.values() 
            if ProjectStructure._is_frontend_file(f.relative_path)
        )
        
        has_backend = backend_count > 0 or ps.backend_framework
        has_frontend = frontend_count > 0 or ps.frontend_framework
        
        if has_backend and has_frontend:
            ps.project_type = "fullstack"
        elif has_backend:
            ps.project_type = "backend"
        elif has_frontend:
            ps.project_type = "frontend"
        else:
            ps.project_type = "unknown"
    
    # === File operation restrictions ===
    
    async def write_file(self, *args, **kwargs) -> None:
        """Context Agent cannot write files."""
        raise PermissionError("Context Agent is read-only and cannot write files")
    
    async def modify_file(self, *args, **kwargs) -> None:
        """Context Agent cannot modify files."""
        raise PermissionError("Context Agent is read-only and cannot modify files")
    
    async def delete_file(self, *args, **kwargs) -> None:
        """Context Agent cannot delete files."""
        raise PermissionError("Context Agent is read-only and cannot delete files")

"""
Copilot Integration

Generates files that GitHub Copilot can read for context:
- .github/copilot-instructions.md - Instructions for Copilot
- .omni/context/project-overview.md - Project structure and summary
- .omni/context/file-summaries.md - Detailed file-by-file summaries
- .omni/insights/security.md - Security findings and recommendations
- .omni/insights/compliance.md - Compliance findings and recommendations

These files are auto-generated and updated when:
1. Workspace is opened
2. Files are modified
3. Security/Compliance scan completes
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class FileSummary:
    """Detailed summary of a single file for senior developers."""
    file_path: str
    relative_path: str
    language: str
    lines_of_code: int
    
    # Structure
    classes: list[dict] = field(default_factory=list)  # [{name, methods, docstring}]
    functions: list[dict] = field(default_factory=list)  # [{name, params, returns, docstring}]
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    constants: list[str] = field(default_factory=list)  # Constants and module-level variables
    
    # Purpose
    purpose: str = ""  # What does this file do
    key_responsibilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # Other files it depends on
    dependents: list[str] = field(default_factory=list)  # Files that depend on this
    
    # Quality
    has_tests: bool = False
    test_coverage: Optional[float] = None
    complexity_notes: list[str] = field(default_factory=list)
    
    # Security/Compliance
    security_notes: list[str] = field(default_factory=list)
    compliance_notes: list[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Generate markdown summary for this file."""
        lines = [f"### `{self.relative_path}`"]
        lines.append(f"**Language:** {self.language} | **Lines:** {self.lines_of_code}")
        
        if self.purpose:
            lines.append(f"\n**Purpose:** {self.purpose}")
        
        if self.key_responsibilities:
            lines.append("\n**Responsibilities:**")
            for resp in self.key_responsibilities:
                lines.append(f"- {resp}")
        
        if self.classes:
            lines.append("\n**Classes:**")
            for cls in self.classes:
                methods = ", ".join(cls.get("methods", [])[:5])
                if len(cls.get("methods", [])) > 5:
                    methods += f" (+{len(cls['methods']) - 5} more)"
                lines.append(f"- `{cls['name']}`: {cls.get('docstring', 'No description')[:100]}")
                if methods:
                    lines.append(f"  - Methods: {methods}")
        
        if self.functions:
            lines.append("\n**Functions:**")
            for func in self.functions[:10]:
                params = ", ".join(func.get("params", []))
                returns = func.get("returns", "")
                sig = f"`{func['name']}({params})`"
                if returns:
                    sig += f" → `{returns}`"
                lines.append(f"- {sig}")
                if func.get("docstring"):
                    lines.append(f"  - {func['docstring'][:80]}")
            if len(self.functions) > 10:
                lines.append(f"- ... and {len(self.functions) - 10} more functions")
        
        if self.imports:
            key_imports = [i for i in self.imports if not i.startswith("__")][:5]
            if key_imports:
                lines.append(f"\n**Key Imports:** {', '.join(key_imports)}")
        
        if self.dependencies:
            lines.append(f"\n**Depends on:** {', '.join(self.dependencies[:5])}")
        
        if self.security_notes:
            lines.append("\n**⚠️ Security Notes:**")
            for note in self.security_notes:
                lines.append(f"- {note}")
        
        if self.compliance_notes:
            lines.append("\n**📋 Compliance Notes:**")
            for note in self.compliance_notes:
                lines.append(f"- {note}")
        
        lines.append("")
        return "\n".join(lines)


@dataclass
class ProjectContext:
    """Complete project context for Copilot."""
    workspace_path: str
    project_name: str
    project_type: str  # fullstack, backend, frontend, library
    
    # Stack
    backend_framework: Optional[str] = None
    frontend_framework: Optional[str] = None
    database: Optional[str] = None
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    
    # Structure
    file_summaries: list[FileSummary] = field(default_factory=list)
    architecture_notes: list[str] = field(default_factory=list)
    
    # Patterns
    api_patterns: list[str] = field(default_factory=list)
    naming_conventions: dict[str, str] = field(default_factory=dict)
    
    # Security
    security_findings: list[dict] = field(default_factory=list)
    security_rules: list[str] = field(default_factory=list)
    
    # Compliance
    compliance_findings: list[dict] = field(default_factory=list)
    compliance_rules: list[str] = field(default_factory=list)
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.utcnow)
    files_analyzed: int = 0


class CopilotIntegration:
    """
    Generates and maintains files for Copilot integration.
    
    Creates a .omni/ folder structure:
    ```
    .omni/
    ├── context/
    │   ├── project-overview.md    # Project structure, stack, architecture
    │   └── file-summaries.md      # Detailed file-by-file summaries
    └── insights/
        ├── security.md            # Security findings and recommendations
        └── compliance.md          # Compliance findings and recommendations
    
    .github/
    └── copilot-instructions.md    # Instructions Copilot reads automatically
    ```
    
    Example:
        ```python
        context = ProjectContext(
            workspace_path="/path/to/project",
            project_name="MyProject",
            project_type="backend",
        )
        
        integration = CopilotIntegration(context)
        
        # Generate all files
        await integration.generate_all()
        
        # Update after file change
        await integration.update_file_summary(file_path, file_summary)
        
        # Update security insights
        await integration.update_security_insights(findings)
        ```
    """
    
    def __init__(self, context: ProjectContext):
        self.context = context
        self.workspace_path = Path(context.workspace_path)
        self.omni_dir = self.workspace_path / ".omni"
        self.context_dir = self.omni_dir / "context"
        self.insights_dir = self.omni_dir / "insights"
        self.github_dir = self.workspace_path / ".github"
        
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories."""
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self.insights_dir.mkdir(parents=True, exist_ok=True)
        self.github_dir.mkdir(parents=True, exist_ok=True)
    
    def _analyze_data_flow(self) -> list[str]:
        """
        Analyze data flow patterns from file summaries.
        Returns insights about how data moves through the application.
        """
        flow_notes = []
        
        if not self.context.file_summaries:
            return flow_notes
        
        # Categorize files by their role
        entry_points = []
        services = []
        repositories = []
        models = []
        views = []
        api_handlers = []
        
        for summary in self.context.file_summaries:
            path = summary.relative_path.lower()
            name = Path(path).stem.lower()
            
            # Detect entry points
            if name in ('main', 'index', 'app', 'application', '__main__'):
                entry_points.append(summary.relative_path)
            
            # Detect services
            if 'service' in path or 'usecase' in path:
                services.append(summary.relative_path)
            
            # Detect repositories/DAL
            if 'repository' in path or 'repo' in name or 'dal' in path:
                repositories.append(summary.relative_path)
            
            # Detect models
            if 'model' in path or 'entity' in path or 'schema' in path:
                models.append(summary.relative_path)
            
            # Detect views/screens
            if 'view' in path or 'screen' in path or 'page' in path or 'component' in path:
                views.append(summary.relative_path)
            
            # Detect API handlers
            if 'route' in path or 'controller' in path or 'handler' in path or 'api' in path:
                api_handlers.append(summary.relative_path)
        
        # Generate flow description
        if entry_points:
            flow_notes.append(f"**Entry Points:** {', '.join(entry_points[:3])}")
        
        if views and api_handlers:
            flow_notes.append("**Flow:** UI/Views → API Handlers → Services → Repositories → Database")
        elif views and services:
            flow_notes.append("**Flow:** UI/Views → Services → Data Layer")
        elif api_handlers and services:
            flow_notes.append("**Flow:** API Routes → Controllers → Services → Repositories")
        elif api_handlers:
            flow_notes.append("**Flow:** HTTP Requests → API Handlers → Business Logic")
        elif views:
            flow_notes.append("**Flow:** User Events → Views/Screens → State → UI Update")
        
        # Count layers
        layers = []
        if views:
            layers.append(f"UI Layer ({len(views)} files)")
        if api_handlers:
            layers.append(f"API Layer ({len(api_handlers)} files)")
        if services:
            layers.append(f"Service Layer ({len(services)} files)")
        if repositories:
            layers.append(f"Data Layer ({len(repositories)} files)")
        if models:
            layers.append(f"Models ({len(models)} files)")
        
        if layers:
            flow_notes.append(f"**Layers:** {' → '.join(layers)}")
        
        # Analyze dependencies from imports
        dependency_count = {}
        for summary in self.context.file_summaries:
            for dep in summary.dependencies:
                dependency_count[dep] = dependency_count.get(dep, 0) + 1
        
        if dependency_count:
            # Find most imported modules (hubs)
            sorted_deps = sorted(dependency_count.items(), key=lambda x: x[1], reverse=True)[:3]
            if sorted_deps and sorted_deps[0][1] > 1:
                hubs = [f"`{dep}` ({count} imports)" for dep, count in sorted_deps]
                flow_notes.append(f"**Key Modules:** {', '.join(hubs)}")
        
        return flow_notes
    
    async def generate_all(self) -> None:
        """Generate all Copilot integration files."""
        logger.info(f"[COPILOT] Starting generation for {self.workspace_path}")
        logger.info(f"[COPILOT] Insights dir: {self.insights_dir}")
        logger.info(f"[COPILOT] Context dir: {self.context_dir}")
        
        await self.generate_copilot_instructions()
        await self.generate_project_overview()
        await self.generate_file_summaries()
        await self.generate_component_map()
        await self.generate_interfaces_and_apis()
        await self.generate_data_model()
        await self.generate_domain_patterns()
        await self.generate_hotspots()
        await self.generate_security_insights()
        await self.generate_compliance_insights()
        await self.generate_quick_reference()
        
        logger.info(f"[COPILOT] Generated all Copilot integration files in {self.workspace_path}")
    
    async def generate_copilot_instructions(self) -> None:
        """
        Generate .github/copilot-instructions.md
        
        This file is automatically read by GitHub Copilot.
        """
        context = self.context
        lines = [
            "# Copilot Instructions for this Project",
            "",
            f"> Auto-generated by OMNI at {datetime.now().isoformat()}",
            "",
            "## 🧠 OMNI Context System",
            "",
            "**ALWAYS read these files BEFORE generating or modifying code:**",
            "",
            "1. **`.omni/context/project-structure.json`** - Current project state with versioning",
            "2. **`.omni/memory/short_term.json`** - Recent changes and active context",
            "3. **`.omni/context/*.md`** - Architecture and design decisions",
            "",
            "### Why Use OMNI Context?",
            "",
            "- **Token efficiency**: Reduces context size by ~83%",
            "- **Accurate information**: Always up-to-date project structure",
            "- **Avoid duplication**: Check existing classes/functions before creating new ones",
            "- **Maintain consistency**: Follow established patterns and naming conventions",
            "",
            "### Before Writing Code:",
            "",
            "1. Read `.omni/context/project-structure.json` to understand:",
            "   - Existing files and their purposes",
            "   - Class/function signatures",
            "   - Dependencies between modules",
            "   - Recent changes (check `change_history`)",
            "",
            "2. Check `.omni/memory/short_term.json` for:",
            "   - Active tasks",
            "   - Recent modifications",
            "   - Current focus areas",
            "",
            "3. Review relevant `.omni/context/*.md` files for domain understanding",
            "",
            "---",
            "",
            "## Project Overview",
            "",
            f"**Project Type:** {context.project_type}",
        ]
        
        if context.backend_framework:
            lines.append(f"**Backend:** {context.backend_framework}")
        if context.frontend_framework:
            lines.append(f"**Frontend:** {context.frontend_framework}")
        if context.database:
            lines.append(f"**Database:** {context.database}")
        
        # Add languages
        if context.languages:
            lines.append(f"**Languages:** {', '.join(context.languages)}")
        
        # Add frameworks
        if context.frameworks:
            lines.append(f"**Frameworks:** {', '.join(context.frameworks)}")
        
        lines.extend([
            "",
            "## Code Style & Conventions",
            "",
        ])
        
        if context.naming_conventions:
            for key, value in context.naming_conventions.items():
                lines.append(f"- **{key}:** {value}")
        else:
            lines.extend([
                "- Use descriptive variable names",
                "- Follow existing code patterns in the project",
                "- Add docstrings to functions and classes",
            ])
        
        if context.api_patterns:
            lines.extend([
                "",
                "## API Patterns",
                "",
            ])
            for pattern in context.api_patterns:
                lines.append(f"- {pattern}")
        
        # Security rules
        lines.extend([
            "",
            "## Security Requirements",
            "",
            "When generating code, ALWAYS:",
            "",
        ])
        
        if context.security_rules:
            for rule in context.security_rules:
                lines.append(f"- {rule}")
        else:
            lines.extend([
                "- Use parameterized queries (never string concatenation for SQL)",
                "- Validate and sanitize all user inputs",
                "- Never hardcode secrets, passwords, or API keys",
                "- Use secure authentication patterns",
                "- Apply proper authorization checks",
                "- Escape output to prevent XSS",
            ])
        
        # Compliance rules
        if context.compliance_rules:
            lines.extend([
                "",
                "## Compliance Requirements",
                "",
            ])
            for rule in context.compliance_rules:
                lines.append(f"- {rule}")
        
        # Recent findings
        if context.security_findings:
            lines.extend([
                "",
                "## ⚠️ Known Security Issues (Fix These!)",
                "",
            ])
            for finding in context.security_findings[:5]:
                if isinstance(finding, dict):
                    severity = finding.get("severity", "unknown").upper()
                    title = finding.get("title", finding.get("description", finding.get("type", "Issue")))
                    file_path = finding.get("file_path", "")
                else:
                    severity = "UNKNOWN"
                    title = str(finding)
                    file_path = ""
                lines.append(f"- **[{severity}]** {title}")
                if file_path:
                    lines.append(f"  - File: `{file_path}`")
        
        lines.extend([
            "",
            "## Additional Context",
            "",
            "For high-level overview, see `.omni/context/project-overview.md`",
            "For component map, see `.omni/context/component-map.md`",
            "For APIs and interfaces, see `.omni/context/interfaces-and-apis.md`",
            "For data model notes, see `.omni/context/data-model.md`",
            "For hotspots, see `.omni/context/hotspots.md`",
            "For detailed file summaries, see `.omni/context/file-summaries.md`",
            "For security insights, see `.omni/insights/security.md`",
            "For compliance insights, see `.omni/insights/compliance.md`",
        ])
        
        content = "\n".join(lines)
        await self._write_file(self.github_dir / "copilot-instructions.md", content)
    
    async def generate_project_overview(self) -> None:
        """Generate .omni/context/project-overview.md"""
        context = self.context
        lines = [
            f"# Project Overview: {context.project_name}",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
            "## Stack",
            "",
            f"- **Type:** {context.project_type}",
        ]
        
        if context.backend_framework:
            lines.append(f"- **Backend:** {context.backend_framework}")
        if context.frontend_framework:
            lines.append(f"- **Frontend:** {context.frontend_framework}")
        if context.database:
            lines.append(f"- **Database:** {context.database}")
        
        if context.languages:
            lines.append(f"- **Languages:** {', '.join(context.languages)}")
        
        if context.frameworks:
            lines.append(f"- **Frameworks:** {', '.join(context.frameworks)}")
        
        lines.extend([
            "",
            "## Architecture",
            "",
        ])
        
        if context.architecture_notes:
            for note in context.architecture_notes:
                lines.append(f"- {note}")
        else:
            lines.append("_Run a full workspace analysis to generate architecture notes._")
        
        # Add data flow section
        lines.extend([
            "",
            "## Data Flow",
            "",
        ])
        
        data_flow = self._analyze_data_flow()
        if data_flow:
            for flow_note in data_flow:
                lines.append(f"- {flow_note}")
        else:
            lines.append("_Data flow will be analyzed after file processing._")
        
        # File structure
        lines.extend([
            "",
            "## File Structure",
            "",
            f"**Total files analyzed:** {len(self.context.file_summaries)}",
            "",
        ])
        
        # Group files by directory
        dirs: dict[str, list[str]] = {}
        for summary in self.context.file_summaries:
            dir_name = str(Path(summary.relative_path).parent)
            if dir_name not in dirs:
                dirs[dir_name] = []
            dirs[dir_name].append(Path(summary.relative_path).name)
        
        for dir_name, files in sorted(dirs.items()):
            lines.append(f"### `{dir_name}/`")
            for file in sorted(files)[:10]:
                lines.append(f"- {file}")
            if len(files) > 10:
                lines.append(f"- ... and {len(files) - 10} more")
            lines.append("")
        
        content = "\n".join(lines)
        await self._write_file(self.context_dir / "project-overview.md", content)
    
    async def generate_file_summaries(self) -> None:
        """Generate .omni/context/file-summaries.md with detailed summaries."""
        lines = [
            "# File Summaries",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
            "Detailed summaries of each file for senior developers.",
            "",
            "---",
            "",
        ]
        
        # Group by category
        backend_files = []
        frontend_files = []
        other_files = []
        
        for summary in self.context.file_summaries:
            path = summary.relative_path
            if self._is_backend_file(path):
                backend_files.append(summary)
            elif self._is_frontend_file(path):
                frontend_files.append(summary)
            else:
                other_files.append(summary)
        
        if backend_files:
            lines.extend([
                "## Backend Files",
                "",
            ])
            for summary in backend_files:
                lines.append(summary.to_markdown())
        
        if frontend_files:
            lines.extend([
                "## Frontend Files",
                "",
            ])
            for summary in frontend_files:
                lines.append(summary.to_markdown())
        
        if other_files:
            lines.extend([
                "## Other Files",
                "",
            ])
            for summary in other_files:
                lines.append(summary.to_markdown())
        
        content = "\n".join(lines)
        await self._write_file(self.context_dir / "file-summaries.md", content)

    async def generate_component_map(self) -> None:
        """Generate .omni/context/component-map.md with a light module map."""
        lines = [
            "# Component Map",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
            "Breakdown by top-level folder with key responsibilities and dependencies.",
            "",
        ]
        buckets: dict[str, list[FileSummary]] = {}
        for summary in self.context.file_summaries:
            parts = Path(summary.relative_path).parts
            top = parts[0] if parts else "root"
            buckets.setdefault(top, []).append(summary)
        for bucket, summaries in sorted(buckets.items()):
            lines.append(f"## {bucket}")
            lines.append("")
            for summary in sorted(summaries, key=lambda s: s.relative_path)[:50]:
                desc = summary.purpose or ", ".join(summary.key_responsibilities) or "(purpose not inferred)"
                deps = ", ".join(summary.dependencies[:5]) if summary.dependencies else ""
                line = f"- `{summary.relative_path}` — {desc}"
                if deps:
                    line += f" (depends on: {deps})"
                lines.append(line)
            lines.append("")
        content = "\n".join(lines)
        await self._write_file(self.context_dir / "component-map.md", content)

    async def generate_interfaces_and_apis(self) -> None:
        """Generate .omni/context/interfaces-and-apis.md (public surface)."""
        lines = [
            "# Interfaces and APIs",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
            "Functions, classes, and modules that look like entrypoints or public surfaces.",
            "",
        ]
        for summary in self.context.file_summaries:
            if not summary.functions and not summary.classes:
                continue
            lines.append(f"## `{summary.relative_path}`")
            if summary.purpose:
                lines.append(f"{summary.purpose}")
            if summary.classes:
                lines.append("\n**Classes:**")
                for cls in summary.classes[:10]:
                    methods = cls.get("methods", [])
                    methods_txt = ", ".join(methods[:5])
                    if len(methods) > 5:
                        methods_txt += " ..."
                    lines.append(f"- `{cls.get('name')}` ({methods_txt})")
            if summary.functions:
                lines.append("\n**Functions:**")
                for func in summary.functions[:20]:
                    params = ", ".join(func.get("params", []))
                    ret = func.get("returns", "")
                    sig = f"`{func.get('name')}({params})`"
                    if ret:
                        sig += f" → {ret}"
                    lines.append(f"- {sig}")
            lines.append("")
        if len(lines) == 5:  # No content added
            lines.append("_No interfaces detected in current analysis._")
        content = "\n".join(lines)
        await self._write_file(self.context_dir / "interfaces-and-apis.md", content)

    async def generate_data_model(self) -> None:
        """Generate .omni/context/data-model.md from classes and constants."""
        lines = [
            "# Data Model",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
            "Classes and data-bearing modules inferred from the codebase.",
            "",
        ]
        for summary in self.context.file_summaries:
            if not summary.classes and not summary.constants:
                continue
            lines.append(f"## `{summary.relative_path}`")
            if summary.classes:
                lines.append("\n**Classes:**")
                for cls in summary.classes[:20]:
                    doc = cls.get("docstring", "") or ""
                    doc_short = (doc[:120] + "...") if len(doc) > 120 else doc
                    lines.append(f"- `{cls.get('name')}` — {doc_short}")
            if summary.constants:
                lines.append("\n**Constants / exports:**")
                for const in summary.constants[:10]:
                    lines.append(f"- `{const}`")
            lines.append("")
        if len(lines) == 5:
            lines.append("_No data model elements detected in current analysis._")
        content = "\n".join(lines)
        await self._write_file(self.context_dir / "data-model.md", content)
    
    async def generate_domain_patterns(self) -> None:
        """Generate .omni/context/domain-patterns.md with domain-specific logic."""
        lines = [
            "# Domain-Specific Patterns",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
            "Domain logic and specialized patterns detected in the codebase.",
            "",
        ]
        
        # Detect domain patterns from file paths and content
        patterns_found = []
        
        # Categorize files by domain
        chat_files = []
        emotion_files = []
        rag_files = []
        auth_files = []
        character_files = []
        voice_files = []
        knowledge_files = []
        agent_files = []
        
        for summary in self.context.file_summaries:
            path = summary.relative_path.lower()
            
            if 'chat' in path:
                chat_files.append(summary)
            if 'emotion' in path or 'soul' in path or 'mood' in path:
                emotion_files.append(summary)
            if 'rag' in path or 'knowledge' in path or 'vector' in path or 'embedding' in path:
                rag_files.append(summary)
            if 'auth' in path or 'login' in path or 'session' in path:
                auth_files.append(summary)
            if 'character' in path or 'persona' in path or 'npc' in path:
                character_files.append(summary)
            if 'voice' in path or 'speech' in path or 'tts' in path or 'stt' in path:
                voice_files.append(summary)
            if 'index' in path and ('knowledge' in path or 'script' in path):
                knowledge_files.append(summary)
            if 'agent' in path:
                agent_files.append(summary)
        
        # Generate sections for detected patterns
        if chat_files:
            lines.extend([
                "## 💬 Chat System",
                "",
                "Chat/conversation management components:",
                "",
            ])
            for f in chat_files[:10]:
                lines.append(f"- `{f.relative_path}` — {f.purpose}")
            if len(chat_files) > 10:
                lines.append(f"- ... and {len(chat_files) - 10} more chat files")
            lines.append("")
            patterns_found.append("chat")
        
        if emotion_files:
            lines.extend([
                "## 🎭 Emotion/Soul System",
                "",
                "Emotional state and personality management:",
                "",
            ])
            for f in emotion_files[:10]:
                lines.append(f"- `{f.relative_path}` — {f.purpose}")
            lines.extend([
                "",
                "**Typical Flow:**",
                "1. User input → Emotion detection",
                "2. Character state update",
                "3. Response generation with emotional context",
                "4. UI feedback (indicators, animations)",
                "",
            ])
            patterns_found.append("emotion")
        
        if rag_files or knowledge_files:
            lines.extend([
                "## 📚 RAG (Retrieval-Augmented Generation)",
                "",
                "Knowledge retrieval and context injection:",
                "",
            ])
            for f in (rag_files + knowledge_files)[:10]:
                lines.append(f"- `{f.relative_path}` — {f.purpose}")
            lines.extend([
                "",
                "**Typical Flow:**",
                "1. Query embedding generation",
                "2. Vector similarity search",
                "3. Context retrieval from knowledge base",
                "4. Prompt augmentation with retrieved context",
                "5. LLM response generation",
                "",
            ])
            patterns_found.append("rag")
        
        if character_files:
            lines.extend([
                "## 👤 Character/Persona System",
                "",
                "Character management and personality:",
                "",
            ])
            for f in character_files[:10]:
                lines.append(f"- `{f.relative_path}` — {f.purpose}")
            lines.append("")
            patterns_found.append("character")
        
        if voice_files:
            lines.extend([
                "## 🔊 Voice System",
                "",
                "Voice input/output and speech processing:",
                "",
            ])
            for f in voice_files[:10]:
                lines.append(f"- `{f.relative_path}` — {f.purpose}")
            lines.extend([
                "",
                "**Components:**",
                "- Voice Input (STT): Speech-to-text conversion",
                "- Voice Output (TTS): Text-to-speech synthesis",
                "- Voice Mode: Full voice interaction handling",
                "",
            ])
            patterns_found.append("voice")
        
        if auth_files:
            lines.extend([
                "## 🔐 Authentication",
                "",
                "User authentication and session management:",
                "",
            ])
            for f in auth_files[:10]:
                lines.append(f"- `{f.relative_path}` — {f.purpose}")
            lines.append("")
            patterns_found.append("auth")
        
        if agent_files:
            lines.extend([
                "## 🤖 AI Agents",
                "",
                "AI agent implementations:",
                "",
            ])
            for f in agent_files[:10]:
                lines.append(f"- `{f.relative_path}` — {f.purpose}")
            lines.append("")
            patterns_found.append("agents")
        
        if not patterns_found:
            lines.append("_No specific domain patterns detected. This appears to be a general-purpose application._")
        else:
            lines.extend([
                "---",
                "",
                f"**Detected Domains:** {', '.join(patterns_found)}",
            ])
        
        content = "\n".join(lines)
        await self._write_file(self.context_dir / "domain-patterns.md", content)

    async def generate_hotspots(self) -> None:
        """Generate .omni/context/hotspots.md highlighting key files."""
        lines = [
            "# Hotspots",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
            "Files prioritized by size (LOC) as a first proxy for complexity.",
            "",
        ]
        top = sorted(self.context.file_summaries, key=lambda s: s.lines_of_code, reverse=True)[:20]
        if not top:
            lines.append("_No files analyzed yet._")
        for summary in top:
            desc = summary.purpose or ", ".join(summary.key_responsibilities) or "(purpose not inferred)"
            lines.append(f"- `{summary.relative_path}` — {summary.lines_of_code} LOC — {desc}")
        content = "\n".join(lines)
        await self._write_file(self.context_dir / "hotspots.md", content)
    
    async def generate_security_insights(self) -> None:
        """Generate .omni/insights/security.md"""
        lines = [
            "# Security Insights",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
        ]
        
        findings = self.context.security_findings
        # Filter to dict findings only
        findings = [f for f in findings if isinstance(f, dict)]
        
        if not findings:
            lines.extend([
                "## ✅ No Security Issues Found",
                "",
                "The codebase has been scanned and no security issues were detected.",
            ])
        else:
            # Summary
            critical = sum(1 for f in findings if f.get("severity") == "critical")
            high = sum(1 for f in findings if f.get("severity") == "high")
            medium = sum(1 for f in findings if f.get("severity") == "medium")
            low = sum(1 for f in findings if f.get("severity") == "low")
            
            lines.extend([
                "## Summary",
                "",
                f"- 🔴 **Critical:** {critical}",
                f"- 🟠 **High:** {high}",
                f"- 🟡 **Medium:** {medium}",
                f"- 🟢 **Low:** {low}",
                "",
            ])
            
            # TOP 10 actionable table
            priority_findings = sorted(
                findings,
                key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.get("severity", "low"), 4)
            )[:10]
            
            lines.extend([
                "## 🎯 Top 10 Priority Fixes",
                "",
                "| # | Sev | Issue | File | Line | Fix |",
                "|---|-----|-------|------|------|-----|",
            ])
            
            for i, f in enumerate(priority_findings, 1):
                sev = f.get("severity", "?")[:3].upper()
                title = (f.get("title") or f.get("type") or "Issue")[:25]
                fp = f.get("file_path", "")
                file_short = fp.split("/")[-1].split("\\")[-1][:18] if fp else "-"
                line = f.get("line_start") or f.get("line") or "-"
                fix = (f.get("remediation") or f.get("recommendation") or "Review")[:35]
                lines.append(f"| {i} | {sev} | {title} | `{file_short}` | {line} | {fix} |")
            
            lines.extend([
                "",
                "---",
                "",
                "## Findings by File",
                "",
            ])
            
            # Group by file
            by_file: dict[str, list] = {}
            for finding in findings:
                fp = finding.get("file_path", "unknown")
                by_file.setdefault(fp, []).append(finding)
            
            for file_path, file_findings in sorted(by_file.items()):
                lines.append(f"### 📄 `{file_path}`")
                lines.append("")
                for finding in file_findings[:5]:  # Max 5 per file
                    severity = finding.get("severity", "?").upper()
                    emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")
                    title = finding.get("title") or finding.get("type") or "Issue"
                    line = finding.get("line_start") or finding.get("line")
                    desc = finding.get("description") or finding.get("message") or ""
                    fix = finding.get("remediation") or finding.get("recommendation") or ""
                    
                    lines.append(f"- {emoji} **{title}**" + (f" (L{line})" if line else ""))
                    if desc:
                        lines.append(f"  - {desc[:100]}")
                    if fix:
                        lines.append(f"  - ✅ Fix: {fix[:80]}")
                
                if len(file_findings) > 5:
                    lines.append(f"  - ... +{len(file_findings) - 5} more")
                lines.append("")
        
        content = "\n".join(lines)
        await self._write_file(self.insights_dir / "security.md", content)
    
    async def generate_compliance_insights(self) -> None:
        """Generate .omni/insights/compliance.md"""
        lines = [
            "# Compliance Insights",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
        ]
        
        findings = self.context.compliance_findings
        # Filter to dict findings only
        findings = [f for f in findings if isinstance(f, dict)]
        
        if not findings:
            lines.extend([
                "## ✅ No Compliance Issues Found",
                "",
                "The codebase complies with configured rules.",
            ])
        else:
            # Group by regulation
            by_regulation: dict[str, list] = {}
            for f in findings:
                reg = f.get("regulation", "General")
                by_regulation.setdefault(reg, []).append(f)
            
            lines.extend([
                f"## Summary: {len(findings)} Issues",
                "",
            ])
            for reg, items in sorted(by_regulation.items()):
                lines.append(f"- **{reg}:** {len(items)} issues")
            lines.append("")
            
            # Top 10 priority table
            priority_findings = findings[:10]
            lines.extend([
                "## 🎯 Top 10 Priority Fixes",
                "",
                "| # | Regulation | Rule | File | Fix |",
                "|---|------------|------|------|-----|",
            ])
            for i, f in enumerate(priority_findings, 1):
                reg = (f.get("regulation") or "General")[:12]
                rule = (f.get("rule_name") or f.get("rule_id") or "Rule")[:20]
                fp = f.get("file_path", "")
                file_short = fp.split("/")[-1].split("\\")[-1][:18] if fp else "-"
                fix = (f.get("remediation") or f.get("message") or "Review")[:30]
                lines.append(f"| {i} | {reg} | {rule} | `{file_short}` | {fix} |")
            
            lines.extend([
                "",
                "---",
                "",
                "## Findings by Regulation",
                "",
            ])
            
            for reg, reg_findings in sorted(by_regulation.items()):
                lines.append(f"### 📋 {reg}")
                lines.append("")
                for finding in reg_findings[:5]:  # Max 5 per regulation
                    rule = finding.get("rule_name") or finding.get("rule_id") or "Rule"
                    fp = finding.get("file_path")
                    msg = finding.get("message") or ""
                    fix = finding.get("remediation") or ""
                    
                    lines.append(f"- **{rule}**" + (f" @ `{fp}`" if fp else ""))
                    if msg:
                        lines.append(f"  - {msg[:80]}")
                    if fix:
                        lines.append(f"  - ✅ Fix: {fix[:80]}")
                
                if len(reg_findings) > 5:
                    lines.append(f"  - ... +{len(reg_findings) - 5} more")
                lines.append("")
        
        content = "\n".join(lines)
        await self._write_file(self.insights_dir / "compliance.md", content)
    
    async def generate_quick_reference(self) -> None:
        """
        Generate .omni/context/quick-reference.md
        
        A compact index for different roles (BE/FE/Sec/QA).
        """
        lines = [
            "# Quick Reference",
            "",
            f"> Last updated: {datetime.now().isoformat()}",
            "",
            "Compact view for different team roles.",
            "",
        ]
        
        # Categorize files
        backend_files = []
        frontend_files = []
        test_files = []
        config_files = []
        
        for s in self.context.file_summaries:
            path = s.relative_path.lower()
            if 'test' in path or 'spec' in path:
                test_files.append(s)
            elif any(x in path for x in ('frontend', 'ui', 'components', '.tsx', '.jsx', '.vue', 'src/app', 'src/pages')):
                frontend_files.append(s)
            elif any(x in path for x in ('config', 'settings', '.yaml', '.json', '.env', '.ini')):
                config_files.append(s)
            else:
                backend_files.append(s)
        
        # Security summary
        sec_findings = [f for f in self.context.security_findings if isinstance(f, dict)]
        sec_critical = sum(1 for f in sec_findings if f.get("severity") in ("critical", "high"))
        
        # Compliance summary
        comp_findings = [f for f in self.context.compliance_findings if isinstance(f, dict)]
        
        lines.extend([
            "## 🛡️ Security Overview (Sec Role)",
            "",
            f"- **Critical/High Issues:** {sec_critical}",
            f"- **Total Findings:** {len(sec_findings)}",
            "",
        ])
        if sec_findings:
            lines.append("**Top 5:**")
            for f in sec_findings[:5]:
                fp = f.get("file_path", "")
                file_short = fp.split("/")[-1].split("\\")[-1] if fp else "-"
                lines.append(f"- `{file_short}` — {f.get('title', f.get('type', 'Issue'))}")
            lines.append("")
            lines.append(f"See [security.md](../insights/security.md) for details.")
        lines.append("")
        
        lines.extend([
            "## 📋 Compliance Overview (Compliance Role)",
            "",
            f"- **Total Issues:** {len(comp_findings)}",
            "",
        ])
        if comp_findings:
            lines.append("**Top 5:**")
            for f in comp_findings[:5]:
                reg = f.get("regulation", "General")
                rule = f.get("rule_name", f.get("rule_id", "Rule"))
                lines.append(f"- **{reg}**: {rule}")
            lines.append("")
            lines.append(f"See [compliance.md](../insights/compliance.md) for details.")
        lines.append("")
        
        lines.extend([
            "## 🔧 Backend (BE Role)",
            "",
            f"**Files:** {len(backend_files)}",
            "",
        ])
        if backend_files:
            lines.append("**Key Files:**")
            # Sort by "importance" (longer files first)
            for s in sorted(backend_files, key=lambda x: x.line_count, reverse=True)[:8]:
                funcs = len(s.functions)
                classes = len(s.classes)
                lines.append(f"- `{s.relative_path}` ({classes}C, {funcs}F, {s.line_count}L)")
        lines.append("")
        
        lines.extend([
            "## 🎨 Frontend (FE Role)",
            "",
            f"**Files:** {len(frontend_files)}",
            "",
        ])
        if frontend_files:
            lines.append("**Key Files:**")
            for s in sorted(frontend_files, key=lambda x: x.line_count, reverse=True)[:8]:
                lines.append(f"- `{s.relative_path}` — {s.purpose[:50]}")
        lines.append("")
        
        lines.extend([
            "## 🧪 QA / Testing (QA Role)",
            "",
            f"**Test Files:** {len(test_files)}",
            "",
        ])
        if test_files:
            lines.append("**Test Coverage:**")
            for s in test_files[:8]:
                funcs = [f for f in s.functions if f.lower().startswith("test")]
                lines.append(f"- `{s.relative_path}` — {len(funcs)} tests")
        lines.append("")
        
        lines.extend([
            "## ⚙️ Configuration",
            "",
            f"**Config Files:** {len(config_files)}",
            "",
        ])
        if config_files:
            for s in config_files[:6]:
                lines.append(f"- `{s.relative_path}` — {s.purpose[:40]}")
        lines.append("")
        
        content = "\n".join(lines)
        await self._write_file(self.context_dir / "quick-reference.md", content)
    
    async def update_file_summary(
        self,
        file_path: str,
        summary: FileSummary,
    ) -> None:
        """Update a single file's summary and regenerate files."""
        # Find and update existing summary or add new one
        found = False
        for i, existing in enumerate(self.context.file_summaries):
            if existing.file_path == file_path:
                self.context.file_summaries[i] = summary
                found = True
                break
        
        if not found:
            self.context.file_summaries.append(summary)
        
        self.context.last_updated = datetime.utcnow()
        
        # Regenerate affected files
        await self.generate_file_summaries()
        await self.generate_component_map()
        await self.generate_interfaces_and_apis()
        await self.generate_data_model()
        await self.generate_hotspots()
        await self.generate_copilot_instructions()
    
    async def update_security_insights(
        self,
        findings: list[dict],
    ) -> None:
        """Update security insights."""
        self.context.security_findings = findings
        self.context.last_updated = datetime.utcnow()
        
        await self.generate_security_insights()
        await self.generate_copilot_instructions()
    
    async def update_compliance_insights(
        self,
        findings: list[dict],
    ) -> None:
        """Update compliance insights."""
        self.context.compliance_findings = findings
        self.context.last_updated = datetime.utcnow()
        
        await self.generate_compliance_insights()
        await self.generate_copilot_instructions()
    
    def _is_backend_file(self, path: str) -> bool:
        """Check if file is backend."""
        path_lower = path.lower()
        return any(p in path_lower for p in [
            "/backend/", "\\backend\\",
            "/api/", "\\api\\",
            "/server/", "\\server\\",
            "main.py", "app.py", "server.",
        ]) or path.endswith(".py")
    
    def _is_frontend_file(self, path: str) -> bool:
        """Check if file is frontend."""
        path_lower = path.lower()
        return any(p in path_lower for p in [
            "/frontend/", "\\frontend\\",
            "/src/", "\\src\\",
            "/components/", "\\components\\",
        ]) or path.endswith((".tsx", ".jsx", ".vue", ".svelte"))
    
    async def _write_file(self, path: Path, content: str) -> None:
        """Write content to file."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            logger.info(f"[COPILOT] Wrote file: {path}")
        except Exception as e:
            logger.error(f"[COPILOT] Failed to write {path}: {e}")

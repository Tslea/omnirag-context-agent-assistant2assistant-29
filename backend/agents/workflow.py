"""
Workflow Orchestrator

Coordinates the full agent pipeline:
1. Context Agent → Analyzes project structure
2. RAG Agent → Indexes files, creates knowledge base
3. Security Agent → Analyzes vulnerabilities using context
4. Compliance Agent → Checks compliance using context

This is the main entry point for automatic code analysis.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable

from backend.core.interfaces.agent import (
    AgentMessage,
    AgentContext,
    MessageType,
)
from backend.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Result from a complete workflow execution."""
    success: bool
    context_summary: str = ""
    rag_indexed_count: int = 0
    security_findings: list[dict] = field(default_factory=list)
    compliance_findings: list[dict] = field(default_factory=list)
    total_issues: int = 0
    execution_time_ms: int = 0
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "context_summary": self.context_summary,
            "rag_indexed_count": self.rag_indexed_count,
            "security_findings": self.security_findings,
            "compliance_findings": self.compliance_findings,
            "total_issues": self.total_issues,
            "execution_time_ms": self.execution_time_ms,
            "errors": self.errors,
        }
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        parts = []
        
        if self.context_summary:
            parts.append(f"📁 {self.context_summary}")
        
        if self.rag_indexed_count > 0:
            parts.append(f"📚 Indexed {self.rag_indexed_count} files")
        
        if self.security_findings:
            critical = sum(1 for f in self.security_findings if f.get("severity") == "critical")
            high = sum(1 for f in self.security_findings if f.get("severity") == "high")
            parts.append(f"🔒 Security: {len(self.security_findings)} issues ({critical} critical, {high} high)")
        else:
            parts.append("🔒 Security: No issues found")
        
        if self.compliance_findings:
            parts.append(f"📋 Compliance: {len(self.compliance_findings)} issues")
        else:
            parts.append("📋 Compliance: No issues found")
        
        if self.errors:
            parts.append(f"⚠️ Errors: {len(self.errors)}")
        
        parts.append(f"⏱️ {self.execution_time_ms}ms")
        
        return "\n".join(parts)


class WorkflowOrchestrator:
    """
    Orchestrates the full analysis workflow.
    
    Flow:
    1. CONTEXT AGENT: Analyze project structure, create summary
    2. RAG AGENT: Index files using context, create knowledge base
    3. SECURITY AGENT: Analyze code using context + RAG
    4. COMPLIANCE AGENT: Check compliance using context + RAG
    
    Example:
        ```python
        workflow = WorkflowOrchestrator(orchestrator)
        
        # Analyze entire workspace
        result = await workflow.analyze_workspace("/path/to/project")
        
        # Analyze single file (incremental)
        result = await workflow.analyze_file("/path/to/file.py", content)
        ```
    """
    
    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        on_progress: Optional[Callable[[str, str], None]] = None,
    ):
        self.orchestrator = orchestrator
        self.on_progress = on_progress or (lambda stage, msg: None)
        self._context_initialized = False
        self._rag_initialized = False
        # Cache per aggiornamenti incrementali del Context Pack
        self._workspace_path: Optional[str] = None
        self._file_summaries: list = []
        self._security_findings: list[dict] = []
        self._compliance_findings: list[dict] = []
    
    def _emit_progress(self, stage: str, message: str) -> None:
        """Emit progress update."""
        logger.info(f"[{stage}] {message}")
        self.on_progress(stage, message)
    
    async def analyze_workspace(
        self,
        workspace_path: str,
        files: Optional[list[dict]] = None,
    ) -> WorkflowResult:
        """
        Analyze an entire workspace.
        
        This is called when:
        - User opens a project folder
        - User requests a full scan
        
        Args:
            workspace_path: Path to workspace
            files: Optional list of file info dicts
            
        Returns:
            WorkflowResult with all findings
        """
        start_time = datetime.now()
        result = WorkflowResult(success=True)
        
        try:
            # ========== STEP 1: CONTEXT AGENT ==========
            self._emit_progress("context", "Analyzing project structure...")
            
            context_agent = self._get_agent("context_agent")
            if context_agent:
                # Analyze project structure
                await self._analyze_project_structure(
                    context_agent, workspace_path, files
                )
                
                # Get summary
                if hasattr(context_agent, "get_project_summary_for_prompt"):
                    result.context_summary = context_agent.get_project_summary_for_prompt()
                
                self._context_initialized = True
                self._emit_progress("context", f"Done: {result.context_summary}")
            else:
                result.errors.append("Context Agent not available")
            
            # ========== STEP 2: RAG AGENT ==========
            self._emit_progress("rag", "Indexing files for search...")
            
            rag_agent = self._get_agent("rag_agent")
            if rag_agent and hasattr(rag_agent, "index_workspace"):
                try:
                    counts = await rag_agent.index_workspace(workspace_path)
                    result.rag_indexed_count = sum(counts.values())
                    self._rag_initialized = True
                    self._emit_progress("rag", f"Indexed {result.rag_indexed_count} files")
                except Exception as e:
                    logger.warning(f"RAG indexing failed: {e}")
                    result.errors.append(f"RAG indexing: {str(e)}")
            
            # ========== STEP 3: SECURITY AGENT ==========
            self._emit_progress("security", "Analyzing security...")
            
            security_findings = await self._run_security_analysis(workspace_path, files)
            result.security_findings = security_findings
            self._emit_progress("security", f"Found {len(security_findings)} issues")
            
            # ========== STEP 4: COMPLIANCE AGENT ==========
            self._emit_progress("compliance", "Checking compliance...")
            
            compliance_findings = await self._run_compliance_check(workspace_path, files)
            result.compliance_findings = compliance_findings
            self._emit_progress("compliance", f"Found {len(compliance_findings)} issues")
            
            # Calculate totals
            result.total_issues = len(result.security_findings) + len(result.compliance_findings)
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            result.success = False
            result.errors.append(str(e))
        
        # Calculate execution time
        result.execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # ========== STEP 5: GENERATE COPILOT FILES ==========
        self._emit_progress("copilot", "Generating Copilot context files...")
        self._workspace_path = workspace_path
        
        try:
            await self._generate_copilot_files(workspace_path, result)
            self._emit_progress("copilot", "Copilot files generated")
        except Exception as e:
            logger.warning(f"Copilot file generation failed: {e}")
            result.errors.append(f"Copilot files: {str(e)}")
        
        return result
    
    async def analyze_file(
        self,
        file_path: str,
        content: str,
        language: str = "",
    ) -> WorkflowResult:
        """
        Analyze a single file (incremental update).
        
        This is called when:
        - User saves a file
        - Copilot modifies a file
        
        Uses existing context from workspace analysis.
        
        Args:
            file_path: Path to file
            content: File content
            language: Programming language
            
        Returns:
            WorkflowResult with findings for this file
        """
        start_time = datetime.now()
        result = WorkflowResult(success=True)
        
        try:
            # ========== STEP 1: UPDATE CONTEXT ==========
            context_agent = self._get_agent("context_agent")
            if context_agent and hasattr(context_agent, "register_generated_file"):
                context_agent.register_generated_file(file_path, content)
                result.context_summary = context_agent.get_project_summary_for_prompt()
            
            # ========== STEP 2: UPDATE RAG INDEX ==========
            rag_agent = self._get_agent("rag_agent")
            if rag_agent and hasattr(rag_agent, "index_file_with_summary"):
                rag_agent.index_file_with_summary(file_path, content)
                result.rag_indexed_count = 1
            # Aggiorna anche l'indice vettoriale RAG (se disponibile)
            if rag_agent and hasattr(rag_agent, "index_file"):
                try:
                    await rag_agent.index_file(file_path, domain="code")
                except Exception as e:
                    logger.debug(f"RAG index_file failed: {e}")
            
            # ========== STEP 3: SECURITY ANALYSIS ==========
            self._emit_progress("security", f"Analyzing {Path(file_path).name}...")
            
            security_agent = self._get_agent("security")
            if security_agent and hasattr(security_agent, "validate_code"):
                try:
                    security_result = await security_agent.validate_code(content, file_path)
                    if security_result.get("issues"):
                        result.security_findings = security_result["issues"]
                except Exception as e:
                    logger.warning(f"Security analysis failed: {e}")
            
            # ========== STEP 4: COMPLIANCE CHECK ==========
            self._emit_progress("compliance", f"Checking {Path(file_path).name}...")
            
            compliance_agent = self._get_agent("compliance")
            if compliance_agent and hasattr(compliance_agent, "validate_code"):
                try:
                    compliance_result = await compliance_agent.validate_code(content, file_path)
                    if compliance_result.get("issues"):
                        result.compliance_findings = compliance_result["issues"]
                except Exception as e:
                    logger.warning(f"Compliance check failed: {e}")
            
            result.total_issues = len(result.security_findings) + len(result.compliance_findings)
            
        except Exception as e:
            logger.error(f"File analysis failed: {e}")
            result.success = False
            result.errors.append(str(e))
        
        result.execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        # Aggiorna incrementale il Context Pack
        try:
            await self._update_context_pack_incremental(file_path, content, result)
        except Exception as e:
            logger.warning(f"Incremental Context Pack update failed: {e}")
        
        return result
    
    def _get_agent(self, agent_id: str):
        """Get agent from orchestrator."""
        # Try both ID formats
        agent = self.orchestrator._agents.get(agent_id)
        if not agent:
            agent = self.orchestrator._agents.get(f"{agent_id}_agent")
        if not agent:
            # Try without _agent suffix
            base_id = agent_id.replace("_agent", "")
            agent = self.orchestrator._agents.get(base_id)
        return agent
    
    async def _analyze_project_structure(
        self,
        context_agent,
        workspace_path: str,
        files: Optional[list[dict]],
    ) -> None:
        """Analyze project structure with Context Agent."""
        # Set workspace path first to enable persistence
        if hasattr(context_agent, "set_workspace"):
            context_agent.set_workspace(workspace_path)
        
        if not files:
            # Scan workspace directory
            files = self._scan_directory(workspace_path)
        
        logger.info(f"[WORKFLOW] Analyzing {len(files)} files from {workspace_path}")
        analyzed_count = 0
        
        for file_info in files[:50]:  # Limit to first 50 files
            file_path = file_info.get("path", "")
            if not file_path:
                continue
            
            try:
                # Read file content
                content = self._read_file_safe(file_path)
                if content:
                    logger.debug(f"[WORKFLOW] Registering file: {file_path} ({len(content)} bytes)")
                    context_agent.register_generated_file(file_path, content)
                    analyzed_count += 1
                else:
                    logger.warning(f"[WORKFLOW] Empty or unreadable: {file_path}")
            except Exception as e:
                logger.debug(f"Failed to analyze {file_path}: {e}")
        
        logger.info(f"[WORKFLOW] Context Agent received {analyzed_count} files")
    
    def _scan_directory(self, workspace_path: str) -> list[dict]:
        """Scan directory for code files."""
        files = []
        supported_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx",
            ".java", ".cs", ".go", ".rb", ".php",
            ".dart", ".kt", ".kts", ".swift",  # Mobile
            ".vue", ".svelte",  # Frontend frameworks
            ".scala", ".rs",  # Other languages
            ".yaml", ".yml", ".json",
            ".html", ".css", ".scss", ".sql",
        }
        
        path = Path(workspace_path)
        if not path.exists():
            return files
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix in supported_extensions:
                # Skip common ignored directories
                if any(p in str(file_path) for p in [
                    "node_modules", "__pycache__", ".git", "dist", "build", ".venv", "venv"
                ]):
                    continue
                
                files.append({
                    "path": str(file_path),
                    "relative_path": str(file_path.relative_to(path)),
                    "language": self._get_language(file_path.suffix),
                })
        
        return files  # No limit - analyze all files
    
    def _read_file_safe(self, file_path: str) -> Optional[str]:
        """Read file content safely."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return None
    
    def _get_language(self, extension: str) -> str:
        """Get language from extension."""
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescriptreact",
            ".jsx": "javascriptreact",
            ".java": "java",
            ".cs": "csharp",
            ".go": "go",
            ".rb": "ruby",
            ".php": "php",
            ".dart": "dart",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".swift": "swift",
            ".vue": "vue",
            ".svelte": "svelte",
            ".scala": "scala",
            ".rs": "rust",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sql": "sql",
        }
        return mapping.get(extension, "unknown")
    
    async def _run_security_analysis(
        self,
        workspace_path: str,
        files: Optional[list[dict]],
    ) -> list[dict]:
        """Run security analysis on workspace."""
        findings = []
        
        security_agent = self._get_agent("security")
        if not security_agent:
            logger.warning("[WORKFLOW] Security agent not found!")
            return findings
        
        logger.info(f"[WORKFLOW] Running security analysis...")
        
        # Use orchestrator's validate_code if available
        if hasattr(self.orchestrator, "validate_code"):
            # Analyze a sample of files
            sample_files = (files or self._scan_directory(workspace_path))[:10]
            logger.info(f"[WORKFLOW] Analyzing {len(sample_files)} files for security")
            
            for file_info in sample_files:
                file_path = file_info.get("path", "")
                content = self._read_file_safe(file_path)
                if content:
                    logger.debug(f"[WORKFLOW] Security scan: {file_path}")
                    try:
                        result = await self.orchestrator.validate_code(content, file_path)
                        security_data = result.get("security", {})
                        if security_data.get("issues"):
                            findings.extend(security_data["issues"])
                            logger.info(f"[WORKFLOW] Found {len(security_data['issues'])} security issues in {file_path}")
                    except Exception as e:
                        logger.debug(f"Security analysis failed for {file_path}: {e}")
        else:
            logger.warning("[WORKFLOW] Orchestrator has no validate_code method!")
        
        return findings
    
    async def _run_compliance_check(
        self,
        workspace_path: str,
        files: Optional[list[dict]],
    ) -> list[dict]:
        """Run compliance check on workspace."""
        findings = []
        
        compliance_agent = self._get_agent("compliance")
        if not compliance_agent:
            logger.warning("[WORKFLOW] Compliance agent not found!")
            return findings
        
        logger.info(f"[WORKFLOW] Running compliance check...")
        
        # Similar to security analysis
        if hasattr(self.orchestrator, "validate_code"):
            sample_files = (files or self._scan_directory(workspace_path))[:10]
            logger.info(f"[WORKFLOW] Checking {len(sample_files)} files for compliance")
            
            for file_info in sample_files:
                file_path = file_info.get("path", "")
                content = self._read_file_safe(file_path)
                if content:
                    logger.debug(f"[WORKFLOW] Compliance check: {file_path}")
                    try:
                        result = await self.orchestrator.validate_code(content, file_path)
                        compliance_data = result.get("compliance", {})
                        if compliance_data.get("issues"):
                            findings.extend(compliance_data["issues"])
                            logger.info(f"[WORKFLOW] Found {len(compliance_data['issues'])} compliance issues in {file_path}")
                    except Exception as e:
                        logger.debug(f"Compliance check failed for {file_path}: {e}")
        else:
            logger.warning("[WORKFLOW] Orchestrator has no validate_code method!")
        
        return findings
        
        return findings
    
    def get_status(self) -> dict[str, Any]:
        """Get current workflow status."""
        return {
            "context_initialized": self._context_initialized,
            "rag_initialized": self._rag_initialized,
            "agents": {
                "context": self._get_agent("context_agent") is not None,
                "rag": self._get_agent("rag_agent") is not None,
                "security": self._get_agent("security") is not None,
                "compliance": self._get_agent("compliance") is not None,
            },
        }
    
    async def _generate_copilot_files(
        self,
        workspace_path: str,
        result: WorkflowResult,
    ) -> None:
        """
        Generate Copilot context files based on analysis results.
        
        Creates:
        - .github/copilot-instructions.md (auto-read by Copilot)
        - .omni/context/project-overview.md
        - .omni/context/file-summaries.md
        - .omni/insights/security.md
        - .omni/insights/compliance.md
        """
        from backend.integrations.copilot_integration import (
            CopilotIntegration,
            FileSummary,
            ProjectContext,
        )
        
        # Get detailed file summaries from Context Agent
        context_agent = self._get_agent("context_agent")
        file_summaries = []
        
        if context_agent and hasattr(context_agent, "analyze_workspace_detailed"):
            detailed = await context_agent.analyze_workspace_detailed(workspace_path)
            
            for file_data in detailed.get("files", []):
                # Skip non-dict entries (error fallbacks)
                if not isinstance(file_data, dict):
                    logger.warning(f"[WORKFLOW] Skipping non-dict file_data: {type(file_data)}")
                    continue
                
                # Skip error entries
                if "error" in file_data and "summary" in file_data:
                    logger.debug(f"[WORKFLOW] Skipping error file: {file_data.get('file_path', 'unknown')}")
                    continue
                
                imports_data = file_data.get("imports", {})
                if not isinstance(imports_data, dict):
                    imports_data = {"internal": [], "external": []}
                
                quality_data = file_data.get("quality", {})
                if not isinstance(quality_data, dict):
                    quality_data = {"is_test_file": False}
                
                file_summaries.append(FileSummary(
                    file_path=file_data.get("file_path", ""),
                    relative_path=file_data.get("relative_path", ""),
                    language=file_data.get("language", "unknown"),
                    lines_of_code=file_data.get("lines_of_code", 0),
                    classes=file_data.get("classes", []),
                    functions=file_data.get("functions", []),
                    imports=imports_data.get("external", []),
                    exports=file_data.get("exports", []),
                    constants=file_data.get("constants", []),
                    purpose=file_data.get("purpose", ""),
                    key_responsibilities=file_data.get("key_responsibilities", []),
                    dependencies=imports_data.get("internal", []),
                    has_tests=quality_data.get("is_test_file", False),
                    security_notes=file_data.get("security_flags", []),
                    compliance_notes=file_data.get("compliance_flags", []),
                ))
                
                # Convert file-level security flags to findings
                for flag in file_data.get("security_flags", []):
                    result.security_findings.append({
                        "severity": "medium",
                        "type": flag,
                        "title": self._security_flag_to_title(flag),
                        "description": self._security_flag_to_description(flag),
                        "file_path": file_data.get("relative_path", ""),
                        "recommendation": self._security_flag_to_recommendation(flag),
                    })
                
                # Convert file-level compliance flags to findings
                for flag in file_data.get("compliance_flags", []):
                    result.compliance_findings.append({
                        "severity": "medium",
                        "type": flag,
                        "rule_id": flag,
                        "title": self._compliance_flag_to_title(flag),
                        "description": self._compliance_flag_to_description(flag),
                        "file_path": file_data.get("relative_path", ""),
                        "recommendation": self._compliance_flag_to_recommendation(flag),
                    })
        
        # Analyze architecture
        architecture_notes = self._analyze_architecture(workspace_path, file_summaries)
        
        # Build project context
        project_context = ProjectContext(
            workspace_path=workspace_path,
            project_name=Path(workspace_path).name,
            project_type=self._detect_project_type(workspace_path),
            languages=self._detect_languages(workspace_path),
            frameworks=self._detect_frameworks(workspace_path),
            file_summaries=file_summaries,
            architecture_notes=architecture_notes,
            security_findings=[
                # Handle both dict and string issues
                (
                    {
                        "severity": f.get("severity", "medium") if isinstance(f, dict) else "medium",
                        "type": f.get("type", "unknown") if isinstance(f, dict) else "unknown",
                        "description": f.get("description", f.get("message", "")) if isinstance(f, dict) else str(f),
                        "file_path": f.get("file_path", f.get("file", "")) if isinstance(f, dict) else "",
                        "line": f.get("line") if isinstance(f, dict) else None,
                        "recommendation": f.get("recommendation", "") if isinstance(f, dict) else "",
                    }
                    if isinstance(f, dict) else
                    {
                        "severity": "medium",
                        "type": "unknown",
                        "description": str(f),
                        "file_path": "",
                        "line": None,
                        "recommendation": "",
                    }
                )
                for f in result.security_findings
            ],
            compliance_findings=[
                # Handle both dict and string issues
                (
                    {
                        "rule_id": f.get("rule_id", "") if isinstance(f, dict) else "",
                        "severity": f.get("severity", "medium") if isinstance(f, dict) else "medium",
                        "type": f.get("type", "unknown") if isinstance(f, dict) else "unknown",
                        "description": f.get("description", f.get("message", "")) if isinstance(f, dict) else str(f),
                        "file_path": f.get("file_path", f.get("file", "")) if isinstance(f, dict) else "",
                        "line": f.get("line") if isinstance(f, dict) else None,
                        "recommendation": f.get("recommendation", "") if isinstance(f, dict) else "",
                    }
                    if isinstance(f, dict) else
                    {
                        "rule_id": "",
                        "severity": "medium",
                        "type": "unknown",
                        "description": str(f),
                        "file_path": "",
                        "line": None,
                        "recommendation": "",
                    }
                )
                for f in result.compliance_findings
            ],
        )
        
        # Generate files
        integration = CopilotIntegration(project_context)
        await integration.generate_all()
        # Cache per incrementali
        self._file_summaries = file_summaries
        self._security_findings = result.security_findings
        self._compliance_findings = result.compliance_findings
        self._workspace_path = workspace_path
        
        logger.info(f"Generated Copilot files for {workspace_path}")
    
    def _detect_project_type(self, workspace_path: str) -> str:
        """Detect project type from workspace."""
        path = Path(workspace_path)
        
        # Check for common files
        if (path / "package.json").exists():
            pkg = self._read_file_safe(str(path / "package.json"))
            if pkg:
                if "react" in pkg.lower():
                    return "React Application"
                elif "vue" in pkg.lower():
                    return "Vue Application"
                elif "angular" in pkg.lower():
                    return "Angular Application"
                return "Node.js Application"
        
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            return "Python Application"
        
        if (path / "go.mod").exists():
            return "Go Application"
        
        if (path / "Cargo.toml").exists():
            return "Rust Application"
        
        # Flutter/Dart
        if (path / "pubspec.yaml").exists():
            return "Flutter Application"
        
        return "Software Project"
    
    def _detect_languages(self, workspace_path: str) -> list[str]:
        """Detect programming languages in workspace."""
        languages = set()
        path = Path(workspace_path)
        
        ext_to_lang = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".dart": "Dart",
            ".kt": "Kotlin",
            ".kts": "Kotlin",
            ".swift": "Swift",
            ".scala": "Scala",
            ".vue": "Vue",
            ".svelte": "Svelte",
        }
        
        for file_path in path.rglob("*"):
            if file_path.suffix in ext_to_lang:
                languages.add(ext_to_lang[file_path.suffix])
        
        return list(languages)
    
    def _detect_frameworks(self, workspace_path: str) -> list[str]:
        """Detect frameworks in workspace."""
        frameworks = []
        path = Path(workspace_path)
        
        # Check package.json
        pkg_path = path / "package.json"
        if pkg_path.exists():
            content = self._read_file_safe(str(pkg_path)) or ""
            if "react" in content.lower():
                frameworks.append("React")
            if "vue" in content.lower():
                frameworks.append("Vue")
            if "angular" in content.lower():
                frameworks.append("Angular")
            if "express" in content.lower():
                frameworks.append("Express")
            if "next" in content.lower():
                frameworks.append("Next.js")
        
        # Check Python
        req_path = path / "requirements.txt"
        if req_path.exists():
            content = self._read_file_safe(str(req_path)) or ""
            if "fastapi" in content.lower():
                frameworks.append("FastAPI")
            if "django" in content.lower():
                frameworks.append("Django")
            if "flask" in content.lower():
                frameworks.append("Flask")
        
        # Check Flutter/Dart
        pubspec_path = path / "pubspec.yaml"
        if pubspec_path.exists():
            content = self._read_file_safe(str(pubspec_path)) or ""
            frameworks.append("Flutter")
            if "bloc" in content.lower():
                frameworks.append("BLoC")
            if "provider" in content.lower():
                frameworks.append("Provider")
            if "riverpod" in content.lower():
                frameworks.append("Riverpod")
            if "get_it" in content.lower():
                frameworks.append("GetIt")
        
        return frameworks
    
    def _analyze_architecture(self, workspace_path: str, file_summaries: list) -> list[str]:
        """
        Analyze project architecture based on file structure and content.
        Returns a list of architecture insights.
        """
        notes = []
        path = Path(workspace_path)
        
        # Detect folder structure patterns
        folders = set()
        for item in path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                folders.add(item.name.lower())
        
        # Detect architecture patterns
        if 'lib' in folders and (path / 'pubspec.yaml').exists():
            notes.append("**Flutter/Dart** project with standard `lib/` structure")
            # Analyze Flutter structure
            lib_path = path / 'lib'
            if lib_path.exists():
                sub_folders = [f.name for f in lib_path.iterdir() if f.is_dir()]
                if sub_folders:
                    notes.append(f"Main code organized into: {', '.join(sub_folders)}")
                    
                # Common Flutter patterns
                if 'screens' in sub_folders or 'pages' in sub_folders:
                    notes.append("Uses **Screen/Page-based** navigation pattern")
                if 'widgets' in sub_folders:
                    notes.append("Has reusable **Widget** components")
                if 'models' in sub_folders:
                    notes.append("Data **Models** separated from UI")
                if 'services' in sub_folders or 'repositories' in sub_folders:
                    notes.append("Uses **Service/Repository** pattern for data access")
                if 'bloc' in sub_folders or 'blocs' in sub_folders:
                    notes.append("Uses **BLoC** (Business Logic Component) state management")
                if 'providers' in sub_folders:
                    notes.append("Uses **Provider** for state management")
                if 'controllers' in sub_folders:
                    notes.append("Uses **Controller** pattern (likely GetX or similar)")
        
        elif 'src' in folders:
            src_path = path / 'src'
            if src_path.exists():
                src_folders = [f.name for f in src_path.iterdir() if f.is_dir()]
                
                # Backend patterns
                if 'api' in src_folders or 'routes' in src_folders:
                    notes.append("Has **API/Routes** layer for HTTP endpoints")
                if 'services' in src_folders:
                    notes.append("Uses **Service layer** for business logic")
                if 'repositories' in src_folders or 'dal' in src_folders:
                    notes.append("Uses **Repository pattern** for data access")
                if 'models' in src_folders or 'entities' in src_folders:
                    notes.append("Has **Model/Entity** layer for data structures")
                if 'controllers' in src_folders:
                    notes.append("Uses **MVC** or **Controller-based** architecture")
                if 'middleware' in src_folders:
                    notes.append("Has custom **Middleware** for request processing")
                
                # Frontend patterns
                if 'components' in src_folders:
                    notes.append("Uses **Component-based** UI architecture")
                if 'views' in src_folders or 'pages' in src_folders:
                    notes.append("Has **View/Page** components for routing")
                if 'store' in src_folders or 'stores' in src_folders:
                    notes.append("Uses **Store** for state management (Redux/Vuex/Pinia)")
                if 'hooks' in src_folders:
                    notes.append("Uses custom **React Hooks** for logic reuse")
                if 'utils' in src_folders or 'helpers' in src_folders:
                    notes.append("Has **Utility** modules for shared functions")
        
        # Detect backend folder
        if 'backend' in folders:
            notes.append("**Backend** code is in dedicated `backend/` folder")
        if 'api' in folders:
            notes.append("**API** layer in root `api/` folder")
        
        # Detect frontend folder
        if 'frontend' in folders:
            notes.append("**Frontend** code is in dedicated `frontend/` folder")
        if 'client' in folders:
            notes.append("**Client** code separated in `client/` folder")
        
        # Detect monorepo patterns
        if 'packages' in folders or 'apps' in folders:
            notes.append("**Monorepo** structure with multiple packages/apps")
        
        # Detect config patterns
        if (path / 'docker-compose.yml').exists() or (path / 'docker-compose.yaml').exists():
            notes.append("Uses **Docker Compose** for containerized deployment")
        if (path / 'Dockerfile').exists():
            notes.append("Has **Dockerfile** for containerization")
        if (path / '.github/workflows').exists():
            notes.append("Has **GitHub Actions** CI/CD workflows")
        
        # Detect test structure
        if 'tests' in folders or 'test' in folders or '__tests__' in folders:
            notes.append("Has dedicated **test** folder for testing")
        
        # Analyze file-level patterns from summaries
        if file_summaries:
            entry_points = []
            for summary in file_summaries:
                rel_path = getattr(summary, 'relative_path', '')
                if 'main' in rel_path.lower() or 'index' in rel_path.lower() or 'app' in rel_path.lower():
                    entry_points.append(rel_path)
            
            if entry_points:
                notes.append(f"Entry points: {', '.join(entry_points[:3])}")
            
            # Count by type
            total_files = len(file_summaries)
            if total_files > 0:
                notes.append(f"**{total_files}** source files analyzed")
        
        if not notes:
            notes.append("Standard project structure")
        
        return notes
    
    def _security_flag_to_title(self, flag: str) -> str:
        """Convert security flag to human-readable title."""
        titles = {
            "hardcoded_secret": "Hardcoded Secret Detected",
            "sql_injection": "Potential SQL Injection",
            "shell_injection": "Potential Shell Injection",
            "eval_usage": "Unsafe eval() Usage",
            "pickle_usage": "Unsafe pickle.load Usage",
        }
        return titles.get(flag, flag.replace("_", " ").title())
    
    def _security_flag_to_description(self, flag: str) -> str:
        """Convert security flag to description."""
        descriptions = {
            "hardcoded_secret": "Found hardcoded credentials or API keys in source code",
            "sql_injection": "SQL query built with string concatenation/interpolation",
            "shell_injection": "Shell command execution with user-controllable input",
            "eval_usage": "Use of eval() can execute arbitrary code",
            "pickle_usage": "pickle.load can execute arbitrary code from untrusted data",
        }
        return descriptions.get(flag, f"Security issue: {flag}")
    
    def _security_flag_to_recommendation(self, flag: str) -> str:
        """Convert security flag to remediation recommendation."""
        recommendations = {
            "hardcoded_secret": "Move secrets to environment variables or a secrets manager",
            "sql_injection": "Use parameterized queries or ORM methods",
            "shell_injection": "Use subprocess with list arguments, avoid shell=True",
            "eval_usage": "Replace eval() with safer alternatives like ast.literal_eval()",
            "pickle_usage": "Use JSON or other safe serialization formats",
        }
        return recommendations.get(flag, "Review and fix this security issue")
    
    def _compliance_flag_to_title(self, flag: str) -> str:
        """Convert compliance flag to human-readable title."""
        titles = {
            "pii_handling": "PII Data Handling",
            "logging_sensitive": "Sensitive Data in Logs",
            "no_encryption": "Unencrypted Sensitive Data",
        }
        return titles.get(flag, flag.replace("_", " ").title())
    
    def _compliance_flag_to_description(self, flag: str) -> str:
        """Convert compliance flag to description."""
        descriptions = {
            "pii_handling": "Code handles personally identifiable information (PII)",
            "logging_sensitive": "Sensitive data may be written to logs",
            "no_encryption": "Passwords or sensitive data stored without encryption",
        }
        return descriptions.get(flag, f"Compliance issue: {flag}")
    
    def _compliance_flag_to_recommendation(self, flag: str) -> str:
        """Convert compliance flag to remediation recommendation."""
        recommendations = {
            "pii_handling": "Ensure GDPR/privacy compliance: encryption, consent, access controls",
            "logging_sensitive": "Mask or remove sensitive data before logging",
            "no_encryption": "Use proper password hashing (bcrypt, argon2) and encryption",
        }
        return recommendations.get(flag, "Review compliance requirements")

    async def _update_context_pack_incremental(
        self,
        file_path: str,
        content: str,
        result: WorkflowResult,
    ) -> None:
        """Aggiorna in modo incrementale il Context Pack per un singolo file."""
        from backend.integrations.file_analyzer import FileAnalyzer
        from backend.integrations.copilot_integration import (
            CopilotIntegration,
            ProjectContext,
        )

        workspace_path = self._workspace_path or str(Path(file_path).resolve().parent)
        self._workspace_path = workspace_path

        analyzer = FileAnalyzer(project_root=workspace_path)
        analysis = analyzer.analyze_file(file_path, content)
        summary = analyzer.to_file_summary(analysis)

        # Aggiorna cache dei file summary
        updated = False
        for idx, existing in enumerate(self._file_summaries):
            if getattr(existing, "file_path", "") == file_path:
                self._file_summaries[idx] = summary
                updated = True
                break
        if not updated:
            self._file_summaries.append(summary)

        # Aggiorna cache findings
        self._security_findings = result.security_findings
        self._compliance_findings = result.compliance_findings

        project_context = ProjectContext(
            workspace_path=workspace_path,
            project_name=Path(workspace_path).name,
            project_type=self._detect_project_type(workspace_path),
            languages=self._detect_languages(workspace_path),
            frameworks=self._detect_frameworks(workspace_path),
            file_summaries=self._file_summaries,
            security_findings=self._security_findings,
            compliance_findings=self._compliance_findings,
        )

        integration = CopilotIntegration(project_context)
        await integration.update_file_summary(file_path, summary)
        if self._security_findings:
            await integration.update_security_insights(self._security_findings)
        if self._compliance_findings:
            await integration.update_compliance_insights(self._compliance_findings)

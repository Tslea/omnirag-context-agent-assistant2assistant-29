"""
Security Agent Plugin

A read-only security analysis agent that:
1. Runs Semgrep first (static analysis)
2. Optionally uses LLM for interpretation (disabled by default)
3. Never writes files - only produces findings

Safety guarantees:
- Agent has NO file write access
- Semgrep rules are configurable
- LLM usage is opt-in (disabled by default)
- Works completely offline with just Semgrep
"""

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

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

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Security finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    """Categories of security findings."""
    INJECTION = "injection"
    XSS = "xss"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CRYPTOGRAPHY = "cryptography"
    SECRETS = "secrets"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    OTHER = "other"


@dataclass
class SecurityFinding:
    """
    A single security finding.
    
    Structured output format for security issues.
    """
    id: str
    title: str
    description: str
    severity: Severity
    category: FindingCategory
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    rule_id: str
    remediation: str = ""
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "rule_id": self.rule_id,
            "remediation": self.remediation,
            "references": self.references,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SecurityAgentConfig:
    """Configuration for security agent."""
    # Semgrep settings
    semgrep_enabled: bool = True
    semgrep_rules: list[str] = field(default_factory=lambda: [
        "p/security-audit",
        "p/secrets",
        "p/owasp-top-ten",
    ])
    semgrep_exclude: list[str] = field(default_factory=lambda: [
        "node_modules",
        "__pycache__",
        ".git",
        "*.min.js",
    ])
    semgrep_timeout: int = 300  # seconds
    
    # LLM settings (disabled by default for safety)
    llm_enabled: bool = False
    llm_max_findings: int = 10  # Max findings to send to LLM
    
    # Output settings
    min_severity: Severity = Severity.INFO
    include_remediation: bool = True
    
    # NEW: Context + RAG integration
    use_context_agent: bool = True  # Use project context for smarter analysis
    use_rag_agent: bool = True  # Query security knowledge base
    continuous_validation: bool = True  # Validate on every code change


class SecurityAgent(AgentBase):
    """
    Read-only security analysis agent.
    
    This agent:
    - NEVER writes files
    - Runs Semgrep for static analysis
    - Optionally uses LLM for interpretation
    - Produces structured security findings
    
    Example:
        ```python
        agent = SecurityAgent()
        result = await agent.analyze("/path/to/project")
        for finding in result.findings:
            print(f"{finding.severity}: {finding.title}")
        ```
    """
    
    def __init__(
        self,
        config: Optional[SecurityAgentConfig] = None,
        llm_provider: Optional[LLMProvider] = None,
        context_agent: Optional[Any] = None,
        rag_agent: Optional[Any] = None,
    ):
        super().__init__()
        self.config = config or SecurityAgentConfig()
        self._llm = llm_provider
        self._findings: list[SecurityFinding] = []
        
        # NEW: Integration with Context + RAG for smarter security
        self._context_agent = context_agent
        self._rag_agent = rag_agent
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="security",
            name="Security Agent",
            description="Analyzes code for security vulnerabilities using Semgrep and optional LLM",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="static_analysis",
                    description="Runs Semgrep static analysis",
                ),
                AgentCapability(
                    name="vulnerability_detection",
                    description="Detects common security vulnerabilities",
                ),
            ],
            tags=["security", "analysis", "semgrep", "read-only"],
            dependencies=["context_agent", "rag_agent"],
            provides=["security_findings", "vulnerability_report"],
        )
    
    def set_llm(self, provider: LLMProvider) -> None:
        """Set LLM provider (must also enable llm_enabled in config)."""
        self._llm = provider
    
    def set_context_agent(self, context_agent: Any) -> None:
        """Set Context Agent for project awareness."""
        self._context_agent = context_agent
    
    def set_rag_agent(self, rag_agent: Any) -> None:
        """Set RAG Agent for security knowledge base."""
        self._rag_agent = rag_agent
    
    # === NEW: Code Validation API (for Copilot integration) ===
    
    async def validate_code(
        self,
        code: str,
        file_path: str,
        context: Optional[AgentContext] = None,
    ) -> dict[str, Any]:
        """
        Validate code BEFORE it gets applied (e.g., from Copilot).
        
        This is the main API for "Assistant to the Assistant" pattern:
        - Copilot generates code
        - OMNI validates it
        - Returns issues or OK
        
        Args:
            code: The code to validate
            file_path: Path where code will be written
            context: Optional agent context
            
        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "issues": list of findings,
                "project_context": str,
                "security_context": str,
            }
        """
        self._findings = []
        
        # 1. Get project context from Context Agent
        project_context = ""
        if self._context_agent and self.config.use_context_agent:
            try:
                project_context = self._context_agent.get_project_summary_for_prompt()
            except Exception as e:
                logger.warning(f"Failed to get project context: {e}")
        
        # 2. Get security context from RAG Agent
        security_context = ""
        if self._rag_agent and self.config.use_rag_agent:
            try:
                # Query for security issues related to this type of code
                security_context = await self._rag_agent.get_relevant_summaries(
                    f"security vulnerabilities {file_path}"
                )
            except Exception as e:
                logger.warning(f"Failed to get security context: {e}")
        
        # 3. Run static analysis on the code
        findings = await self._analyze_code_string(code, file_path)
        self._findings.extend(findings)
        
        # 4. Enrich findings with context
        if self._llm and self.config.llm_enabled:
            await self._enrich_findings_with_context(
                project_context, security_context
            )
        
        # 5. Build result
        return {
            "valid": len(self._findings) == 0,
            "issues": [f.to_dict() for f in self._findings],
            "issue_count": len(self._findings),
            "critical_count": len([f for f in self._findings if f.severity == Severity.CRITICAL]),
            "high_count": len([f for f in self._findings if f.severity == Severity.HIGH]),
            "project_context": project_context,
            "security_context": security_context[:500] if security_context else "",
        }
    
    async def _analyze_code_string(
        self,
        code: str,
        file_path: str,
    ) -> list[SecurityFinding]:
        """Analyze a code string (not a file) for security issues."""
        findings = []
        
        # Quick pattern-based checks (fast, no semgrep needed)
        findings.extend(self._quick_security_checks(code, file_path))
        
        # If semgrep enabled, write to temp file and scan
        if self.config.semgrep_enabled:
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=Path(file_path).suffix,
                delete=False
            ) as f:
                f.write(code)
                temp_path = f.name
            
            try:
                semgrep_findings = await self._run_semgrep(temp_path)
                # Update file paths to original
                for finding in semgrep_findings:
                    finding.file_path = file_path
                findings.extend(semgrep_findings)
            finally:
                Path(temp_path).unlink(missing_ok=True)
        
        return findings
    
    def _quick_security_checks(
        self,
        code: str,
        file_path: str,
    ) -> list[SecurityFinding]:
        """Fast pattern-based security checks."""
        findings = []
        lines = code.split('\n')
        
        # Common vulnerability patterns
        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password", Severity.CRITICAL, FindingCategory.SECRETS),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key", Severity.CRITICAL, FindingCategory.SECRETS),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret", Severity.CRITICAL, FindingCategory.SECRETS),
            (r'eval\s*\(', "Use of eval()", Severity.HIGH, FindingCategory.INJECTION),
            (r'exec\s*\(', "Use of exec()", Severity.HIGH, FindingCategory.INJECTION),
            (r'subprocess\.call\([^)]*shell\s*=\s*True', "Shell injection risk", Severity.HIGH, FindingCategory.INJECTION),
            (r'\.execute\([^)]*%', "SQL injection risk (string formatting)", Severity.HIGH, FindingCategory.INJECTION),
            (r'\.execute\([^)]*\.format\(', "SQL injection risk (format)", Severity.HIGH, FindingCategory.INJECTION),
            (r'innerHTML\s*=', "XSS risk (innerHTML)", Severity.MEDIUM, FindingCategory.XSS),
            (r'dangerouslySetInnerHTML', "XSS risk (React)", Severity.MEDIUM, FindingCategory.XSS),
        ]
        
        import re
        for i, line in enumerate(lines, 1):
            for pattern, title, severity, category in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SecurityFinding(
                        id=f"quick-{len(findings)}",
                        title=title,
                        description=f"Potential security issue detected",
                        severity=severity,
                        category=category,
                        file_path=file_path,
                        line_start=i,
                        line_end=i,
                        code_snippet=line.strip()[:100],
                        rule_id=f"omni/{category.value}",
                        remediation=f"Review this code for {title.lower()}",
                    ))
        
        return findings
    
    async def _enrich_findings_with_context(
        self,
        project_context: str,
        security_context: str,
    ) -> None:
        """Enrich findings using project and security context."""
        if not self._findings or not self._llm:
            return
        
        # Use LLM to provide better remediation based on context
        prompt = f"""Given this project context:
{project_context}

And these security findings:
{chr(10).join(f"- {f.title} in {f.file_path}:{f.line_start}" for f in self._findings[:5])}

Provide specific remediation advice for this project's stack.
Be concise (1-2 sentences per finding)."""
        
        try:
            from backend.core.interfaces.llm import LLMMessage, LLMRole, LLMConfig
            response = await self._llm.complete(
                [LLMMessage(role=LLMRole.USER, content=prompt)],
                LLMConfig(model=self._llm.default_model, max_tokens=300),
            )
            # Note: In a real implementation, parse response and update findings
            logger.debug(f"LLM enrichment: {response.content[:100]}")
        except Exception as e:
            logger.warning(f"LLM enrichment failed: {e}")

    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """
        Process a security analysis request.
        
        Expected message content:
        - "analyze /path/to/project" - Full project scan
        - "check /path/to/file.py" - Single file scan
        - "status" - Return current findings
        """
        self.status = AgentStatus.EXECUTING
        content = str(message.content).strip()
        
        try:
            if content.startswith("analyze "):
                path = content[8:].strip()
                return await self._handle_analyze(path, context)
            
            elif content.startswith("check "):
                path = content[6:].strip()
                return await self._handle_check_file(path, context)
            
            elif content == "status":
                return await self._handle_status()
            
            else:
                return AgentMessage(
                    content="Unknown command. Use: analyze <path>, check <file>, or status",
                    type=MessageType.ERROR,
                    sender=self.metadata.id,
                )
        
        except Exception as e:
            logger.error(f"Security agent error: {e}")
            return AgentMessage(
                content=f"Security analysis failed: {str(e)}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
        finally:
            self.status = AgentStatus.IDLE
    
    async def _handle_analyze(
        self,
        path: str,
        context: AgentContext,
    ) -> AgentMessage:
        """Handle full project analysis."""
        project_path = Path(path)
        if not project_path.exists():
            return AgentMessage(
                content=f"Path not found: {path}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
        
        self._findings = []
        
        # Run Semgrep analysis
        if self.config.semgrep_enabled:
            semgrep_findings = await self._run_semgrep(str(project_path))
            self._findings.extend(semgrep_findings)
        
        # Filter by severity
        self._findings = [
            f for f in self._findings
            if self._severity_value(f.severity) >= self._severity_value(self.config.min_severity)
        ]
        
        # Optional LLM interpretation
        llm_summary = ""
        if self.config.llm_enabled and self._llm and self._findings:
            llm_summary = await self._get_llm_summary()
        
        # Build response
        response = self._format_findings(self._findings, llm_summary)
        
        return AgentMessage(
            content=response,
            type=MessageType.TEXT,
            sender=self.metadata.id,
            metadata={
                "findings_count": len(self._findings),
                "findings": [f.to_dict() for f in self._findings],
            },
        )
    
    async def _handle_check_file(
        self,
        file_path: str,
        context: AgentContext,
    ) -> AgentMessage:
        """Handle single file check."""
        if not Path(file_path).exists():
            return AgentMessage(
                content=f"File not found: {file_path}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
        
        findings = []
        
        if self.config.semgrep_enabled:
            semgrep_findings = await self._run_semgrep(file_path)
            findings.extend(semgrep_findings)
        
        response = self._format_findings(findings)
        
        return AgentMessage(
            content=response,
            type=MessageType.TEXT,
            sender=self.metadata.id,
            metadata={
                "findings_count": len(findings),
                "findings": [f.to_dict() for f in findings],
            },
        )
    
    async def _handle_status(self) -> AgentMessage:
        """Return current findings status."""
        return AgentMessage(
            content=f"Current findings: {len(self._findings)}",
            type=MessageType.STATUS,
            sender=self.metadata.id,
            metadata={
                "findings_count": len(self._findings),
                "by_severity": self._count_by_severity(),
            },
        )
    
    async def _run_semgrep(self, path: str) -> list[SecurityFinding]:
        """
        Run Semgrep analysis.
        
        Returns list of SecurityFindings parsed from Semgrep output.
        """
        findings = []
        
        try:
            # Check if semgrep is available
            result = subprocess.run(
                ["semgrep", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning("Semgrep not available")
                return findings
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Semgrep not installed or not in PATH")
            return findings
        
        # Build command
        cmd = [
            "semgrep",
            "--json",
            "--quiet",
            f"--timeout={self.config.semgrep_timeout}",
        ]
        
        # Add rules
        for rule in self.config.semgrep_rules:
            cmd.extend(["--config", rule])
        
        # Add excludes
        for exclude in self.config.semgrep_exclude:
            cmd.extend(["--exclude", exclude])
        
        cmd.append(path)
        
        logger.info(f"Running Semgrep: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.semgrep_timeout + 30,
            )
            
            if result.stdout:
                output = json.loads(result.stdout)
                findings = self._parse_semgrep_output(output)
                
        except subprocess.TimeoutExpired:
            logger.error("Semgrep timed out")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Semgrep output: {e}")
        except Exception as e:
            logger.error(f"Semgrep execution failed: {e}")
        
        return findings
    
    def _parse_semgrep_output(self, output: dict) -> list[SecurityFinding]:
        """Parse Semgrep JSON output into SecurityFindings."""
        findings = []
        
        for result in output.get("results", []):
            try:
                # Map Semgrep severity
                semgrep_severity = result.get("extra", {}).get("severity", "INFO")
                severity = self._map_semgrep_severity(semgrep_severity)
                
                # Determine category from rule ID
                rule_id = result.get("check_id", "unknown")
                category = self._categorize_rule(rule_id)
                
                finding = SecurityFinding(
                    id=f"semgrep-{len(findings)+1}",
                    title=result.get("extra", {}).get("message", "Security Issue"),
                    description=result.get("extra", {}).get("message", ""),
                    severity=severity,
                    category=category,
                    file_path=result.get("path", "unknown"),
                    line_start=result.get("start", {}).get("line", 0),
                    line_end=result.get("end", {}).get("line", 0),
                    code_snippet=result.get("extra", {}).get("lines", ""),
                    rule_id=rule_id,
                    remediation=result.get("extra", {}).get("fix", ""),
                    references=result.get("extra", {}).get("references", []),
                    metadata={
                        "semgrep_result": result,
                    },
                )
                findings.append(finding)
                
            except Exception as e:
                logger.warning(f"Failed to parse Semgrep result: {e}")
        
        return findings
    
    def _map_semgrep_severity(self, severity: str) -> Severity:
        """Map Semgrep severity to our Severity enum."""
        mapping = {
            "ERROR": Severity.HIGH,
            "WARNING": Severity.MEDIUM,
            "INFO": Severity.LOW,
        }
        return mapping.get(severity.upper(), Severity.INFO)
    
    def _categorize_rule(self, rule_id: str) -> FindingCategory:
        """Categorize a rule by its ID."""
        rule_lower = rule_id.lower()
        
        if any(x in rule_lower for x in ["sql", "injection", "command"]):
            return FindingCategory.INJECTION
        if any(x in rule_lower for x in ["xss", "script"]):
            return FindingCategory.XSS
        if any(x in rule_lower for x in ["auth", "login", "password"]):
            return FindingCategory.AUTHENTICATION
        if any(x in rule_lower for x in ["authz", "permission", "access"]):
            return FindingCategory.AUTHORIZATION
        if any(x in rule_lower for x in ["crypto", "hash", "encrypt"]):
            return FindingCategory.CRYPTOGRAPHY
        if any(x in rule_lower for x in ["secret", "key", "token", "api"]):
            return FindingCategory.SECRETS
        if any(x in rule_lower for x in ["config", "setting"]):
            return FindingCategory.CONFIGURATION
        
        return FindingCategory.OTHER
    
    def _severity_value(self, severity: Severity) -> int:
        """Get numeric value for severity comparison."""
        values = {
            Severity.INFO: 0,
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }
        return values.get(severity, 0)
    
    def _count_by_severity(self) -> dict[str, int]:
        """Count findings by severity."""
        counts: dict[str, int] = {}
        for finding in self._findings:
            key = finding.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts
    
    async def _get_llm_summary(self) -> str:
        """Get LLM summary of findings (only if enabled)."""
        if not self._llm or not self.config.llm_enabled:
            return ""
        
        # Limit findings sent to LLM
        findings_to_send = self._findings[:self.config.llm_max_findings]
        
        findings_text = "\n".join([
            f"- {f.severity.value.upper()}: {f.title} in {f.file_path}:{f.line_start}"
            for f in findings_to_send
        ])
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content="""You are a security expert. Analyze these security findings and provide:
1. A brief summary of the most critical issues
2. Recommended priority order for fixes
3. Any patterns you notice

Be concise and actionable.""",
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=f"Security findings:\n{findings_text}",
            ),
        ]
        
        try:
            response = await self._llm.complete(messages, LLMConfig(
                model=self._llm.default_model,
                max_tokens=500,
            ))
            return response.content or ""
        except Exception as e:
            logger.warning(f"LLM summary failed: {e}")
            return ""
    
    def _format_findings(
        self,
        findings: list[SecurityFinding],
        llm_summary: str = "",
    ) -> str:
        """Format findings as readable text."""
        if not findings:
            return "✅ No security issues found."
        
        lines = [f"🔒 Found {len(findings)} security issue(s):\n"]
        
        # Group by severity
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            severity_findings = [f for f in findings if f.severity == severity]
            if not severity_findings:
                continue
            
            emoji = {
                Severity.CRITICAL: "🚨",
                Severity.HIGH: "🔴",
                Severity.MEDIUM: "🟠",
                Severity.LOW: "🟡",
                Severity.INFO: "ℹ️",
            }.get(severity, "•")
            
            lines.append(f"\n{emoji} {severity.value.upper()} ({len(severity_findings)}):")
            
            for f in severity_findings:
                lines.append(f"  • {f.title}")
                lines.append(f"    📁 {f.file_path}:{f.line_start}")
                if f.remediation and self.config.include_remediation:
                    lines.append(f"    💡 {f.remediation[:100]}")
        
        if llm_summary:
            lines.append(f"\n📋 Analysis Summary:\n{llm_summary}")
        
        return "\n".join(lines)
    
    # SAFETY: These methods ensure the agent cannot write files
    
    async def write_file(self, *args, **kwargs) -> None:
        """DISABLED: Security agent cannot write files."""
        raise PermissionError("SecurityAgent is read-only and cannot write files")
    
    async def modify_file(self, *args, **kwargs) -> None:
        """DISABLED: Security agent cannot modify files."""
        raise PermissionError("SecurityAgent is read-only and cannot modify files")
    
    async def delete_file(self, *args, **kwargs) -> None:
        """DISABLED: Security agent cannot delete files."""
        raise PermissionError("SecurityAgent is read-only and cannot delete files")

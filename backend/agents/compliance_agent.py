"""
Compliance Agent Plugin

A compliance checking agent that:
1. Loads rules from external JSON/YAML files
2. Is jurisdiction-agnostic (no hardcoded regulations)
3. Optionally enriches with RAG context
4. Never crashes on missing rules (empty ruleset = no-op)

Safety guarantees:
- Rules are external, not hardcoded
- Empty ruleset produces no findings (not an error)
- Missing rule files log warnings but don't crash
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

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


class ComplianceSeverity(str, Enum):
    """Compliance finding severity."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    ADVISORY = "advisory"


class ComplianceStatus(str, Enum):
    """Compliance check status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"
    MANUAL_REVIEW = "manual_review"


@dataclass
class ComplianceRule:
    """
    A single compliance rule.
    
    Rules are loaded from external files and define what to check.
    """
    id: str
    name: str
    description: str
    category: str
    severity: ComplianceSeverity
    
    # What to check
    patterns: list[str] = field(default_factory=list)  # Regex patterns
    file_patterns: list[str] = field(default_factory=list)  # File globs
    keywords: list[str] = field(default_factory=list)  # Keywords to search
    
    # Compliance details
    regulation: str = ""  # e.g., "GDPR", "HIPAA", "SOC2"
    article: str = ""  # e.g., "Article 5", "Section 164.312"
    remediation: str = ""
    references: list[str] = field(default_factory=list)
    
    # Metadata
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceFinding:
    """
    A compliance finding from rule evaluation.
    """
    rule_id: str
    rule_name: str
    status: ComplianceStatus
    severity: ComplianceSeverity
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: str = ""
    remediation: str = ""
    regulation: str = ""
    article: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "status": self.status.value,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "regulation": self.regulation,
            "article": self.article,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ComplianceAgentConfig:
    """Configuration for compliance agent."""
    # Rule loading
    ruleset_paths: list[str] = field(default_factory=lambda: [
        "./rulesets",
        "~/.omni/rulesets",
    ])
    enabled_rulesets: list[str] = field(default_factory=list)  # Empty = all
    
    # RAG integration (optional)
    rag_enabled: bool = False
    rag_domains: list[str] = field(default_factory=lambda: ["compliance"])
    
    # LLM interpretation (optional)
    llm_enabled: bool = False
    
    # Output settings
    include_passed: bool = False  # Include passing checks in output
    min_severity: ComplianceSeverity = ComplianceSeverity.ADVISORY
    
    # NEW: Context + RAG Agent integration
    use_context_agent: bool = True  # Use project context for smarter checks
    use_rag_agent: bool = True  # Query compliance knowledge base
    continuous_validation: bool = True  # Validate on every code change


class ComplianceAgent(AgentBase):
    """
    Compliance checking agent using external rulesets.
    
    This agent:
    - Loads rules from JSON/YAML files (no hardcoded regulations)
    - Is jurisdiction-agnostic
    - Works with empty rulesets (no-op, not an error)
    - Optionally enriches checks with RAG context
    
    Example:
        ```python
        agent = ComplianceAgent()
        await agent.load_rules()  # Load from configured paths
        result = await agent.check("/path/to/project")
        ```
    """
    
    def __init__(
        self,
        config: Optional[ComplianceAgentConfig] = None,
        llm_provider: Optional[LLMProvider] = None,
        rag_service: Optional[Any] = None,
        context_agent: Optional[Any] = None,
        rag_agent: Optional[Any] = None,
    ):
        super().__init__()
        self.config = config or ComplianceAgentConfig()
        self._llm = llm_provider
        self._rag = rag_service
        
        # NEW: Integration with Context + RAG for smarter compliance
        self._context_agent = context_agent
        self._rag_agent = rag_agent
        
        self._rules: dict[str, ComplianceRule] = {}
        self._findings: list[ComplianceFinding] = []
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="compliance",
            name="Compliance Agent",
            description="Checks code against compliance rules from external rulesets",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="rule_based_checking",
                    description="Evaluates code against loaded compliance rules",
                ),
                AgentCapability(
                    name="multi_regulation",
                    description="Supports any regulation via external rulesets",
                ),
            ],
            tags=["compliance", "audit", "rules", "regulation"],
            dependencies=["context_agent", "rag_agent"],
            provides=["compliance_findings", "compliance_report"],
        )
    
    def set_llm(self, provider: LLMProvider) -> None:
        """Set LLM provider (must also enable llm_enabled in config)."""
        self._llm = provider
    
    def set_rag(self, rag_service: Any) -> None:
        """Set RAG service for context enrichment."""
        self._rag = rag_service
    
    def set_context_agent(self, context_agent: Any) -> None:
        """Set Context Agent for project awareness."""
        self._context_agent = context_agent
    
    def set_rag_agent(self, rag_agent: Any) -> None:
        """Set RAG Agent for compliance knowledge base."""
        self._rag_agent = rag_agent
    
    # === NEW: Code Validation API (for Copilot integration) ===
    
    async def validate_code(
        self,
        code: str,
        file_path: str,
        context: Optional[AgentContext] = None,
    ) -> dict[str, Any]:
        """
        Validate code for compliance BEFORE it gets applied.
        
        This is the main API for "Assistant to the Assistant" pattern:
        - Copilot generates code
        - OMNI validates for compliance
        - Returns issues or OK
        
        Args:
            code: The code to validate
            file_path: Path where code will be written
            context: Optional agent context
            
        Returns:
            Dict with validation results
        """
        self._findings = []
        
        # 1. Get project context from Context Agent
        project_context = ""
        data_types_handled = []
        if self._context_agent and self.config.use_context_agent:
            try:
                project_context = self._context_agent.get_project_summary_for_prompt()
                # Try to detect what kind of data this code handles
                data_types_handled = self._detect_data_types(code)
            except Exception as e:
                logger.warning(f"Failed to get project context: {e}")
        
        # 2. Get compliance context from RAG Agent
        compliance_context = ""
        if self._rag_agent and self.config.use_rag_agent:
            try:
                # Query for compliance rules related to detected data types
                query = f"compliance regulations {' '.join(data_types_handled)}"
                compliance_context = await self._rag_agent.get_relevant_summaries(query)
            except Exception as e:
                logger.warning(f"Failed to get compliance context: {e}")
        
        # 3. Run compliance checks
        findings = await self._check_code_compliance(code, file_path, data_types_handled)
        self._findings.extend(findings)
        
        # 4. Build result
        return {
            "valid": len(self._findings) == 0,
            "issues": [f.to_dict() for f in self._findings],
            "issue_count": len(self._findings),
            "critical_count": len([f for f in self._findings if f.severity == ComplianceSeverity.CRITICAL]),
            "data_types_detected": data_types_handled,
            "project_context": project_context,
            "compliance_context": compliance_context[:500] if compliance_context else "",
            "regulations_checked": list(set(f.regulation for f in self._findings if f.regulation)),
        }
    
    def _detect_data_types(self, code: str) -> list[str]:
        """Detect what types of sensitive data the code handles."""
        import re
        detected = []
        
        patterns = {
            "personal_data": [r'email', r'name', r'address', r'phone', r'birth'],
            "financial_data": [r'credit_card', r'payment', r'bank', r'account_number'],
            "health_data": [r'patient', r'medical', r'health', r'diagnosis', r'prescription'],
            "authentication": [r'password', r'token', r'auth', r'session', r'login'],
        }
        
        code_lower = code.lower()
        for data_type, keywords in patterns.items():
            if any(re.search(k, code_lower) for k in keywords):
                detected.append(data_type)
        
        return detected
    
    async def _check_code_compliance(
        self,
        code: str,
        file_path: str,
        data_types: list[str],
    ) -> list[ComplianceFinding]:
        """Check code for compliance issues."""
        findings = []
        lines = code.split('\n')
        
        # GDPR checks if handling personal data
        if "personal_data" in data_types:
            findings.extend(self._check_gdpr_compliance(code, file_path, lines))
        
        # HIPAA checks if handling health data
        if "health_data" in data_types:
            findings.extend(self._check_hipaa_compliance(code, file_path, lines))
        
        # PCI-DSS checks if handling financial data
        if "financial_data" in data_types:
            findings.extend(self._check_pci_compliance(code, file_path, lines))
        
        # Authentication best practices
        if "authentication" in data_types:
            findings.extend(self._check_auth_compliance(code, file_path, lines))
        
        # Also run loaded rules
        for rule in self._rules.values():
            if rule.enabled:
                rule_findings = self._evaluate_rule(rule, code, file_path, lines)
                findings.extend(rule_findings)
        
        return findings
    
    def _check_gdpr_compliance(
        self,
        code: str,
        file_path: str,
        lines: list[str],
    ) -> list[ComplianceFinding]:
        """Check GDPR compliance."""
        findings = []
        import re
        
        # Check for consent mechanism
        if re.search(r'(email|personal|user_data)', code, re.IGNORECASE):
            if not re.search(r'consent', code, re.IGNORECASE):
                findings.append(ComplianceFinding(
                    rule_id="GDPR-CONSENT",
                    rule_name="User Consent Required",
                    status=ComplianceStatus.WARNING,
                    severity=ComplianceSeverity.MAJOR,
                    message="Personal data handling without explicit consent check",
                    file_path=file_path,
                    regulation="GDPR",
                    article="Article 6",
                    remediation="Add consent verification before processing personal data",
                ))
        
        # Check for data logging
        if re.search(r'(log|print|console)\s*\([^)]*\b(email|password|name)\b', code, re.IGNORECASE):
            findings.append(ComplianceFinding(
                rule_id="GDPR-LOGGING",
                rule_name="Personal Data in Logs",
                status=ComplianceStatus.FAIL,
                severity=ComplianceSeverity.CRITICAL,
                message="Personal data may be exposed in logs",
                file_path=file_path,
                regulation="GDPR",
                article="Article 32",
                remediation="Sanitize logs to remove personal data",
            ))
        
        return findings
    
    def _check_hipaa_compliance(
        self,
        code: str,
        file_path: str,
        lines: list[str],
    ) -> list[ComplianceFinding]:
        """Check HIPAA compliance."""
        findings = []
        import re
        
        # Check for unencrypted health data
        if re.search(r'(patient|medical|health)', code, re.IGNORECASE):
            if not re.search(r'(encrypt|hash|bcrypt)', code, re.IGNORECASE):
                findings.append(ComplianceFinding(
                    rule_id="HIPAA-ENCRYPT",
                    rule_name="Health Data Encryption",
                    status=ComplianceStatus.WARNING,
                    severity=ComplianceSeverity.MAJOR,
                    message="Health data should be encrypted",
                    file_path=file_path,
                    regulation="HIPAA",
                    article="Section 164.312",
                    remediation="Encrypt health data at rest and in transit",
                ))
        
        return findings
    
    def _check_pci_compliance(
        self,
        code: str,
        file_path: str,
        lines: list[str],
    ) -> list[ComplianceFinding]:
        """Check PCI-DSS compliance."""
        findings = []
        import re
        
        # Check for credit card storage
        if re.search(r'credit_card|card_number|cvv', code, re.IGNORECASE):
            findings.append(ComplianceFinding(
                rule_id="PCI-STORAGE",
                rule_name="Card Data Storage",
                status=ComplianceStatus.MANUAL_REVIEW,
                severity=ComplianceSeverity.CRITICAL,
                message="Credit card data handling detected - requires PCI compliance review",
                file_path=file_path,
                regulation="PCI-DSS",
                article="Requirement 3",
                remediation="Use tokenization, never store CVV, encrypt card data",
            ))
        
        return findings
    
    def _check_auth_compliance(
        self,
        code: str,
        file_path: str,
        lines: list[str],
    ) -> list[ComplianceFinding]:
        """Check authentication best practices."""
        findings = []
        import re
        
        # Check for password hashing
        if re.search(r'password', code, re.IGNORECASE):
            if not re.search(r'(bcrypt|argon|pbkdf|hash)', code, re.IGNORECASE):
                findings.append(ComplianceFinding(
                    rule_id="AUTH-HASH",
                    rule_name="Password Hashing",
                    status=ComplianceStatus.WARNING,
                    severity=ComplianceSeverity.MAJOR,
                    message="Password handling without visible hashing",
                    file_path=file_path,
                    regulation="Security Best Practice",
                    remediation="Use bcrypt or argon2 to hash passwords",
                ))
        
        return findings
    
    def _evaluate_rule(
        self,
        rule: ComplianceRule,
        code: str,
        file_path: str,
        lines: list[str],
    ) -> list[ComplianceFinding]:
        """Evaluate a single compliance rule against code."""
        import re
        import fnmatch
        findings = []
        
        # Check file pattern
        if rule.file_patterns:
            matches_file = any(
                fnmatch.fnmatch(file_path, pattern)
                for pattern in rule.file_patterns
            )
            if not matches_file:
                return []
        
        # Check patterns
        for pattern in rule.patterns:
            try:
                if re.search(pattern, code, re.IGNORECASE):
                    findings.append(ComplianceFinding(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        status=ComplianceStatus.WARNING,
                        severity=rule.severity,
                        message=rule.description,
                        file_path=file_path,
                        regulation=rule.regulation,
                        article=rule.article,
                        remediation=rule.remediation,
                    ))
            except re.error:
                logger.warning(f"Invalid regex in rule {rule.id}: {pattern}")
        
        return findings

    async def load_rules(self) -> int:
        """
        Load compliance rules from configured paths.
        
        Returns:
            Number of rules loaded
        """
        self._rules = {}
        
        for ruleset_path in self.config.ruleset_paths:
            path = Path(ruleset_path).expanduser()
            if not path.exists():
                logger.debug(f"Ruleset path not found: {path}")
                continue
            
            # Load all .json and .yaml files
            for file_path in path.glob("**/*.json"):
                self._load_ruleset_file(file_path)
            
            for file_path in path.glob("**/*.yaml"):
                self._load_ruleset_file(file_path)
            
            for file_path in path.glob("**/*.yml"):
                self._load_ruleset_file(file_path)
        
        logger.info(f"Loaded {len(self._rules)} compliance rules")
        return len(self._rules)
    
    def _load_ruleset_file(self, file_path: Path) -> None:
        """Load rules from a single file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            if file_path.suffix == ".json":
                data = json.loads(content)
            else:
                data = yaml.safe_load(content)
            
            if not data:
                return
            
            # Handle both single rule and ruleset formats
            rules = data.get("rules", [data]) if isinstance(data, dict) else data
            
            for rule_data in rules:
                if not isinstance(rule_data, dict):
                    continue
                
                # Check if ruleset is enabled
                ruleset_name = rule_data.get("ruleset", file_path.stem)
                if self.config.enabled_rulesets and ruleset_name not in self.config.enabled_rulesets:
                    continue
                
                rule = self._parse_rule(rule_data, ruleset_name)
                if rule and rule.enabled:
                    self._rules[rule.id] = rule
                    
        except Exception as e:
            logger.warning(f"Failed to load ruleset file {file_path}: {e}")
    
    def _parse_rule(self, data: dict, ruleset: str) -> Optional[ComplianceRule]:
        """Parse rule data into ComplianceRule."""
        try:
            rule_id = data.get("id", f"{ruleset}-{len(self._rules)}")
            
            severity_str = data.get("severity", "advisory").lower()
            severity = ComplianceSeverity(severity_str) if severity_str in [s.value for s in ComplianceSeverity] else ComplianceSeverity.ADVISORY
            
            return ComplianceRule(
                id=rule_id,
                name=data.get("name", rule_id),
                description=data.get("description", ""),
                category=data.get("category", "general"),
                severity=severity,
                patterns=data.get("patterns", []),
                file_patterns=data.get("file_patterns", ["*.*"]),
                keywords=data.get("keywords", []),
                regulation=data.get("regulation", ""),
                article=data.get("article", ""),
                remediation=data.get("remediation", ""),
                references=data.get("references", []),
                enabled=data.get("enabled", True),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.warning(f"Failed to parse rule: {e}")
            return None
    
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """
        Process a compliance check request.
        
        Expected message content:
        - "check /path/to/project" - Check project
        - "check file /path/to/file" - Check single file
        - "rules" - List loaded rules
        - "reload" - Reload rules from disk
        """
        self.status = AgentStatus.EXECUTING
        content = str(message.content).strip()
        
        try:
            if content.startswith("check "):
                target = content[6:].strip()
                if target.startswith("file "):
                    return await self._check_file(target[5:].strip(), context)
                return await self._check_project(target, context)
            
            elif content == "rules":
                return await self._list_rules()
            
            elif content == "reload":
                count = await self.load_rules()
                return AgentMessage(
                    content=f"Reloaded {count} compliance rules",
                    type=MessageType.TEXT,
                    sender=self.metadata.id,
                )
            
            else:
                return AgentMessage(
                    content="Unknown command. Use: check <path>, check file <path>, rules, reload",
                    type=MessageType.ERROR,
                    sender=self.metadata.id,
                )
        
        except Exception as e:
            logger.error(f"Compliance agent error: {e}")
            return AgentMessage(
                content=f"Compliance check failed: {str(e)}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
        finally:
            self.status = AgentStatus.IDLE
    
    async def _check_project(
        self,
        path: str,
        context: AgentContext,
    ) -> AgentMessage:
        """Check a project directory."""
        project_path = Path(path)
        if not project_path.exists():
            return AgentMessage(
                content=f"Path not found: {path}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
        
        # If no rules loaded, try loading
        if not self._rules:
            await self.load_rules()
        
        # Empty ruleset = no findings (not an error)
        if not self._rules:
            return AgentMessage(
                content="✅ No compliance rules loaded. Add rules to rulesets/ directory.",
                type=MessageType.TEXT,
                sender=self.metadata.id,
                metadata={"findings_count": 0, "rules_count": 0},
            )
        
        self._findings = []
        
        # Evaluate each rule
        for rule in self._rules.values():
            findings = await self._evaluate_rule(rule, project_path)
            self._findings.extend(findings)
        
        # Optional RAG enrichment
        if self.config.rag_enabled and self._rag:
            await self._enrich_with_rag()
        
        # Optional LLM summary
        llm_summary = ""
        if self.config.llm_enabled and self._llm and self._findings:
            llm_summary = await self._get_llm_summary()
        
        response = self._format_findings(llm_summary)
        
        return AgentMessage(
            content=response,
            type=MessageType.TEXT,
            sender=self.metadata.id,
            metadata={
                "findings_count": len(self._findings),
                "rules_checked": len(self._rules),
                "findings": [f.to_dict() for f in self._findings],
            },
        )
    
    async def _check_file(
        self,
        file_path: str,
        context: AgentContext,
    ) -> AgentMessage:
        """Check a single file."""
        path = Path(file_path)
        if not path.exists():
            return AgentMessage(
                content=f"File not found: {file_path}",
                type=MessageType.ERROR,
                sender=self.metadata.id,
            )
        
        if not self._rules:
            await self.load_rules()
        
        findings = []
        for rule in self._rules.values():
            rule_findings = await self._evaluate_rule_on_file(rule, path)
            findings.extend(rule_findings)
        
        response = self._format_findings_list(findings)
        
        return AgentMessage(
            content=response,
            type=MessageType.TEXT,
            sender=self.metadata.id,
            metadata={
                "findings_count": len(findings),
                "findings": [f.to_dict() for f in findings],
            },
        )
    
    async def _list_rules(self) -> AgentMessage:
        """List loaded rules."""
        if not self._rules:
            await self.load_rules()
        
        lines = [f"📋 Loaded {len(self._rules)} compliance rules:\n"]
        
        # Group by regulation
        by_regulation: dict[str, list[ComplianceRule]] = {}
        for rule in self._rules.values():
            reg = rule.regulation or "General"
            by_regulation.setdefault(reg, []).append(rule)
        
        for regulation, rules in sorted(by_regulation.items()):
            lines.append(f"\n**{regulation}** ({len(rules)} rules):")
            for rule in rules[:5]:  # Show first 5
                lines.append(f"  • {rule.id}: {rule.name}")
            if len(rules) > 5:
                lines.append(f"  ... and {len(rules) - 5} more")
        
        return AgentMessage(
            content="\n".join(lines),
            type=MessageType.TEXT,
            sender=self.metadata.id,
            metadata={"rules_count": len(self._rules)},
        )
    
    async def _evaluate_rule(
        self,
        rule: ComplianceRule,
        project_path: Path,
    ) -> list[ComplianceFinding]:
        """Evaluate a rule against a project."""
        findings = []
        
        for pattern in rule.file_patterns:
            for file_path in project_path.rglob(pattern):
                if file_path.is_file():
                    file_findings = await self._evaluate_rule_on_file(rule, file_path)
                    findings.extend(file_findings)
        
        return findings
    
    async def _evaluate_rule_on_file(
        self,
        rule: ComplianceRule,
        file_path: Path,
    ) -> list[ComplianceFinding]:
        """Evaluate a rule on a single file."""
        import re
        
        findings = []
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            
            # Check patterns
            for pattern in rule.patterns:
                try:
                    regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                    for i, line in enumerate(lines, 1):
                        if regex.search(line):
                            findings.append(ComplianceFinding(
                                rule_id=rule.id,
                                rule_name=rule.name,
                                status=ComplianceStatus.FAIL,
                                severity=rule.severity,
                                message=f"Pattern match: {pattern}",
                                file_path=str(file_path),
                                line_number=i,
                                evidence=line.strip()[:200],
                                remediation=rule.remediation,
                                regulation=rule.regulation,
                                article=rule.article,
                            ))
                except re.error as e:
                    logger.warning(f"Invalid regex in rule {rule.id}: {e}")
            
            # Check keywords
            for keyword in rule.keywords:
                for i, line in enumerate(lines, 1):
                    if keyword.lower() in line.lower():
                        findings.append(ComplianceFinding(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            status=ComplianceStatus.WARNING,
                            severity=rule.severity,
                            message=f"Keyword found: {keyword}",
                            file_path=str(file_path),
                            line_number=i,
                            evidence=line.strip()[:200],
                            remediation=rule.remediation,
                            regulation=rule.regulation,
                            article=rule.article,
                        ))
                        
        except Exception as e:
            logger.warning(f"Failed to evaluate rule {rule.id} on {file_path}: {e}")
        
        return findings
    
    async def _enrich_with_rag(self) -> None:
        """Enrich findings with RAG context."""
        if not self._rag or not self._findings:
            return
        
        # Get relevant compliance context
        try:
            for finding in self._findings[:10]:  # Limit to avoid too many queries
                query = f"{finding.regulation} {finding.rule_name}"
                results = await self._rag.query("compliance", query, top_k=2)
                
                if results:
                    # Add context to finding
                    finding.evidence += f"\n\nRelevant context:\n{results[0].content[:500]}"
        except Exception as e:
            logger.warning(f"RAG enrichment failed: {e}")
    
    async def _get_llm_summary(self) -> str:
        """Get LLM summary of findings."""
        if not self._llm or not self.config.llm_enabled:
            return ""
        
        findings_text = "\n".join([
            f"- {f.severity.value}: {f.rule_name} ({f.regulation})"
            for f in self._findings[:15]
        ])
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content="""You are a compliance expert. Summarize these compliance findings:
1. Most critical issues requiring immediate attention
2. Patterns or common themes
3. Recommended priority for remediation

Be concise.""",
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=f"Compliance findings:\n{findings_text}",
            ),
        ]
        
        try:
            response = await self._llm.complete(messages, LLMConfig(
                model=self._llm.default_model,
                max_tokens=400,
            ))
            return response.content or ""
        except Exception as e:
            logger.warning(f"LLM summary failed: {e}")
            return ""
    
    def _format_findings(self, llm_summary: str = "") -> str:
        """Format all findings as text."""
        return self._format_findings_list(self._findings, llm_summary)
    
    def _format_findings_list(
        self,
        findings: list[ComplianceFinding],
        llm_summary: str = "",
    ) -> str:
        """Format a list of findings as text."""
        # Filter by config
        filtered = [
            f for f in findings
            if self._severity_value(f.severity) >= self._severity_value(self.config.min_severity)
        ]
        
        if not self.config.include_passed:
            filtered = [f for f in filtered if f.status != ComplianceStatus.PASS]
        
        if not filtered:
            return "✅ All compliance checks passed."
        
        lines = [f"📋 Compliance Report: {len(filtered)} finding(s)\n"]
        
        # Group by regulation
        by_regulation: dict[str, list[ComplianceFinding]] = {}
        for f in filtered:
            reg = f.regulation or "General"
            by_regulation.setdefault(reg, []).append(f)
        
        for regulation, reg_findings in sorted(by_regulation.items()):
            lines.append(f"\n**{regulation}** ({len(reg_findings)} findings):")
            
            for f in reg_findings:
                status_icon = {
                    ComplianceStatus.FAIL: "❌",
                    ComplianceStatus.WARNING: "⚠️",
                    ComplianceStatus.PASS: "✅",
                    ComplianceStatus.MANUAL_REVIEW: "👁️",
                }.get(f.status, "•")
                
                lines.append(f"\n  {status_icon} **{f.rule_name}** [{f.severity.value}]")
                if f.file_path:
                    lines.append(f"     📁 {f.file_path}:{f.line_number or 0}")
                lines.append(f"     {f.message}")
                if f.remediation:
                    lines.append(f"     💡 {f.remediation[:100]}")
        
        if llm_summary:
            lines.append(f"\n📋 Summary:\n{llm_summary}")
        
        return "\n".join(lines)
    
    def _severity_value(self, severity: ComplianceSeverity) -> int:
        """Get numeric value for severity."""
        values = {
            ComplianceSeverity.ADVISORY: 0,
            ComplianceSeverity.MINOR: 1,
            ComplianceSeverity.MAJOR: 2,
            ComplianceSeverity.CRITICAL: 3,
        }
        return values.get(severity, 0)

"""
Coding Agent Plugin

A coding agent that ONLY produces patches (unified diff format).
This agent:
1. NEVER writes files directly
2. Outputs only unified diff format
3. Receives RAG context + user intent
4. Validates patches before returning

Safety guarantees:
- Agent has NO file write capability
- Output is always unified diff
- Patches are validated (syntax, no secrets, no config edits by default)
- Invalid patches are rejected
"""

import difflib
import logging
import re
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


class PatchValidationError(Exception):
    """Raised when a patch fails validation."""
    pass


class PatchType(str, Enum):
    """Types of code changes."""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    TEST = "test"
    DOCS = "docs"


@dataclass
class PatchResult:
    """
    Result of code generation - always a patch.
    """
    file_path: str
    original_content: str
    new_content: str
    unified_diff: str
    patch_type: PatchType
    description: str
    line_count_added: int = 0
    line_count_removed: int = 0
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "unified_diff": self.unified_diff,
            "patch_type": self.patch_type.value,
            "description": self.description,
            "line_count_added": self.line_count_added,
            "line_count_removed": self.line_count_removed,
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CodingAgentConfig:
    """Configuration for coding agent."""
    # LLM settings
    temperature: float = 0.3  # Low for consistent code
    max_tokens: int = 4096
    
    # Validation settings
    validate_syntax: bool = True
    reject_secrets: bool = True
    reject_config_edits: bool = True
    max_diff_lines: int = 500
    
    # NEW: Integration with Context Agent and RAG Agent
    auto_register_files: bool = True  # Register generated files with Context Agent
    auto_index_summaries: bool = True  # Index summaries with RAG Agent
    use_project_context: bool = True  # Get project summary from Context Agent
    
    # Restricted patterns (will reject patches containing these)
    restricted_patterns: list[str] = field(default_factory=lambda: [
        r"api_key\s*=",
        r"password\s*=",
        r"secret\s*=",
        r"AWS_SECRET",
        r"PRIVATE_KEY",
    ])
    
    # Restricted file patterns (won't generate patches for these)
    restricted_files: list[str] = field(default_factory=lambda: [
        "*.env",
        "*.pem",
        "*.key",
        "*credentials*",
        "*secrets*",
        ".git/*",
    ])
    
    # RAG settings
    use_rag_context: bool = True
    max_context_tokens: int = 2000


class CodingAgent(AgentBase):
    """
    Coding agent that produces patches only.
    
    This agent:
    - NEVER writes files - only produces unified diffs
    - Validates all patches before returning
    - Uses RAG context for better code understanding
    - Rejects patches that contain secrets or edit restricted files
    
    Example:
        ```python
        agent = CodingAgent(llm_provider=llm)
        result = await agent.generate_patch(
            file_path="/path/to/file.py",
            intent="Add error handling to the process function",
            context=rag_context,
        )
        print(result.unified_diff)
        ```
    """
    
    PROMPT_TEMPLATE = '''You are an expert programmer. Generate a code change as a unified diff.

RULES:
1. Output ONLY the unified diff - no explanations before or after
2. Use proper unified diff format with --- and +++ headers
3. Include 3 lines of context around changes
4. Make minimal, focused changes
5. Preserve existing code style and patterns
6. Do NOT include secrets, API keys, or credentials

FILE: {file_path}
CURRENT CONTENT:
```
{current_content}
```

{rag_context}

USER REQUEST: {intent}

OUTPUT (unified diff only):'''
    
    # NEW: Token-efficient prompt that uses project summary instead of raw code
    PROMPT_TEMPLATE_WITH_CONTEXT = '''You are an expert programmer. Generate a code change as a unified diff.

PROJECT CONTEXT:
{project_summary}

RULES:
1. Output ONLY the unified diff - no explanations before or after
2. Use proper unified diff format with --- and +++ headers
3. Include 3 lines of context around changes
4. Make minimal, focused changes
5. Preserve existing code style and patterns
6. Do NOT include secrets, API keys, or credentials
7. Consider the project type ({project_type}) - if fullstack, may need both backend+frontend

FILE: {file_path}
CURRENT CONTENT:
```
{current_content}
```

{rag_context}

USER REQUEST: {intent}

OUTPUT (unified diff only):'''
    
    def __init__(
        self,
        config: Optional[CodingAgentConfig] = None,
        llm_provider: Optional[LLMProvider] = None,
        rag_service: Optional[Any] = None,
        context_agent: Optional[Any] = None,  # NEW: Context Agent reference
        rag_agent: Optional[Any] = None,  # NEW: RAG Agent reference
    ):
        super().__init__()
        self.config = config or CodingAgentConfig()
        self._llm = llm_provider
        self._rag = rag_service
        # NEW: Agent integrations for token efficiency
        self._context_agent = context_agent
        self._rag_agent = rag_agent
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="coding",
            name="Coding Agent",
            description="Generates code changes as unified diffs (never writes files)",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="patch_generation",
                    description="Generates unified diff patches",
                ),
                AgentCapability(
                    name="patch_validation",
                    description="Validates patches for safety and correctness",
                ),
            ],
            tags=["coding", "patch", "diff", "safe"],
            dependencies=["context_agent", "rag_agent"],
            provides=["code_patches", "code_changes"],
        )
    
    def set_llm(self, provider: LLMProvider) -> None:
        """Set LLM provider."""
        self._llm = provider
    
    def set_rag(self, rag_service: Any) -> None:
        """Set RAG service for context."""
        self._rag = rag_service
    
    def set_context_agent(self, context_agent: Any) -> None:
        """Set Context Agent for project awareness."""
        self._context_agent = context_agent
    
    def set_rag_agent(self, rag_agent: Any) -> None:
        """Set RAG Agent for token-efficient summaries."""
        self._rag_agent = rag_agent
    
    async def process(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """
        Process a coding request.
        
        Expected message content:
        - JSON with file_path and intent
        - Or "patch <file_path>: <intent>"
        """
        self.status = AgentStatus.EXECUTING
        content = str(message.content).strip()
        
        try:
            # Parse request
            if content.startswith("patch "):
                parts = content[6:].split(":", 1)
                if len(parts) != 2:
                    return self._error("Format: patch <file_path>: <intent>")
                file_path = parts[0].strip()
                intent = parts[1].strip()
            else:
                # Try JSON
                import json
                try:
                    data = json.loads(content)
                    file_path = data.get("file_path", "")
                    intent = data.get("intent", "")
                except json.JSONDecodeError:
                    return self._error("Invalid format. Use: patch <file>: <intent>")
            
            if not file_path or not intent:
                return self._error("Both file_path and intent are required")
            
            # Generate patch
            result = await self.generate_patch(file_path, intent, context)
            
            if not result.is_valid:
                return AgentMessage(
                    content=f"❌ Patch rejected:\n" + "\n".join(f"  • {e}" for e in result.validation_errors),
                    type=MessageType.ERROR,
                    sender=self.metadata.id,
                    metadata={"patch": result.to_dict()},
                )
            
            response = self._format_patch_result(result)
            
            return AgentMessage(
                content=response,
                type=MessageType.TEXT,
                sender=self.metadata.id,
                metadata={"patch": result.to_dict()},
            )
        
        except Exception as e:
            logger.error(f"Coding agent error: {e}")
            return self._error(str(e))
        finally:
            self.status = AgentStatus.IDLE
    
    def _error(self, message: str) -> AgentMessage:
        """Create error response."""
        return AgentMessage(
            content=f"Error: {message}",
            type=MessageType.ERROR,
            sender=self.metadata.id,
        )
    
    async def generate_patch(
        self,
        file_path: str,
        intent: str,
        context: Optional[AgentContext] = None,
    ) -> PatchResult:
        """
        Generate a patch for a file.
        
        Args:
            file_path: Path to file to modify
            intent: Description of desired change
            context: Optional agent context with history
            
        Returns:
            PatchResult with unified diff
        """
        path = Path(file_path)
        
        # Validate file is not restricted
        if self._is_restricted_file(file_path):
            return PatchResult(
                file_path=file_path,
                original_content="",
                new_content="",
                unified_diff="",
                patch_type=PatchType.FEATURE,
                description=intent,
                is_valid=False,
                validation_errors=["File is restricted and cannot be modified"],
            )
        
        # Read current content
        if path.exists():
            original_content = path.read_text(encoding="utf-8", errors="ignore")
        else:
            original_content = ""  # New file
        
        # Get RAG context
        rag_context = ""
        if self.config.use_rag_context and self._rag:
            rag_context = await self._get_rag_context(file_path, intent)
        
        # Generate new content via LLM
        if not self._llm:
            return PatchResult(
                file_path=file_path,
                original_content=original_content,
                new_content="",
                unified_diff="",
                patch_type=PatchType.FEATURE,
                description=intent,
                is_valid=False,
                validation_errors=["No LLM provider configured"],
            )
        
        # Build prompt
        prompt = self.PROMPT_TEMPLATE.format(
            file_path=file_path,
            current_content=original_content[:8000],  # Limit content
            rag_context=f"RELEVANT CONTEXT:\n{rag_context}\n" if rag_context else "",
            intent=intent,
        )
        
        messages = [
            LLMMessage(role=LLMRole.USER, content=prompt),
        ]
        
        try:
            response = await self._llm.complete(messages, LLMConfig(
                model=self._llm.default_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ))
            
            llm_output = response.content or ""
            
            # Parse diff from LLM output
            unified_diff = self._extract_diff(llm_output)
            
            if not unified_diff:
                # LLM didn't produce a diff - try to create one from content
                new_content = self._extract_code(llm_output)
                if new_content:
                    unified_diff = self._create_diff(file_path, original_content, new_content)
                else:
                    return PatchResult(
                        file_path=file_path,
                        original_content=original_content,
                        new_content="",
                        unified_diff="",
                        patch_type=PatchType.FEATURE,
                        description=intent,
                        is_valid=False,
                        validation_errors=["LLM did not produce a valid diff"],
                    )
            
            # Apply diff to get new content
            new_content = self._apply_diff(original_content, unified_diff)
            if new_content is None:
                new_content = original_content  # Couldn't apply
            
            # Create result
            result = PatchResult(
                file_path=file_path,
                original_content=original_content,
                new_content=new_content,
                unified_diff=unified_diff,
                patch_type=self._detect_patch_type(intent),
                description=intent,
            )
            
            # Count lines
            result.line_count_added = unified_diff.count("\n+") - 1  # Exclude header
            result.line_count_removed = unified_diff.count("\n-") - 1
            
            # Validate
            self._validate_patch(result)
            
            # NEW: Register generated file with Context Agent (for memory)
            if result.is_valid and self.config.auto_register_files:
                self._register_generated_file(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Patch generation failed: {e}")
            return PatchResult(
                file_path=file_path,
                original_content=original_content,
                new_content="",
                unified_diff="",
                patch_type=PatchType.FEATURE,
                description=intent,
                is_valid=False,
                validation_errors=[f"Generation failed: {str(e)}"],
            )
    
    async def _get_rag_context(self, file_path: str, intent: str) -> str:
        """Get RAG context for code generation."""
        # NEW: Prefer RAG Agent summaries (token efficient)
        if self._rag_agent:
            try:
                summaries = await self._rag_agent.get_relevant_summaries(
                    f"{Path(file_path).name} {intent}"
                )
                if summaries:
                    return summaries
            except Exception as e:
                logger.warning(f"RAG Agent retrieval failed: {e}")
        
        # Fallback to raw RAG service
        if not self._rag:
            return ""
        
        try:
            # Query code domain
            query = f"{Path(file_path).name} {intent}"
            results = await self._rag.query("code", query, top_k=3)
            
            if not results:
                return ""
            
            return self._rag.get_context_for_prompt(
                results,
                max_tokens=self.config.max_context_tokens,
            )
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")
            return ""
    
    def _get_project_context(self) -> tuple[str, str]:
        """
        Get project summary from Context Agent.
        Returns (project_summary, project_type) - token efficient!
        """
        if not self._context_agent or not self.config.use_project_context:
            return ("", "unknown")
        
        try:
            summary = self._context_agent.get_project_summary_for_prompt()
            project_structure = self._context_agent.get_project_structure()
            project_type = project_structure.project_type if project_structure else "unknown"
            return (summary, project_type)
        except Exception as e:
            logger.warning(f"Project context retrieval failed: {e}")
            return ("", "unknown")
    
    def _register_generated_file(self, result: "PatchResult") -> None:
        """
        Register a generated file with Context Agent and RAG Agent.
        This enables persistent memory - next request already knows this file!
        """
        if not result.is_valid or not result.new_content:
            return
        
        # Register with Context Agent (memory)
        if self._context_agent and self.config.auto_register_files:
            try:
                self._context_agent.register_generated_file(
                    file_path=result.file_path,
                    content=result.new_content,
                    file_type="code",
                )
                logger.info(f"Registered file with Context Agent: {result.file_path}")
            except Exception as e:
                logger.warning(f"Failed to register with Context Agent: {e}")
        
        # Index with RAG Agent (summaries for token efficiency)
        if self._rag_agent and self.config.auto_index_summaries:
            try:
                self._rag_agent.index_file_with_summary(
                    file_path=result.file_path,
                    content=result.new_content,
                )
                logger.info(f"Indexed summary with RAG Agent: {result.file_path}")
            except Exception as e:
                logger.warning(f"Failed to index with RAG Agent: {e}")
    
    def _is_restricted_file(self, file_path: str) -> bool:
        """Check if file is restricted."""
        import fnmatch
        
        for pattern in self.config.restricted_files:
            if fnmatch.fnmatch(file_path, pattern):
                return True
            if fnmatch.fnmatch(Path(file_path).name, pattern):
                return True
        
        return False
    
    def _extract_diff(self, llm_output: str) -> str:
        """Extract unified diff from LLM output."""
        lines = llm_output.split("\n")
        diff_lines = []
        in_diff = False
        
        for line in lines:
            # Start of diff
            if line.startswith("---") or line.startswith("diff --git"):
                in_diff = True
                diff_lines = [line]
            elif in_diff:
                diff_lines.append(line)
                # End of diff (blank line after hunks)
                if line.strip() == "" and len(diff_lines) > 5:
                    # Check if we have complete diff
                    has_hunks = any(l.startswith("@@") for l in diff_lines)
                    if has_hunks:
                        break
        
        if diff_lines and any(l.startswith("@@") for l in diff_lines):
            return "\n".join(diff_lines)
        
        return ""
    
    def _extract_code(self, llm_output: str) -> str:
        """Extract code block from LLM output if no diff."""
        # Look for code blocks
        code_block_pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(code_block_pattern, llm_output, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        return ""
    
    def _create_diff(self, file_path: str, original: str, new: str) -> str:
        """Create unified diff from original and new content."""
        original_lines = original.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{Path(file_path).name}",
            tofile=f"b/{Path(file_path).name}",
        )
        
        return "".join(diff)
    
    def _apply_diff(self, original: str, diff: str) -> Optional[str]:
        """Apply unified diff to get new content."""
        # Simple diff application - for complex cases, use patch library
        try:
            lines = original.splitlines(keepends=True)
            diff_lines = diff.splitlines()
            
            # Parse hunks
            result_lines = list(lines)
            offset = 0
            
            i = 0
            while i < len(diff_lines):
                line = diff_lines[i]
                if line.startswith("@@"):
                    # Parse hunk header
                    match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                    if match:
                        old_start = int(match.group(1)) - 1
                        # Apply hunk changes
                        j = i + 1
                        pos = old_start + offset
                        while j < len(diff_lines) and not diff_lines[j].startswith("@@"):
                            hunk_line = diff_lines[j]
                            if hunk_line.startswith("-"):
                                if pos < len(result_lines):
                                    result_lines.pop(pos)
                                    offset -= 1
                            elif hunk_line.startswith("+"):
                                result_lines.insert(pos, hunk_line[1:] + "\n")
                                pos += 1
                                offset += 1
                            else:
                                pos += 1
                            j += 1
                        i = j - 1
                i += 1
            
            return "".join(result_lines)
            
        except Exception as e:
            logger.warning(f"Diff application failed: {e}")
            return None
    
    def _detect_patch_type(self, intent: str) -> PatchType:
        """Detect patch type from intent."""
        intent_lower = intent.lower()
        
        if any(x in intent_lower for x in ["fix", "bug", "error", "issue"]):
            return PatchType.BUGFIX
        if any(x in intent_lower for x in ["test", "spec", "unittest"]):
            return PatchType.TEST
        if any(x in intent_lower for x in ["doc", "comment", "readme"]):
            return PatchType.DOCS
        if any(x in intent_lower for x in ["refactor", "clean", "improve"]):
            return PatchType.REFACTOR
        
        return PatchType.FEATURE
    
    def _validate_patch(self, result: PatchResult) -> None:
        """Validate a patch for safety and correctness."""
        errors = []
        
        # Check for restricted patterns
        if self.config.reject_secrets:
            for pattern in self.config.restricted_patterns:
                if re.search(pattern, result.unified_diff, re.IGNORECASE):
                    errors.append(f"Patch contains restricted pattern: {pattern}")
        
        # Check diff size
        if self.config.max_diff_lines > 0:
            line_count = len(result.unified_diff.splitlines())
            if line_count > self.config.max_diff_lines:
                errors.append(f"Patch too large: {line_count} lines (max {self.config.max_diff_lines})")
        
        # Check for config file edits
        if self.config.reject_config_edits:
            config_patterns = [".env", "config.", "settings.", "credentials"]
            for pattern in config_patterns:
                if pattern in result.file_path.lower():
                    errors.append(f"Config file edits not allowed: {result.file_path}")
        
        # Basic syntax validation (for Python files)
        if self.config.validate_syntax and result.file_path.endswith(".py"):
            syntax_error = self._validate_python_syntax(result.new_content)
            if syntax_error:
                errors.append(f"Python syntax error: {syntax_error}")
        
        result.validation_errors = errors
        result.is_valid = len(errors) == 0
    
    def _validate_python_syntax(self, code: str) -> Optional[str]:
        """Validate Python syntax."""
        if not code:
            return None
        
        try:
            compile(code, "<string>", "exec")
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}"
    
    def _format_patch_result(self, result: PatchResult) -> str:
        """Format patch result for display."""
        lines = [
            f"📝 Patch Generated: {result.file_path}",
            f"Type: {result.patch_type.value}",
            f"Changes: +{result.line_count_added} / -{result.line_count_removed} lines",
            "",
            "```diff",
            result.unified_diff,
            "```",
            "",
            "⚠️ This is a preview. Apply with: `git apply` or manually copy changes.",
        ]
        
        return "\n".join(lines)
    
    # SAFETY: These methods ensure the agent cannot write files
    
    async def write_file(self, *args, **kwargs) -> None:
        """DISABLED: Coding agent cannot write files directly."""
        raise PermissionError("CodingAgent only produces patches - use apply_patch externally")
    
    async def modify_file(self, *args, **kwargs) -> None:
        """DISABLED: Coding agent cannot modify files directly."""
        raise PermissionError("CodingAgent only produces patches - use apply_patch externally")
    
    async def delete_file(self, *args, **kwargs) -> None:
        """DISABLED: Coding agent cannot delete files."""
        raise PermissionError("CodingAgent cannot delete files")

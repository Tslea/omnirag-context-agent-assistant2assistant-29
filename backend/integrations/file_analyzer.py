"""
File Analyzer

Analyzes source code files and generates detailed summaries
suitable for senior developers and Copilot context.

Supports: Python, TypeScript, JavaScript, Java, Go, and more.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    docstring: str = ""
    methods: list[str] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    is_dataclass: bool = False
    is_abstract: bool = False


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    params: list[str] = field(default_factory=list)
    returns: str = ""
    docstring: str = ""
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    is_private: bool = False
    complexity: int = 1  # Cyclomatic complexity estimate


@dataclass 
class FileAnalysis:
    """Complete analysis of a source file."""
    file_path: str
    relative_path: str
    language: str
    lines_of_code: int
    
    # Structure
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    constants: list[str] = field(default_factory=list)
    
    # Module info
    module_docstring: str = ""
    
    # Purpose inference
    purpose: str = ""
    key_responsibilities: list[str] = field(default_factory=list)
    
    # Dependencies
    internal_deps: list[str] = field(default_factory=list)  # Project files
    external_deps: list[str] = field(default_factory=list)  # External packages
    
    # Quality indicators
    has_type_hints: bool = False
    has_docstrings: bool = False
    test_related: bool = False
    
    # Security/Compliance flags
    security_flags: list[str] = field(default_factory=list)
    compliance_flags: list[str] = field(default_factory=list)


class FileAnalyzer:
    """
    Analyzes source files to generate detailed summaries.
    
    Example:
        ```python
        analyzer = FileAnalyzer()
        
        # Analyze a file
        analysis = analyzer.analyze_file("/path/to/file.py", content)
        
        # Get summary for Copilot
        summary = analyzer.to_file_summary(analysis)
        ```
    """
    
    # Security-sensitive patterns
    SECURITY_PATTERNS = {
        "hardcoded_secret": re.compile(
            r'(password|secret|api_key|apikey|token|auth)\s*=\s*["\'][^"\']+["\']',
            re.IGNORECASE
        ),
        "sql_injection": re.compile(
            r'(execute|query)\s*\(\s*[f"\'].*\{.*\}|%s.*%',
            re.IGNORECASE
        ),
        "shell_injection": re.compile(
            r'(os\.system|subprocess\.\w+|shell=True)',
            re.IGNORECASE
        ),
        "eval_usage": re.compile(r'\beval\s*\('),
        "pickle_usage": re.compile(r'pickle\.(load|loads)'),
    }
    
    # Compliance patterns
    COMPLIANCE_PATTERNS = {
        "pii_handling": re.compile(
            r'(email|phone|address|ssn|social_security|credit_card|birthdate)',
            re.IGNORECASE
        ),
        "logging_sensitive": re.compile(
            r'(log|print|console)\s*\(.*password|token|secret',
            re.IGNORECASE
        ),
        "no_encryption": re.compile(
            r'password.*=.*plain|store.*password.*text',
            re.IGNORECASE
        ),
    }
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else None
    
    def analyze_file(self, file_path: str, content: str) -> FileAnalysis:
        """
        Analyze a source file and return detailed analysis.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            FileAnalysis with all extracted information
        """
        path = Path(file_path)
        language = self._detect_language(path)
        
        analysis = FileAnalysis(
            file_path=file_path,
            relative_path=str(path.relative_to(self.project_root)) if self.project_root else path.name,
            language=language,
            lines_of_code=len(content.splitlines()),
        )
        
        # Analyze based on language
        if language == "python":
            self._analyze_python(content, analysis)
        elif language in ("typescript", "javascript"):
            self._analyze_js_ts(content, analysis)
        elif language == "java":
            self._analyze_java(content, analysis)
        elif language == "go":
            self._analyze_go(content, analysis)
        else:
            self._analyze_generic(content, analysis)
        
        # Check for security and compliance issues
        self._check_security(content, analysis)
        self._check_compliance(content, analysis)
        
        # Infer purpose
        self._infer_purpose(analysis)
        
        return analysis
    
    def _detect_language(self, path: Path) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".dart": "dart",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".swift": "swift",
            ".vue": "vue",
            ".svelte": "svelte",
            ".scala": "scala",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".md": "markdown",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sql": "sql",
        }
        return ext_map.get(path.suffix.lower(), "unknown")
    
    def _analyze_python(self, content: str, analysis: FileAnalysis) -> None:
        """Analyze Python file using AST."""
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Failed to parse Python file: {e}")
            self._analyze_generic(content, analysis)
            return
        
        # Module docstring
        analysis.module_docstring = ast.get_docstring(tree) or ""
        
        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis.imports.append(alias.name)
                    if not alias.name.startswith(("backend.", "frontend.", ".")):
                        analysis.external_deps.append(alias.name.split(".")[0])
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                analysis.imports.append(module)
                if module.startswith(("backend.", "frontend.", ".")):
                    analysis.internal_deps.append(module)
                else:
                    analysis.external_deps.append(module.split(".")[0])
            
            # Classes
            elif isinstance(node, ast.ClassDef):
                class_info = ClassInfo(
                    name=node.name,
                    docstring=ast.get_docstring(node) or "",
                    base_classes=[
                        self._get_base_name(base) for base in node.bases
                    ],
                    decorators=[
                        self._get_decorator_name(d) for d in node.decorator_list
                    ],
                )
                
                # Check for special class types
                class_info.is_dataclass = "dataclass" in class_info.decorators
                class_info.is_abstract = any(
                    "ABC" in b or "Abstract" in b for b in class_info.base_classes
                )
                
                # Get methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        class_info.methods.append(item.name)
                
                analysis.classes.append(class_info)
            
            # Functions (top-level only)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip if inside a class
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                    func_info = FunctionInfo(
                        name=node.name,
                        params=[arg.arg for arg in node.args.args],
                        docstring=ast.get_docstring(node) or "",
                        decorators=[
                            self._get_decorator_name(d) for d in node.decorator_list
                        ],
                        is_async=isinstance(node, ast.AsyncFunctionDef),
                        is_private=node.name.startswith("_"),
                    )
                    
                    # Get return type hint
                    if node.returns:
                        func_info.returns = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                    
                    analysis.functions.append(func_info)
            
            # Constants (top-level assignments)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        analysis.constants.append(target.id)
        
        # Check for type hints
        analysis.has_type_hints = ":" in content and "->" in content
        analysis.has_docstrings = '"""' in content or "'''" in content
        analysis.test_related = "test" in analysis.file_path.lower()
    
    def _analyze_js_ts(self, content: str, analysis: FileAnalysis) -> None:
        """Analyze JavaScript/TypeScript file using regex."""
        # Imports
        import_pattern = re.compile(
            r'import\s+(?:{[^}]+}|\*\s+as\s+\w+|\w+)\s+from\s+["\']([^"\']+)["\']'
        )
        for match in import_pattern.finditer(content):
            module = match.group(1)
            analysis.imports.append(module)
            if module.startswith(("./", "../", "@/")):
                analysis.internal_deps.append(module)
            else:
                analysis.external_deps.append(module.split("/")[0])
        
        # Exports
        export_pattern = re.compile(r'export\s+(?:default\s+)?(?:class|function|const|interface|type)\s+(\w+)')
        analysis.exports = [m.group(1) for m in export_pattern.finditer(content)]
        
        # Classes
        class_pattern = re.compile(r'class\s+(\w+)(?:\s+extends\s+(\w+))?')
        for match in class_pattern.finditer(content):
            analysis.classes.append(ClassInfo(
                name=match.group(1),
                base_classes=[match.group(2)] if match.group(2) else [],
            ))
        
        # Functions
        func_patterns = [
            re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)'),
            re.compile(r'const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'),
            re.compile(r'(\w+)\s*:\s*\([^)]*\)\s*=>'),
        ]
        
        for pattern in func_patterns:
            for match in pattern.finditer(content):
                name = match.group(1)
                analysis.functions.append(FunctionInfo(
                    name=name,
                    is_async="async" in match.group(0),
                    is_private=name.startswith("_"),
                ))
        
        # React components
        component_pattern = re.compile(r'(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)\s*\(')
        for match in component_pattern.finditer(content):
            if match.group(1) not in [c.name for c in analysis.classes]:
                analysis.classes.append(ClassInfo(
                    name=match.group(1),
                    docstring="React Component",
                ))
        
        analysis.has_type_hints = ": " in content and ("interface" in content or "type " in content)
        analysis.test_related = ".test." in analysis.file_path or ".spec." in analysis.file_path
    
    def _analyze_java(self, content: str, analysis: FileAnalysis) -> None:
        """Analyze Java file using regex."""
        # Package/imports
        import_pattern = re.compile(r'import\s+([\w.]+);')
        analysis.imports = [m.group(1) for m in import_pattern.finditer(content)]
        
        # Classes
        class_pattern = re.compile(
            r'(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'
        )
        for match in class_pattern.finditer(content):
            analysis.classes.append(ClassInfo(
                name=match.group(1),
                base_classes=[match.group(2)] if match.group(2) else [],
                is_abstract="abstract" in match.group(0),
            ))
        
        # Methods
        method_pattern = re.compile(
            r'(?:public|private|protected)?\s*(?:static\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)'
        )
        for match in method_pattern.finditer(content):
            analysis.functions.append(FunctionInfo(
                name=match.group(2),
                returns=match.group(1),
                params=match.group(3).split(",") if match.group(3) else [],
            ))
    
    def _analyze_go(self, content: str, analysis: FileAnalysis) -> None:
        """Analyze Go file using regex."""
        # Imports
        import_pattern = re.compile(r'import\s+(?:\(\s*)?["\']([^"\']+)["\']')
        analysis.imports = [m.group(1) for m in import_pattern.finditer(content)]
        
        # Functions
        func_pattern = re.compile(r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)(?:\s*(\w+))?')
        for match in func_pattern.finditer(content):
            analysis.functions.append(FunctionInfo(
                name=match.group(1),
                params=match.group(2).split(",") if match.group(2) else [],
                returns=match.group(3) or "",
            ))
        
        # Structs (as classes)
        struct_pattern = re.compile(r'type\s+(\w+)\s+struct')
        for match in struct_pattern.finditer(content):
            analysis.classes.append(ClassInfo(name=match.group(1)))
    
    def _analyze_generic(self, content: str, analysis: FileAnalysis) -> None:
        """Generic analysis for unknown languages."""
        # Count functions/methods by common patterns
        func_pattern = re.compile(r'\b(function|def|func|fn|sub|method)\s+(\w+)')
        for match in func_pattern.finditer(content):
            analysis.functions.append(FunctionInfo(name=match.group(2)))
        
        # Count classes
        class_pattern = re.compile(r'\b(class|struct|interface|type)\s+(\w+)')
        for match in class_pattern.finditer(content):
            analysis.classes.append(ClassInfo(name=match.group(2)))
    
    def _check_security(self, content: str, analysis: FileAnalysis) -> None:
        """Check for security issues."""
        for name, pattern in self.SECURITY_PATTERNS.items():
            if pattern.search(content):
                analysis.security_flags.append(name)
    
    def _check_compliance(self, content: str, analysis: FileAnalysis) -> None:
        """Check for compliance issues."""
        for name, pattern in self.COMPLIANCE_PATTERNS.items():
            if pattern.search(content):
                analysis.compliance_flags.append(name)
    
    def _infer_purpose(self, analysis: FileAnalysis) -> None:
        """Infer the purpose of the file from its content and path."""
        purposes = []
        responsibilities = []
        
        # From module docstring
        if analysis.module_docstring:
            first_line = analysis.module_docstring.split("\n")[0].strip()
            if first_line and len(first_line) > 5:
                purposes.append(first_line)
        
        # Get path parts for pattern matching
        path = Path(analysis.file_path)
        name = path.stem.lower()
        parent = path.parent.name.lower() if path.parent else ""
        full_path = analysis.relative_path.lower()
        
        # React/Frontend patterns (check path hierarchy)
        if "components" in full_path:
            if "common" in full_path or "ui" in full_path:
                purposes.append("Reusable UI Component")
                responsibilities.append("Shared UI element across the application")
            elif "chat" in full_path:
                purposes.append("Chat UI Component")
                responsibilities.append("Part of the chat interface system")
            elif "layout" in full_path:
                purposes.append("Layout Component")
                responsibilities.append("Page layout structure and navigation")
            elif "auth" in full_path:
                purposes.append("Authentication Component")
                responsibilities.append("User authentication UI")
            elif "immersive" in full_path:
                purposes.append("Immersive Experience Component")
                responsibilities.append("Interactive/immersive UI element")
            elif "admin" in full_path:
                purposes.append("Admin UI Component")
                responsibilities.append("Administrative interface element")
            else:
                purposes.append("UI Component")
                responsibilities.append("React component for UI rendering")
        
        elif "pages" in full_path or "views" in full_path:
            if "admin" in full_path:
                purposes.append("Admin Page")
                responsibilities.append("Administrative dashboard page")
            else:
                purposes.append("Page Component")
                responsibilities.append("Full page/route component")
        
        elif "stores" in full_path or "store" in full_path:
            purposes.append("State Store")
            if "auth" in name:
                responsibilities.append("Manages authentication state (Zustand/Redux)")
            elif "chat" in name:
                responsibilities.append("Manages chat/conversation state")
            elif "character" in name:
                responsibilities.append("Manages character data state")
            else:
                responsibilities.append("Application state management")
        
        elif "hooks" in full_path:
            purposes.append("Custom React Hook")
            responsibilities.append("Reusable stateful logic")
        
        elif "lib" in full_path or "utils" in full_path:
            purposes.append("Utility Module")
            responsibilities.append("Helper functions and utilities")
        
        # Backend patterns
        elif "agents" in full_path:
            purposes.append("AI Agent Module")
            responsibilities.append("Agent logic and behavior implementation")
        
        elif "api" in full_path or "routes" in full_path:
            purposes.append("API Endpoint")
            responsibilities.append("HTTP route handler")
        
        elif "services" in full_path:
            purposes.append("Service Layer")
            responsibilities.append("Business logic implementation")
        
        elif "repositories" in full_path or "dal" in full_path:
            purposes.append("Data Access Layer")
            responsibilities.append("Database operations and queries")
        
        elif "models" in full_path or "schemas" in full_path:
            purposes.append("Data Model")
            responsibilities.append("Data structure definition")
        
        elif "scripts" in full_path:
            # Analyze script purpose from name
            if "init" in name or "seed" in name:
                purposes.append("Database Initialization Script")
                responsibilities.append("Sets up database schema/data")
            elif "index" in name:
                purposes.append("Knowledge Indexing Script")
                responsibilities.append("Indexes data for search/RAG")
            elif "chat" in name or "client" in name:
                purposes.append("Chat Client Script")
                responsibilities.append("CLI/test client for chat")
            elif "run" in name or "server" in name:
                purposes.append("Server Runner Script")
                responsibilities.append("Starts/runs the server")
            else:
                purposes.append("Utility Script")
                responsibilities.append("Automation/utility script")
        
        elif "alembic" in full_path:
            purposes.append("Database Migration")
            responsibilities.append("Alembic migration for schema changes")
        
        elif "migrations" in full_path:
            purposes.append("Database Migration")
            responsibilities.append("Schema migration script")
        
        # Filename-based inference (fallback)
        if not purposes:
            if name in ("index", "main", "app", "__init__"):
                purposes.append("Application Entry Point")
                responsibilities.append("Module entry point / exports")
            elif "test" in name or "spec" in name:
                purposes.append("Test File")
                responsibilities.append("Unit/integration tests")
            elif "config" in name or name in ("settings", "constants"):
                purposes.append("Configuration File")
                responsibilities.append("Application settings and constants")
            elif "handler" in name or "controller" in name:
                purposes.append("Request Handler")
                responsibilities.append("Handles incoming requests")
            elif name.endswith(".config") or name.endswith("rc"):
                purposes.append("Configuration File")
                responsibilities.append("Tool/build configuration")
        
        # Analyze exports/classes for more context
        for cls in analysis.classes:
            cls_name = cls.name
            if cls_name.endswith("Store"):
                responsibilities.append(f"`{cls_name}`: State management store")
            elif cls_name.endswith("Service"):
                responsibilities.append(f"`{cls_name}`: Business logic service")
            elif cls_name.endswith("Agent"):
                responsibilities.append(f"`{cls_name}`: AI agent implementation")
            elif cls_name.endswith("Handler") or cls_name.endswith("Controller"):
                responsibilities.append(f"`{cls_name}`: Request handling")
            elif cls_name.endswith("Model") or cls_name.endswith("Schema"):
                responsibilities.append(f"`{cls_name}`: Data model definition")
            elif cls_name[0].isupper() and analysis.language in ("typescript", "javascript"):
                # Likely a React component
                if not any(cls_name in r for r in responsibilities):
                    responsibilities.append(f"`{cls_name}`: React component")
        
        # Set final purpose
        analysis.purpose = purposes[0] if purposes else "General module"
        analysis.key_responsibilities = list(dict.fromkeys(responsibilities))[:5]  # Dedupe, limit to 5
    
    def _get_base_name(self, node: ast.expr) -> str:
        """Get the name of a base class."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return str(node)
    
    def _get_decorator_name(self, node: ast.expr) -> str:
        """Get the name of a decorator."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return str(node)
    
    def to_file_summary(self, analysis: FileAnalysis) -> "FileSummary":
        """Convert FileAnalysis to FileSummary for Copilot integration."""
        from backend.integrations.copilot_integration import FileSummary
        
        return FileSummary(
            file_path=analysis.file_path,
            relative_path=analysis.relative_path,
            language=analysis.language,
            lines_of_code=analysis.lines_of_code,
            classes=[
                {
                    "name": c.name,
                    "methods": c.methods,
                    "docstring": c.docstring,
                }
                for c in analysis.classes
            ],
            functions=[
                {
                    "name": f.name,
                    "params": f.params,
                    "returns": f.returns,
                    "docstring": f.docstring,
                }
                for f in analysis.functions
            ],
            imports=analysis.imports,
            exports=analysis.exports,
            purpose=analysis.purpose,
            key_responsibilities=analysis.key_responsibilities,
            dependencies=analysis.internal_deps,
            has_tests=analysis.test_related,
            security_notes=[
                self._security_flag_to_note(flag)
                for flag in analysis.security_flags
            ],
            compliance_notes=[
                self._compliance_flag_to_note(flag)
                for flag in analysis.compliance_flags
            ],
        )
    
    def _security_flag_to_note(self, flag: str) -> str:
        """Convert security flag to human-readable note."""
        notes = {
            "hardcoded_secret": "Contains potential hardcoded secrets",
            "sql_injection": "Potential SQL injection vulnerability",
            "shell_injection": "Potential shell injection risk",
            "eval_usage": "Uses eval() - potential code injection",
            "pickle_usage": "Uses pickle.load - potential deserialization attack",
        }
        return notes.get(flag, flag)
    
    def _compliance_flag_to_note(self, flag: str) -> str:
        """Convert compliance flag to human-readable note."""
        notes = {
            "pii_handling": "Handles PII data - ensure proper protection",
            "logging_sensitive": "May log sensitive data",
            "no_encryption": "May store passwords without encryption",
        }
        return notes.get(flag, flag)

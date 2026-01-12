"""Helpers for applying .gitignore-style filtering during scans."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern

# Baseline ignore rules even if a .gitignore is missing
_DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    ".hg/",
    ".svn/",
    "node_modules/",
    "dist/",
    "build/",
    ".next/",
    "__pycache__/",
    "*.pyc",
    ".venv/",
    "venv/",
    ".idea/",
    ".vscode/",
    ".mypy_cache/",
    ".pytest_cache/",
    "*.egg-info/",
    ".tox/",
    ".cache/",
    "coverage/",
    "htmlcov/",
    ".DS_Store",
    "*.iml",
    "npm-debug.log*",
    "yarn-error.log*",
    "*.log",
]


def _clean_patterns(patterns: Iterable[str]) -> list[str]:
    cleaned = []
    for pattern in patterns:
        if not pattern:
            continue
        stripped = pattern.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cleaned.append(stripped)
    return cleaned


def load_gitignore(root: Path) -> PathSpec:
    """Load .gitignore patterns from ``root`` plus default ignores."""
    patterns: list[str] = []
    gitignore_path = root / ".gitignore"
    if gitignore_path.exists():
        try:
            patterns.extend(gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines())
        except OSError:
            # If reading fails, fall back to defaults only
            pass
    patterns.extend(_DEFAULT_IGNORE_PATTERNS)
    return PathSpec.from_lines(GitWildMatchPattern, _clean_patterns(patterns))


def should_ignore(path: Path, root: Path, spec: Optional[PathSpec] = None) -> bool:
    """Check whether ``path`` is ignored relative to ``root`` using ``spec``."""
    spec = spec or load_gitignore(root)
    try:
        relative = path.relative_to(root)
    except ValueError:
        # If path is outside root, best-effort fallback to absolute posix
        relative = path
    return spec.match_file(relative.as_posix())

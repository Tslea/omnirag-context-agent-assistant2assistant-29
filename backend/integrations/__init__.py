"""
OMNI Integrations Package

Contains integrations with external tools and services.
"""

from backend.integrations.copilot_integration import (
    CopilotIntegration,
    FileSummary,
    ProjectContext,
)
from backend.integrations.file_analyzer import (
    FileAnalyzer,
    FileAnalysis,
    ClassInfo,
    FunctionInfo,
)

__all__ = [
    "CopilotIntegration",
    "FileSummary",
    "ProjectContext",
    "FileAnalyzer",
    "FileAnalysis",
    "ClassInfo",
    "FunctionInfo",
]

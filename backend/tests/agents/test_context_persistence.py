"""
Tests for Context Agent persistence and unified DetailedFileSummary.

These tests verify:
1. DetailedFileSummary serialization/deserialization
2. ProjectStructure persistence to JSON
3. Auto-loading on ContextAgent initialization
4. Legacy format migration (backward compatibility)
5. VERSION TRACKING
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.agents.context_agent import (
    ContextAgent,
    ContextAgentConfig,
    DetailedFileSummary,
    ProjectStructure,
)


class TestDetailedFileSummary:
    """Tests for DetailedFileSummary dataclass."""
    
    def test_to_dict_serialization(self):
        """Test that DetailedFileSummary serializes correctly."""
        summary = DetailedFileSummary(
            file_path="/workspace/backend/main.py",
            relative_path="backend/main.py",
            language="python",
            lines_of_code=150,
            classes=[
                {"name": "MyClass", "methods": ["__init__", "run"], "docstring": "A class"}
            ],
            functions=[
                {"name": "main", "params": ["args"], "returns": "int", "docstring": "Entry point"}
            ],
            imports={"internal": ["utils"], "external": ["asyncio", "logging"]},
            purpose="Main entry point for the application",
            security_flags=["hardcoded_secret"],
        )
        
        data = summary.to_dict()
        
        assert data["file_path"] == "/workspace/backend/main.py"
        assert data["relative_path"] == "backend/main.py"
        assert data["language"] == "python"
        assert data["lines_of_code"] == 150
        assert len(data["classes"]) == 1
        assert data["classes"][0]["name"] == "MyClass"
        assert len(data["functions"]) == 1
        assert data["purpose"] == "Main entry point for the application"
        assert "hardcoded_secret" in data["security_flags"]
        assert "last_analyzed" in data
    
    def test_from_dict_deserialization(self):
        """Test that DetailedFileSummary deserializes correctly."""
        data = {
            "file_path": "/workspace/api/handler.py",
            "relative_path": "api/handler.py",
            "language": "python",
            "lines_of_code": 200,
            "classes": [{"name": "Handler", "methods": ["get", "post"]}],
            "functions": [{"name": "validate", "params": ["data"]}],
            "imports": {"internal": ["models"], "external": ["fastapi"]},
            "purpose": "API request handlers",
            "security_flags": [],
            "compliance_flags": ["gdpr_data_handling"],
            "last_analyzed": "2025-01-10T12:00:00",
        }
        
        summary = DetailedFileSummary.from_dict(data)
        
        assert summary.file_path == "/workspace/api/handler.py"
        assert summary.relative_path == "api/handler.py"
        assert summary.language == "python"
        assert summary.lines_of_code == 200
        assert summary.classes[0]["name"] == "Handler"
        assert summary.purpose == "API request handlers"
        assert "gdpr_data_handling" in summary.compliance_flags
    
    def test_to_compact_string(self):
        """Test compact string generation for quick lookups."""
        summary = DetailedFileSummary(
            file_path="test.py",
            relative_path="test.py",
            language="python",
            lines_of_code=50,
            classes=[{"name": "TestClass"}],
            functions=[{"name": "test_func"}],
            purpose="Unit tests",
        )
        
        compact = summary.to_compact_string()
        
        assert "python" in compact
        assert "50 lines" in compact
        assert "TestClass" in compact
        assert "test_func" in compact
    
    def test_to_markdown(self):
        """Test markdown generation for Copilot files."""
        summary = DetailedFileSummary(
            file_path="/ws/service.py",
            relative_path="service.py",
            language="python",
            lines_of_code=100,
            classes=[{"name": "Service", "methods": ["start", "stop"], "docstring": "Main service"}],
            functions=[{"name": "create_service", "params": ["config"], "returns": "Service"}],
            purpose="Core service implementation",
            key_responsibilities=["Handle requests", "Manage state"],
            imports={"internal": ["models"], "external": ["asyncio"]},
            security_flags=["eval_usage"],
        )
        
        markdown = summary.to_markdown()
        
        assert "### `service.py`" in markdown
        assert "**Language:** python" in markdown
        assert "**Purpose:** Core service implementation" in markdown
        assert "Handle requests" in markdown
        assert "`Service`" in markdown
        assert "`create_service(config)`" in markdown
        assert "⚠️ Security Notes:" in markdown


class TestProjectStructure:
    """Tests for ProjectStructure with unified files dict."""
    
    def test_to_dict_with_files(self):
        """Test serialization with DetailedFileSummary files."""
        structure = ProjectStructure(
            project_type="backend",
            backend_framework="fastapi",
            files={
                "main.py": DetailedFileSummary(
                    file_path="main.py",
                    relative_path="main.py",
                    language="python",
                    lines_of_code=50,
                ),
                "api/routes.py": DetailedFileSummary(
                    file_path="api/routes.py",
                    relative_path="api/routes.py",
                    language="python",
                    lines_of_code=100,
                ),
            },
        )
        
        data = structure.to_dict()
        
        assert data["project_type"] == "backend"
        assert data["backend_framework"] == "fastapi"
        assert len(data["files"]) == 2
        assert "main.py" in data["files"]
        assert data["files"]["main.py"]["language"] == "python"
    
    def test_from_dict_with_files(self):
        """Test deserialization with DetailedFileSummary files."""
        data = {
            "project_type": "fullstack",
            "backend_framework": "django",
            "frontend_framework": "react",
            "files": {
                "backend/app.py": {
                    "file_path": "backend/app.py",
                    "relative_path": "backend/app.py",
                    "language": "python",
                    "lines_of_code": 200,
                },
                "frontend/App.tsx": {
                    "file_path": "frontend/App.tsx",
                    "relative_path": "frontend/App.tsx",
                    "language": "typescript",
                    "lines_of_code": 150,
                },
            },
        }
        
        structure = ProjectStructure.from_dict(data)
        
        assert structure.project_type == "fullstack"
        assert len(structure.files) == 2
        assert structure.files["backend/app.py"].language == "python"
        assert structure.files["frontend/App.tsx"].language == "typescript"
    
    def test_legacy_format_migration(self):
        """Test that old backend_files/frontend_files format is migrated."""
        legacy_data = {
            "project_type": "backend",
            "backend_files": {
                "main.py": "Python file with FastAPI app (50 lines)",
            },
            "frontend_files": {},
            "shared_files": {
                "config.yaml": "Config file (20 lines)",
            },
        }
        
        structure = ProjectStructure.from_dict(legacy_data)
        
        # Legacy files should be migrated to unified format
        assert "main.py" in structure.files
        assert "config.yaml" in structure.files
        # Old summary becomes purpose
        assert structure.files["main.py"].purpose == "Python file with FastAPI app (50 lines)"
    
    def test_get_file(self):
        """Test getting a specific file by path."""
        structure = ProjectStructure(
            files={
                "api/handler.py": DetailedFileSummary(
                    file_path="api/handler.py",
                    relative_path="api/handler.py",
                    language="python",
                    lines_of_code=100,
                ),
            }
        )
        
        found = structure.get_file("api/handler.py")
        assert found is not None
        assert found.language == "python"
        
        not_found = structure.get_file("nonexistent.py")
        assert not_found is None
    
    def test_search_by_class(self):
        """Test searching files by class name."""
        structure = ProjectStructure(
            files={
                "models.py": DetailedFileSummary(
                    file_path="models.py",
                    relative_path="models.py",
                    language="python",
                    lines_of_code=100,
                    classes=[{"name": "User"}, {"name": "Post"}],
                ),
                "auth.py": DetailedFileSummary(
                    file_path="auth.py",
                    relative_path="auth.py",
                    language="python",
                    lines_of_code=50,
                    classes=[{"name": "AuthService"}],
                ),
            }
        )
        
        results = structure.search_by_class("User")
        assert len(results) == 1
        assert results[0].relative_path == "models.py"
    
    def test_search_by_function(self):
        """Test searching files by function name."""
        structure = ProjectStructure(
            files={
                "utils.py": DetailedFileSummary(
                    file_path="utils.py",
                    relative_path="utils.py",
                    language="python",
                    lines_of_code=50,
                    functions=[{"name": "validate_email"}, {"name": "hash_password"}],
                ),
            }
        )
        
        results = structure.search_by_function("validate_email")
        assert len(results) == 1
        assert results[0].relative_path == "utils.py"
    
    def test_get_files_with_security_issues(self):
        """Test filtering files with security flags."""
        structure = ProjectStructure(
            files={
                "safe.py": DetailedFileSummary(
                    file_path="safe.py",
                    relative_path="safe.py",
                    language="python",
                    lines_of_code=50,
                    security_flags=[],
                ),
                "risky.py": DetailedFileSummary(
                    file_path="risky.py",
                    relative_path="risky.py",
                    language="python",
                    lines_of_code=100,
                    security_flags=["sql_injection", "eval_usage"],
                ),
            }
        )
        
        risky_files = structure.get_files_with_security_issues()
        assert len(risky_files) == 1
        assert risky_files[0].relative_path == "risky.py"


class TestContextAgentPersistence:
    """Tests for ContextAgent persistence functionality."""
    
    def test_save_and_load_project_structure(self):
        """Test saving and loading project structure to/from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create agent and register a file
            agent = ContextAgent(
                config=ContextAgentConfig(persist_memory=True),
                workspace_path=str(workspace),
            )
            
            # Manually create a project structure
            agent._project_structure = ProjectStructure(
                project_type="backend",
                backend_framework="fastapi",
                files={
                    "main.py": DetailedFileSummary(
                        file_path=str(workspace / "main.py"),
                        relative_path="main.py",
                        language="python",
                        lines_of_code=100,
                        purpose="Main application entry point",
                    ),
                },
            )
            
            # Save
            saved = agent._save_project_structure()
            assert saved
            
            # Verify file exists
            persistence_path = workspace / ".omni" / "context" / "project-structure.json"
            assert persistence_path.exists()
            
            # Create new agent and verify it loads
            agent2 = ContextAgent(
                config=ContextAgentConfig(persist_memory=True),
                workspace_path=str(workspace),
            )
            
            assert agent2._project_structure is not None
            assert agent2._project_structure.project_type == "backend"
            assert "main.py" in agent2._project_structure.files
    
    def test_no_load_when_persist_disabled(self):
        """Test that persistence is skipped when disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create persistence file manually
            persistence_dir = workspace / ".omni" / "context"
            persistence_dir.mkdir(parents=True)
            (persistence_dir / "project-structure.json").write_text(
                json.dumps({"project_type": "frontend", "files": {}})
            )
            
            # Create agent with persistence disabled
            agent = ContextAgent(
                config=ContextAgentConfig(persist_memory=False),
                workspace_path=str(workspace),
            )
            
            # Should NOT have loaded
            assert agent._project_structure is None
    
    def test_set_workspace_with_auto_load(self):
        """Test set_workspace triggers auto-loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create persistence file
            persistence_dir = workspace / ".omni" / "context"
            persistence_dir.mkdir(parents=True)
            (persistence_dir / "project-structure.json").write_text(
                json.dumps({
                    "project_type": "library",
                    "files": {
                        "lib.py": {
                            "file_path": "lib.py",
                            "relative_path": "lib.py",
                            "language": "python",
                            "lines_of_code": 50,
                        }
                    }
                })
            )
            
            # Create agent without workspace
            agent = ContextAgent(
                config=ContextAgentConfig(persist_memory=True),
            )
            assert agent._project_structure is None
            
            # Set workspace - should trigger load
            agent.set_workspace(str(workspace))
            
            assert agent._project_structure is not None
            assert agent._project_structure.project_type == "library"
            assert "lib.py" in agent._project_structure.files


class TestContextAgentIntegration:
    """Integration tests for ContextAgent with unified summaries."""
    
    def test_get_file_summary_returns_detailed(self):
        """Test that get_file_summary uses DetailedFileSummary."""
        agent = ContextAgent()
        agent._project_structure = ProjectStructure(
            files={
                "api/routes.py": DetailedFileSummary(
                    file_path="api/routes.py",
                    relative_path="api/routes.py",
                    language="python",
                    lines_of_code=150,
                    classes=[{"name": "Router", "methods": ["get", "post"]}],
                    functions=[{"name": "create_routes", "params": ["app"]}],
                    purpose="API routing definitions",
                ),
            }
        )
        
        # Get file from structure
        file_summary = agent._project_structure.get_file("api/routes.py")
        
        assert file_summary is not None
        assert file_summary.purpose == "API routing definitions"
        assert file_summary.classes[0]["name"] == "Router"
    
    def test_project_context_uses_detailed_files(self):
        """Test that project context summary reflects detailed files."""
        agent = ContextAgent()
        agent._project_structure = ProjectStructure(
            project_type="fullstack",
            backend_framework="fastapi",
            frontend_framework="react",
            files={
                "backend/main.py": DetailedFileSummary(
                    file_path="backend/main.py",
                    relative_path="backend/main.py",
                    language="python",
                    lines_of_code=100,
                ),
                "frontend/App.tsx": DetailedFileSummary(
                    file_path="frontend/App.tsx",
                    relative_path="frontend/App.tsx",
                    language="typescript",
                    lines_of_code=200,
                ),
            },
        )
        
        summary = agent.get_project_summary_for_prompt()
        
        assert "fullstack" in summary.lower()
        assert "fastapi" in summary.lower()
        assert "react" in summary.lower()


class TestVersionTracking:
    """Tests for ProjectStructure version tracking."""
    
    def test_version_increments_on_change(self):
        """Test that version increments when files are added."""
        structure = ProjectStructure()
        
        assert structure.version == 0
        
        structure.increment_version("copilot", "Added main.py")
        assert structure.version == 1
        assert structure.last_modifier == "copilot"
        
        structure.increment_version("user", "Modified config.yaml")
        assert structure.version == 2
        assert structure.last_modifier == "user"
    
    def test_change_history_recorded(self):
        """Test that change history is recorded."""
        structure = ProjectStructure()
        
        structure.increment_version("copilot", "Added auth.py")
        structure.increment_version("scan", "Full workspace scan")
        structure.increment_version("user", "Manual edit")
        
        assert len(structure.change_history) == 3
        assert structure.change_history[0]["modifier"] == "copilot"
        assert structure.change_history[1]["modifier"] == "scan"
        assert structure.change_history[2]["modifier"] == "user"
        assert structure.change_history[0]["description"] == "Added auth.py"
    
    def test_change_history_limited_to_50(self):
        """Test that change history is limited to 50 entries."""
        structure = ProjectStructure()
        
        for i in range(60):
            structure.increment_version("test", f"Change {i}")
        
        assert len(structure.change_history) == 50
        # Should keep the most recent 50
        assert structure.change_history[0]["description"] == "Change 10"
        assert structure.change_history[-1]["description"] == "Change 59"
    
    def test_version_persisted_to_json(self):
        """Test that version is included in JSON serialization."""
        structure = ProjectStructure()
        structure.increment_version("copilot", "Initial")
        structure.increment_version("scan", "Full scan")
        
        data = structure.to_dict()
        
        assert data["version"] == 2
        assert data["last_modifier"] == "scan"
        assert len(data["change_history"]) == 2
    
    def test_version_loaded_from_json(self):
        """Test that version is restored from JSON."""
        data = {
            "project_type": "backend",
            "version": 42,
            "last_modifier": "copilot",
            "change_history": [
                {"version": 41, "modifier": "user", "description": "Edit"},
                {"version": 42, "modifier": "copilot", "description": "Generate"},
            ],
            "files": {},
        }
        
        structure = ProjectStructure.from_dict(data)
        
        assert structure.version == 42
        assert structure.last_modifier == "copilot"
        assert len(structure.change_history) == 2
    
    def test_on_change_callback(self):
        """Test that change callbacks are called."""
        structure = ProjectStructure()
        
        callback_calls = []
        def on_change(struct, version, modifier):
            callback_calls.append((version, modifier))
        
        structure.on_change(on_change)
        
        structure.increment_version("copilot", "Test")
        structure.increment_version("user", "Another")
        
        assert len(callback_calls) == 2
        assert callback_calls[0] == (1, "copilot")
        assert callback_calls[1] == (2, "user")
    
    def test_context_agent_tracks_version_on_register(self):
        """Test that ContextAgent increments version when registering files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            agent = ContextAgent(
                config=ContextAgentConfig(persist_memory=False),
                workspace_path=str(workspace),
            )
            
            # Register first file
            agent.register_generated_file(
                str(workspace / "main.py"),
                "print('hello')",
                modifier="copilot",
            )
            
            assert agent._project_structure.version == 1
            assert agent._project_structure.last_modifier == "copilot"
            
            # Register second file
            agent.register_generated_file(
                str(workspace / "utils.py"),
                "def helper(): pass",
                modifier="user",
            )
            
            assert agent._project_structure.version == 2
            assert agent._project_structure.last_modifier == "user"
    
    def test_version_persisted_and_loaded(self):
        """Test full persistence cycle with versioning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create agent and register files
            agent1 = ContextAgent(
                config=ContextAgentConfig(persist_memory=True),
                workspace_path=str(workspace),
            )
            
            agent1._project_structure = ProjectStructure()
            agent1._project_structure.files["test.py"] = DetailedFileSummary(
                file_path="test.py",
                relative_path="test.py",
                language="python",
                lines_of_code=10,
            )
            agent1._project_structure.increment_version("copilot", "Created test.py")
            agent1._project_structure.increment_version("scan", "Analyzed")
            
            # Save
            agent1._save_project_structure()
            
            # Load in new agent
            agent2 = ContextAgent(
                config=ContextAgentConfig(persist_memory=True),
                workspace_path=str(workspace),
            )
            
            assert agent2._project_structure.version == 2
            assert agent2._project_structure.last_modifier == "scan"
            assert len(agent2._project_structure.change_history) == 2

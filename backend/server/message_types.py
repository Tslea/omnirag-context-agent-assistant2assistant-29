"""
Message Types

Defines the message protocol between VS Code and the backend.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class MessageType(str, Enum):
    """Types of messages exchanged between frontend and backend."""
    
    # Client -> Server
    CHAT_MESSAGE = "chat_message"
    GET_AGENTS = "get_agents"
    SELECT_AGENT = "select_agent"
    GET_HISTORY = "get_history"
    CANCEL = "cancel"
    
    # NEW: Automatic code analysis
    ANALYZE_CODE = "analyze_code"  # Analyze a single file
    SCAN_WORKSPACE = "scan_workspace"  # Scan entire workspace
    QUERY_CONTEXT = "query_context"  # Query the project context
    
    # Server -> Client
    CHAT_RESPONSE = "chat_response"
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_END = "stream_end"
    AGENT_LIST = "agent_list"
    AGENT_STATUS = "agent_status"
    ERROR = "error"
    
    # NEW: Analysis results
    ANALYSIS_RESULT = "analysis_result"  # Results from code analysis
    SECURITY_FINDINGS = "security_findings"  # Security issues found
    QUERY_RESULT = "query_result"  # Results from context query
    
    # Bidirectional
    PING = "ping"
    PONG = "pong"


@dataclass
class Message:
    """
    A message in the communication protocol.
    
    Attributes:
        type: Message type
        data: Message payload
        id: Optional message ID for request-response correlation
        timestamp: When the message was created
    """
    type: str
    data: Any = None
    id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "data": self.data,
            "id": self.id,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            type=data.get("type", "unknown"),
            data=data.get("data"),
            id=data.get("id"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
        )
    
    @classmethod
    def chat_response(cls, content: str, agent_id: str, message_id: Optional[str] = None) -> "Message":
        """Create a chat response message."""
        return cls(
            type=MessageType.CHAT_RESPONSE.value,
            data={
                "content": content,
                "agent_id": agent_id,
            },
            id=message_id,
        )
    
    @classmethod
    def stream_start(cls, message_id: Optional[str] = None) -> "Message":
        """Create a stream start message."""
        return cls(
            type=MessageType.STREAM_START.value,
            data={},
            id=message_id,
        )
    
    @classmethod
    def stream_chunk(cls, content: str, message_id: Optional[str] = None) -> "Message":
        """Create a stream chunk message."""
        return cls(
            type=MessageType.STREAM_CHUNK.value,
            data={"content": content},
            id=message_id,
        )
    
    @classmethod
    def stream_end(cls, message_id: Optional[str] = None) -> "Message":
        """Create a stream end message."""
        return cls(
            type=MessageType.STREAM_END.value,
            data={},
            id=message_id,
        )
    
    @classmethod
    def error(cls, message: str, code: Optional[str] = None, request_id: Optional[str] = None) -> "Message":
        """Create an error message."""
        return cls(
            type=MessageType.ERROR.value,
            data={
                "message": message,
                "code": code,
            },
            id=request_id,
        )
    
    @classmethod
    def agent_list(cls, agents: list[dict[str, Any]]) -> "Message":
        """Create an agent list message."""
        return cls(
            type=MessageType.AGENT_LIST.value,
            data={"agents": agents},
        )
    
    @classmethod
    def agent_status(cls, agent_id: str, status: str) -> "Message":
        """Create an agent status message."""
        return cls(
            type=MessageType.AGENT_STATUS.value,
            data={
                "agent_id": agent_id,
                "status": status,
            },
        )
    
    @classmethod
    def analysis_result(cls, file_path: str, findings: list, agent_id: str = "security") -> "Message":
        """Create an analysis result message."""
        return cls(
            type=MessageType.ANALYSIS_RESULT.value,
            data={
                "file_path": file_path,
                "findings": findings,
                "agent_id": agent_id,
                "findings_count": len(findings),
            },
        )
    
    @classmethod
    def security_findings(cls, findings: list, summary: dict) -> "Message":
        """Create a security findings message."""
        return cls(
            type=MessageType.SECURITY_FINDINGS.value,
            data={
                "findings": findings,
                "summary": summary,
            },
        )

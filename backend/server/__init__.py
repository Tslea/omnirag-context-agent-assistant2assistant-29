"""
Backend Server Package

WebSocket server for VS Code extension communication.
"""

from backend.server.main import run_server
from backend.server.websocket_handler import WebSocketHandler
from backend.server.message_types import MessageType, Message

__all__ = [
    "run_server",
    "WebSocketHandler",
    "MessageType",
    "Message",
]

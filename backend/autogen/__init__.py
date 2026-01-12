"""
AutoGen Multi-Agent Runtime Module

Provides optional AutoGen integration for multi-agent conversations.
This module is completely optional - system works without AutoGen.

Key features:
- Agents can run standalone OR in group chats
- AutoGen is behind an adapter (existing agents unchanged)
- Disabled by default

Usage:
    from backend.autogen import AutoGenRuntime
    
    runtime = AutoGenRuntime(settings)
    if runtime.is_available():
        result = await runtime.run_group_chat([agent1, agent2], task)
"""

from backend.autogen.runtime import AutoGenRuntime, AutoGenConfig

__all__ = ["AutoGenRuntime", "AutoGenConfig"]

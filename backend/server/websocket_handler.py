"""
WebSocket Handler

Handles WebSocket connections and message routing.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional
from uuid import uuid4

import websockets
from websockets.server import WebSocketServerProtocol

from backend.server.message_types import Message, MessageType
from backend.core.interfaces.agent import AgentMessage, AgentContext, MessageType as AgentMsgType
from backend.core.exceptions import (
    AgentError,
    AgentTimeoutError,
    WorkflowError,
    LLMError,
    VectorDBError,
    RAGError,
    ErrorContext,
    is_recoverable,
    wrap_exception,
)
from backend.agents.orchestrator import AgentOrchestrator
from backend.agents.workflow import WorkflowOrchestrator, WorkflowResult
from backend.agents.loader import AgentLoader, AgentRegistry
from backend.adapters.llm.factory import LLMFactory
from backend.adapters.vectordb.factory import VectorDBFactory
from backend.rag.service import RAGService, RAGConfig
from backend.config.settings import Settings

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """
    Handles WebSocket connections from VS Code extension.
    
    Routes messages to appropriate handlers and manages
    the agent orchestration system.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.connections: set[WebSocketServerProtocol] = set()
        
        # Initialize agent system
        self.registry = AgentRegistry()
        self.loader = AgentLoader(self.registry)
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.workflow: Optional[WorkflowOrchestrator] = None
        
        # Current session state
        self.sessions: dict[str, dict[str, Any]] = {}
        self.current_agent_id: str = "assistant"
        
        # Message handlers
        self.handlers: dict[str, Callable] = {
            MessageType.CHAT_MESSAGE.value: self._handle_chat_message,
            MessageType.GET_AGENTS.value: self._handle_get_agents,
            MessageType.SELECT_AGENT.value: self._handle_select_agent,
            MessageType.PING.value: self._handle_ping,
            MessageType.CANCEL.value: self._handle_cancel,
            MessageType.ANALYZE_CODE.value: self._handle_analyze_code,
            MessageType.SCAN_WORKSPACE.value: self._handle_scan_workspace,
            MessageType.QUERY_CONTEXT.value: self._handle_query_context,
        }
        
        # Initialize
        self._initialize_agents()
    
    def _initialize_agents(self) -> None:
        """Initialize the agent system."""
        # Load built-in agents
        loaded_count = self.loader.load_builtin_agents()
        logger.info(f"Loaded {loaded_count} built-in agents")
        
        # Load agents from plugin directories
        for plugin_dir in self.settings.agents.plugin_dirs:
            self.loader.load_from_directory(plugin_dir)
        
        # Create LLM provider
        try:
            llm_config = self.settings.get_llm_config()
            llm_provider = LLMFactory.from_config(llm_config)

            # Create VectorDB provider (optional, needed for RAG)
            vectordb_provider = None
            try:
                vectordb_config = self.settings.get_vectordb_config()
                vectordb_provider = VectorDBFactory.from_config(vectordb_config)
            except Exception as e:
                logger.warning(f"VectorDB initialization failed (RAG will be limited): {e}")
                vectordb_provider = None
            
            # Create RAG service (optional)
            rag_service = RAGService(
                RAGConfig(
                    enabled=self.settings.features.enable_rag and self.settings.rag.enabled,
                    chunk_size=self.settings.rag.chunk_size,
                    chunk_overlap=self.settings.rag.chunk_overlap,
                    top_k=self.settings.rag.top_k,
                    score_threshold=self.settings.rag.score_threshold,
                ),
                vectordb_provider=vectordb_provider,
                llm_provider=llm_provider,
            )
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(rag_service.initialize())
                loop.close()
            except Exception as e:
                logger.warning(f"RAG service initialization failed: {e}")
            
            # Create orchestrator
            self.orchestrator = AgentOrchestrator(self.registry, llm_provider)
            
            # Add default agents
            logger.info(f"Default agents to add: {self.settings.agents.default_agents}")
            logger.info(f"Available agents in registry: {list(self.registry._agents.keys())}")
            
            for agent_id in self.settings.agents.default_agents:
                if self.registry.has(agent_id):
                    success = self.orchestrator.add_agent(agent_id)
                    logger.info(f"Added agent '{agent_id}': {success}")
                else:
                    logger.warning(f"Agent '{agent_id}' not found in registry")
            
            logger.info(f"Orchestrator agents: {list(self.orchestrator._agents.keys())}")

            # Wire RAG service into RAG agent if available
            rag_agent = self.orchestrator._agents.get("rag_agent")
            if rag_agent:
                rag_agent.config.enabled = bool(self.settings.features.enable_rag and self.settings.rag.enabled)
                if hasattr(rag_agent, "set_rag_service"):
                    rag_agent.set_rag_service(rag_service)
                logger.info(f"RAG agent enabled: {rag_agent.config.enabled} | service available: {rag_service.is_available()}")
            
            # Create workflow orchestrator for full pipeline
            self.workflow = WorkflowOrchestrator(self.orchestrator)
                    
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
    
    async def handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        """Handle a new WebSocket connection."""
        self.connections.add(websocket)
        session_id = str(uuid4())
        self.sessions[session_id] = {
            "websocket": websocket,
            "agent_id": self.current_agent_id,
            "context": AgentContext(session_id=session_id),
        }
        
        logger.info(f"New connection: {session_id}")
        
        try:
            async for raw_message in websocket:
                try:
                    data = json.loads(raw_message)
                    message = Message.from_dict(data)
                    await self._route_message(websocket, session_id, message)
                except json.JSONDecodeError:
                    await self._send_error(websocket, "Invalid JSON", None)
                except Exception as e:
                    logger.exception(f"Error handling message: {e}")
                    await self._send_error(websocket, str(e), None)
                    
        except websockets.ConnectionClosed:
            logger.info(f"Connection closed: {session_id}")
        finally:
            self.connections.discard(websocket)
            self.sessions.pop(session_id, None)
    
    async def _route_message(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: Message,
    ) -> None:
        """Route a message to the appropriate handler."""
        handler = self.handlers.get(message.type)
        
        if handler:
            await handler(websocket, session_id, message)
        else:
            await self._send_error(
                websocket,
                f"Unknown message type: {message.type}",
                message.id,
            )
    
    async def _handle_chat_message(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: Message,
    ) -> None:
        """Handle a chat message from the client."""
        # Handle case where data is a string instead of dict
        if isinstance(message.data, str):
            content = message.data
            agent_id = self.current_agent_id
        else:
            content = message.data.get("content", "") if message.data else ""
            agent_id = message.data.get("agent_id") if message.data else None
            agent_id = agent_id or self.current_agent_id
        
        if not self.orchestrator:
            await self._send_error(websocket, "Agent system not initialized", message.id)
            return
        
        session = self.sessions.get(session_id, {})
        context = session.get("context", AgentContext(session_id=session_id))
        
        # Create agent message
        agent_message = AgentMessage(
            content=content,
            type=AgentMsgType.TEXT,
            sender="user",
        )
        
        # Check if streaming is enabled
        if self.settings.features.enable_streaming:
            await self._handle_streaming_response(
                websocket, agent_id, agent_message, context, message.id
            )
        else:
            await self._handle_regular_response(
                websocket, agent_id, agent_message, context, message.id
            )
    
    async def _handle_regular_response(
        self,
        websocket: WebSocketServerProtocol,
        agent_id: str,
        agent_message: AgentMessage,
        context: AgentContext,
        request_id: Optional[str],
    ) -> None:
        """Handle non-streaming response."""
        try:
            # Notify agent status
            await self._send(websocket, Message.agent_status(agent_id, "thinking"))
            
            response = await self.orchestrator.send_to_agent(
                agent_id, agent_message, context
            )
            
            # Send response
            await self._send(
                websocket,
                Message.chat_response(str(response.content), agent_id, request_id)
            )
            
            # Update status
            await self._send(websocket, Message.agent_status(agent_id, "idle"))
            
        except asyncio.TimeoutError:
            err = AgentTimeoutError(f"Agent {agent_id} response timed out")
            logger.warning(str(err))
            await self._send_error(websocket, str(err), request_id)
            await self._send(websocket, Message.agent_status(agent_id, "error"))
        except AgentError as e:
            logger.error(f"Agent error: {e}")
            await self._send_error(websocket, str(e), request_id)
            await self._send(websocket, Message.agent_status(agent_id, "error"))
        except Exception as e:
            wrapped = wrap_exception(e, "Failed to process message", AgentError)
            logger.exception(str(wrapped))
            await self._send_error(websocket, str(e), request_id)
            await self._send(websocket, Message.agent_status(agent_id, "error"))
    
    async def _handle_streaming_response(
        self,
        websocket: WebSocketServerProtocol,
        agent_id: str,
        agent_message: AgentMessage,
        context: AgentContext,
        request_id: Optional[str],
    ) -> None:
        """Handle streaming response."""
        try:
            # Notify stream start
            await self._send(websocket, Message.stream_start(request_id))
            await self._send(websocket, Message.agent_status(agent_id, "thinking"))
            
            # For now, simulate streaming by sending the full response in chunks
            # In a real implementation, you would use the LLM's streaming API
            response = await self.orchestrator.send_to_agent(
                agent_id, agent_message, context
            )
            
            content = str(response.content)
            chunk_size = 20
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                await self._send(websocket, Message.stream_chunk(chunk, request_id))
                await asyncio.sleep(0.02)  # Small delay for visual effect
            
            await self._send(websocket, Message.stream_end(request_id))
            await self._send(websocket, Message.agent_status(agent_id, "idle"))
            
        except asyncio.TimeoutError:
            err = AgentTimeoutError(f"Agent {agent_id} streaming timed out")
            logger.warning(str(err))
            await self._send_error(websocket, str(err), request_id)
            await self._send(websocket, Message.agent_status(agent_id, "error"))
        except AgentError as e:
            logger.error(f"Agent streaming error: {e}")
            await self._send_error(websocket, str(e), request_id)
            await self._send(websocket, Message.agent_status(agent_id, "error"))
        except Exception as e:
            wrapped = wrap_exception(e, "Streaming failed", AgentError)
            logger.exception(str(wrapped))
            await self._send_error(websocket, str(e), request_id)
            await self._send(websocket, Message.agent_status(agent_id, "error"))
    
    async def _handle_get_agents(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: Message,
    ) -> None:
        """Handle request for agent list."""
        agents = []
        
        for metadata in self.registry.list_metadata():
            agents.append({
                "id": metadata.id,
                "name": metadata.name,
                "description": metadata.description,
                "capabilities": [cap.name for cap in metadata.capabilities],
                "status": "idle",
            })
        
        await self._send(websocket, Message.agent_list(agents))
    
    async def _handle_select_agent(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: Message,
    ) -> None:
        """Handle agent selection."""
        agent_id = message.data.get("agent_id")
        
        if not agent_id:
            await self._send_error(websocket, "agent_id required", message.id)
            return
        
        if not self.registry.has(agent_id):
            await self._send_error(websocket, f"Unknown agent: {agent_id}", message.id)
            return
        
        self.current_agent_id = agent_id
        
        if session_id in self.sessions:
            self.sessions[session_id]["agent_id"] = agent_id
        
        await self._send(websocket, Message.agent_status(agent_id, "idle"))
    
    async def _handle_ping(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: Message,
    ) -> None:
        """Handle ping message."""
        await self._send(
            websocket,
            Message(type=MessageType.PONG.value, id=message.id)
        )
    
    async def _handle_cancel(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: Message,
    ) -> None:
        """Handle cancellation request."""
        # TODO: Implement actual cancellation of ongoing operations
        pass
    
    async def _handle_analyze_code(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: Message,
    ) -> None:
        """
        Handle code analysis request.
        
        Automatically triggered when a file is saved or modified.
        Uses the full workflow pipeline:
        1. Context Agent updates project context
        2. RAG Agent indexes the file
        3. Security Agent analyzes vulnerabilities
        4. Compliance Agent checks compliance
        """
        data = message.data or {}
        file_path = data.get("file_path", "")
        content = data.get("content", "")
        language = data.get("language", "")
        
        if not content:
            return  # Skip empty files
        
        logger.info(f"Analyzing code: {file_path} ({language})")
        
        if not self.workflow:
            await self._send_error(websocket, "Workflow not initialized", message.id)
            return
        
        try:
            # Notify all agents are starting
            await self._send(websocket, Message.agent_status("context_agent", "analyzing"))
            
            # Run the full workflow pipeline
            result = await self.workflow.analyze_file(file_path, content, language)
            
            # Update agent statuses
            await self._send(websocket, Message.agent_status("context_agent", "idle"))
            await self._send(websocket, Message.agent_status("rag_agent", "idle"))
            await self._send(websocket, Message.agent_status("security", "idle"))
            await self._send(websocket, Message.agent_status("compliance", "idle"))
            
            # Build response message
            response_parts = []
            
            # Context summary
            if result.context_summary:
                response_parts.append(f"📁 **Project:** {result.context_summary}")
            
            # Security findings
            if result.security_findings:
                response_parts.append(f"\n🔒 **Security Issues ({len(result.security_findings)}):**")
                for finding in result.security_findings[:5]:
                    if isinstance(finding, dict):
                        severity = finding.get("severity", "unknown")
                        title = finding.get("title", finding.get("message", "Issue"))
                    else:
                        severity = "unknown"
                        title = str(finding)
                    response_parts.append(f"  - [{severity.upper()}] {title}")
                if len(result.security_findings) > 5:
                    response_parts.append(f"  ... and {len(result.security_findings) - 5} more")
            else:
                response_parts.append("\n🔒 **Security:** ✅ No issues found")
            
            # Compliance findings
            if result.compliance_findings:
                response_parts.append(f"\n📋 **Compliance Issues ({len(result.compliance_findings)}):**")
                for finding in result.compliance_findings[:5]:
                    if isinstance(finding, dict):
                        severity = finding.get("severity", "unknown")
                        title = finding.get("rule_name", finding.get("message", "Issue"))
                    else:
                        severity = "unknown"
                        title = str(finding)
                    response_parts.append(f"  - [{severity.upper()}] {title}")
            else:
                response_parts.append("\n📋 **Compliance:** ✅ No issues found")
            
            response_parts.append(f"\n⏱️ Analysis completed in {result.execution_time_ms}ms")
            
            # Send analysis result
            await self._send(
                websocket,
                Message.analysis_result(
                    file_path,
                    result.security_findings + result.compliance_findings,
                    "workflow"
                )
            )
            
            # Send as chat response
            await self._send(
                websocket,
                Message.chat_response(
                    f"**Analysis for `{file_path}`:**\n\n" + "\n".join(response_parts),
                    "workflow",
                    message.id
                )
            )
            
        except asyncio.TimeoutError:
            err = WorkflowError(f"Code analysis timed out for {file_path}")
            logger.warning(str(err))
            await self._send(websocket, Message.agent_status("security", "error"))
            await self._send_error(websocket, str(err), message.id)
        except (AgentError, WorkflowError) as e:
            logger.error(f"Code analysis failed: {e}")
            await self._send(websocket, Message.agent_status("security", "error"))
            await self._send_error(websocket, f"Analysis failed: {str(e)}", message.id)
        except Exception as e:
            wrapped = wrap_exception(e, f"Code analysis failed for {file_path}", WorkflowError)
            logger.exception(str(wrapped))
            await self._send(websocket, Message.agent_status("security", "error"))
            await self._send_error(websocket, f"Analysis failed: {str(e)}", message.id)
    
    async def _handle_scan_workspace(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: Message,
    ) -> None:
        """
        Handle workspace scan request.
        
        Triggered when a workspace folder is opened.
        Uses the full workflow pipeline:
        1. Context Agent analyzes project structure
        2. RAG Agent indexes all files
        3. Security Agent scans for vulnerabilities
        4. Compliance Agent checks compliance
        """
        data = message.data or {}
        folder_path = data.get("folder_path", "")
        folder_name = data.get("folder_name", "workspace")
        files = data.get("files", [])
        
        logger.info(f"Scanning workspace: {folder_name} ({len(files)} files)")
        
        if not self.workflow:
            await self._send_error(websocket, "Workflow not initialized", message.id)
            return
        
        try:
            # Notify scan started
            await self._send(
                websocket,
                Message.chat_response(
                    f"🔍 **Starting workspace scan for `{folder_name}`...**\n\n"
                    f"Found {len(files)} code files to analyze.\n\n"
                    "Running analysis pipeline:\n"
                    "1️⃣ Context Agent → Analyzing project structure...\n"
                    "2️⃣ RAG Agent → Indexing files for search...\n"
                    "3️⃣ Security Agent → Scanning for vulnerabilities...\n"
                    "4️⃣ Compliance Agent → Checking compliance...",
                    "workflow",
                    message.id
                )
            )
            
            # Update agent statuses
            await self._send(websocket, Message.agent_status("context_agent", "analyzing"))
            await self._send(websocket, Message.agent_status("rag_agent", "indexing"))
            
            # Run the full workflow pipeline
            result = await self.workflow.analyze_workspace(folder_path, files)
            
            # Reset agent statuses
            await self._send(websocket, Message.agent_status("context_agent", "idle"))
            await self._send(websocket, Message.agent_status("rag_agent", "idle"))
            await self._send(websocket, Message.agent_status("security", "idle"))
            await self._send(websocket, Message.agent_status("compliance", "idle"))
            
            # Build summary response
            response_parts = [f"✅ **Workspace scan complete for `{folder_name}`**\n"]
            
            # Context summary
            if result.context_summary:
                response_parts.append(f"📁 **Project:** {result.context_summary}")
            
            # RAG index
            if result.rag_indexed_count > 0:
                response_parts.append(f"📚 **Indexed:** {result.rag_indexed_count} files")
            
            # Security summary
            if result.security_findings:
                critical = sum(1 for f in result.security_findings if isinstance(f, dict) and f.get("severity") == "critical")
                high = sum(1 for f in result.security_findings if isinstance(f, dict) and f.get("severity") == "high")
                response_parts.append(f"\n🔒 **Security Issues:** {len(result.security_findings)} total")
                if critical > 0:
                    response_parts.append(f"   🔴 {critical} critical")
                if high > 0:
                    response_parts.append(f"   🟠 {high} high")
                    
                # Show top issues
                response_parts.append("\n   **Top Issues:**")
                for finding in result.security_findings[:3]:
                    if isinstance(finding, dict):
                        severity = finding.get("severity", "?")
                        title = finding.get("title", finding.get("message", "Issue"))
                    else:
                        severity = "?"
                        title = str(finding)
                    response_parts.append(f"   - [{severity}] {title}")
            else:
                response_parts.append("\n🔒 **Security:** ✅ No issues found")
            
            # Compliance summary
            if result.compliance_findings:
                response_parts.append(f"\n📋 **Compliance Issues:** {len(result.compliance_findings)} total")
                for finding in result.compliance_findings[:3]:
                    if isinstance(finding, dict):
                        response_parts.append(f"   - {finding.get('rule_name', 'Issue')}")
                    else:
                        response_parts.append(f"   - {str(finding)}")
            else:
                response_parts.append("\n📋 **Compliance:** ✅ No issues found")
            
            response_parts.append(f"\n⏱️ Scan completed in {result.execution_time_ms}ms")
            
            # Copilot files info
            response_parts.append("\n\n📝 **Generated Copilot Context Files:**")
            response_parts.append("   - `.github/copilot-instructions.md` (auto-read by Copilot)")
            response_parts.append("   - `.omni/context/project-overview.md`")
            response_parts.append("   - `.omni/context/file-summaries.md`")
            response_parts.append("   - `.omni/insights/security.md`")
            response_parts.append("   - `.omni/insights/compliance.md`")
            
            response_parts.append("\n\n💡 Files will be re-analyzed automatically when modified.")
            
            # Send security findings
            await self._send(
                websocket,
                Message.security_findings(
                    result.security_findings,
                    {"total": result.total_issues}
                )
            )
            
            # Send summary
            await self._send(
                websocket,
                Message.chat_response(
                    "\n".join(response_parts),
                    "workflow",
                    message.id
                )
            )
            
        except asyncio.TimeoutError:
            err = WorkflowError(f"Workspace scan timed out for {folder_name}")
            logger.warning(str(err))
            await self._send(websocket, Message.agent_status("security", "error"))
            await self._send_error(websocket, str(err), message.id)
        except (AgentError, WorkflowError) as e:
            logger.error(f"Workspace scan failed: {e}")
            await self._send(websocket, Message.agent_status("security", "error"))
            await self._send_error(websocket, f"Scan failed: {str(e)}", message.id)
        except Exception as e:
            wrapped = wrap_exception(e, f"Workspace scan failed for {folder_name}", WorkflowError)
            logger.exception(str(wrapped))
            await self._send(websocket, Message.agent_status("security", "error"))
            await self._send_error(websocket, f"Scan failed: {str(e)}", message.id)
    
    async def _handle_query_context(
        self,
        websocket: WebSocketServerProtocol,
        message: Message,
    ) -> None:
        """
        Handle context query requests.
        
        Message payload:
        - query: str - Query string (e.g., "file:auth.py", "class:UserService")
        
        Supported queries:
        - "file:name" - Find file by name
        - "class:ClassName" - Find files with class
        - "func:funcName" - Find files with function
        - "lang:python" - Files by language
        - "sec:" - Files with security issues
        - "comp:" - Files with compliance issues
        - "pattern:xyz" - Files matching pattern
        """
        query = message.payload.get("query", "")
        
        if not query:
            await self._send_error(websocket, "Missing 'query' in payload", message.id)
            return
        
        if not self.context_agent:
            await self._send_error(websocket, "Context agent not initialized", message.id)
            return
        
        try:
            # Get project structure
            project = self.context_agent._project_structure
            if not project:
                await self._send_error(websocket, "No project structure loaded. Run scan first.", message.id)
                return
            
            # Execute query
            result = project.query(query)
            
            # Send result
            await self._send(
                websocket,
                Message(
                    type=MessageType.QUERY_RESULT.value,
                    payload={
                        "query": query,
                        "results": result["results"],
                        "count": result["count"],
                    },
                    request_id=message.id,
                )
            )
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            await self._send_error(websocket, f"Query failed: {str(e)}", message.id)
    
    async def _send(self, websocket: WebSocketServerProtocol, message: Message) -> None:
        """Send a message to a client."""
        try:
            await websocket.send(json.dumps(message.to_dict()))
        except websockets.ConnectionClosed:
            pass
    
    async def _send_error(
        self,
        websocket: WebSocketServerProtocol,
        error_message: str,
        request_id: Optional[str],
    ) -> None:
        """Send an error message."""
        await self._send(websocket, Message.error(error_message, request_id=request_id))
    
    async def broadcast(self, message: Message) -> None:
        """Broadcast a message to all connected clients."""
        if self.connections:
            await asyncio.gather(
                *[self._send(ws, message) for ws in self.connections],
                return_exceptions=True,
            )

"""
Main Server Entry Point

Starts the WebSocket server and HTTP health endpoint.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import websockets

from backend.config.settings import get_settings, Settings
from backend.server.websocket_handler import WebSocketHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(settings: Settings) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="OMNI Backend",
        description="Backend server for OMNI AI Assistant",
        version="0.1.0",
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}
    
    @app.get("/config")
    async def get_config():
        """Get current configuration (non-sensitive)."""
        return {
            "llm_provider": settings.llm.provider,
            "vectordb_provider": settings.vectordb.provider,
            "features": {
                "streaming": settings.features.enable_streaming,
                "multi_agent": settings.features.enable_multi_agent,
                "rag": settings.features.enable_rag,
            },
        }
    
    return app


async def run_websocket_server(
    settings: Settings,
    handler: WebSocketHandler,
) -> None:
    """Run the WebSocket server."""
    host = settings.server.host
    port = settings.server.port
    
    logger.info(f"Starting WebSocket server on ws://{host}:{port}/ws")
    
    async with websockets.serve(
        handler.handle_connection,
        host,
        port,
        ping_interval=30,
        ping_timeout=10,
    ):
        await asyncio.Future()  # Run forever


def run_server(
    config_path: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    """
    Run the OMNI backend server.
    
    Args:
        config_path: Path to configuration file
        host: Override server host
        port: Override server port
    """
    # Load settings
    settings = get_settings(config_path)
    
    # Override with command line arguments
    if host:
        settings.server.host = host
    if port:
        settings.server.port = port
    
    # Create WebSocket handler
    ws_handler = WebSocketHandler(settings)
    
    # Create FastAPI app for health checks
    app = create_app(settings)
    
    # Setup shutdown handlers
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        logger.info("Shutdown signal received")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    async def main():
        """Main async entry point."""
        # Start HTTP server in background
        config = uvicorn.Config(
            app,
            host=settings.server.host,
            port=settings.server.port + 1,  # Health check on port + 1
            log_level="warning",
        )
        http_server = uvicorn.Server(config)
        
        # Run both servers
        await asyncio.gather(
            http_server.serve(),
            run_websocket_server(settings, ws_handler),
        )
    
    # Run the server
    logger.info(f"Starting OMNI backend server")
    logger.info(f"WebSocket: ws://{settings.server.host}:{settings.server.port}")
    logger.info(f"HTTP: http://{settings.server.host}:{settings.server.port + 1}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OMNI Backend Server")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    parser.add_argument("--host", "-H", help="Server host")
    parser.add_argument("--port", "-p", type=int, help="Server port")
    
    args = parser.parse_args()
    
    run_server(
        config_path=args.config,
        host=args.host,
        port=args.port,
    )

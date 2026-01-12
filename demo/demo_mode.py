"""
OMNI Demo Mode

End-to-end local demo that runs without external dependencies.
Uses FakeLLM + in-memory storage.

Run with: python -m demo.demo_mode

Requirements:
- No API keys needed
- No external services
- Works on clean machine with just Python installed
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.tests.conftest import FakeLLMProvider, FakeVectorStore
from backend.core.interfaces.llm import LLMConfig
from backend.core.interfaces.vectordb import CollectionConfig as VectorDBConfig
from backend.core.interfaces.agent import AgentContext, AgentMessage, MessageType
from backend.agents.base_agents import AssistantAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DemoConfig:
    """Demo configuration."""
    llm_model: str = "demo-model"
    demo_response: str = "This is a demo response from FakeLLM."
    

async def run_demo():
    """Run the demo."""
    print("=" * 60)
    print("🚀 OMNI Demo Mode")
    print("=" * 60)
    print()
    print("This demo runs locally without any external services.")
    print("It uses FakeLLM and in-memory storage.")
    print()
    
    # Initialize fake providers
    print("📦 Initializing fake providers...")
    
    llm_config = LLMConfig(model=DemoConfig.llm_model)
    llm = FakeLLMProvider(llm_config)
    llm.set_response(DemoConfig.demo_response)
    await llm.initialize()
    print("  ✅ FakeLLM initialized")
    
    vectordb_config = VectorDBConfig(name="demo", dimension=384)
    vectordb = FakeVectorStore(vectordb_config)
    await vectordb.initialize()
    print("  ✅ FakeVectorStore initialized")
    
    # Create assistant agent
    print()
    print("🤖 Creating assistant agent...")
    agent = AssistantAgent(llm_provider=llm)
    print(f"  ✅ Agent '{agent.metadata.name}' ready")
    print(f"     Capabilities: {[c.name for c in agent.metadata.capabilities]}")
    
    # Create context
    context = AgentContext(session_id="demo-session")
    
    # Demo conversation
    print()
    print("=" * 60)
    print("💬 Demo Conversation")
    print("=" * 60)
    print()
    
    messages = [
        "Hello! What can you help me with?",
        "Can you explain what OMNI is?",
        "What agents are available?",
    ]
    
    for user_message in messages:
        print(f"👤 User: {user_message}")
        
        agent_message = AgentMessage(
            content=user_message,
            type=MessageType.TEXT,
            sender="user",
        )
        
        response = await agent.process(agent_message, context)
        print(f"🤖 Agent: {response.content}")
        print()
    
    # Demo streaming
    print("=" * 60)
    print("📡 Demo Streaming")
    print("=" * 60)
    print()
    
    llm.set_stream_chunks(["Hello", " from", " the", " streaming", " demo", "!"])
    
    print("👤 User: Show me streaming")
    print("🤖 Agent: ", end="", flush=True)
    
    async for chunk in llm.stream([]):
        print(chunk, end="", flush=True)
        await asyncio.sleep(0.1)  # Simulate delay
    
    print()
    print()
    
    # Demo vector store
    print("=" * 60)
    print("📚 Demo Vector Store")
    print("=" * 60)
    print()
    
    from backend.core.interfaces.vectordb import Document
    
    # Add documents
    docs = [
        Document(id="1", content="OMNI is a modular AI system", metadata={"source": "readme"}),
        Document(id="2", content="Security agent analyzes code for vulnerabilities", metadata={"source": "docs"}),
        Document(id="3", content="Compliance agent checks regulatory requirements", metadata={"source": "docs"}),
    ]
    
    print("📝 Adding documents to vector store...")
    await vectordb.upsert("demo", docs)
    print(f"  ✅ Added {len(docs)} documents")
    
    # Search
    print()
    print("🔍 Searching for 'security'...")
    results = await vectordb.search("demo", query_text="security")
    print(f"  Found {len(results)} results:")
    for r in results:
        print(f"    - {r.document.content[:50]}...")
    
    # Cleanup
    print()
    print("=" * 60)
    print("🧹 Cleanup")
    print("=" * 60)
    print()
    
    await llm.shutdown()
    await vectordb.shutdown()
    print("  ✅ All providers shut down")
    
    print()
    print("=" * 60)
    print("✨ Demo Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Configure real LLM providers in config/default.yaml")
    print("  2. Start the backend: python -m backend.server.main")
    print("  3. Install the VS Code extension")
    print()


async def run_agent_demo():
    """Demo different agent types."""
    print()
    print("=" * 60)
    print("🎭 Agent Types Demo")
    print("=" * 60)
    print()
    
    # Import agents
    from backend.agents.security_agent import SecurityAgent, SecurityAgentConfig
    from backend.agents.compliance_agent import ComplianceAgent, ComplianceAgentConfig
    from backend.agents.coding_agent import CodingAgent, CodingAgentConfig
    
    # Security Agent (works without LLM)
    print("🔒 Security Agent (Semgrep-based)")
    security_config = SecurityAgentConfig(
        semgrep_enabled=False,  # Disable for demo (semgrep may not be installed)
        llm_enabled=False,
    )
    security_agent = SecurityAgent(config=security_config)
    print(f"  Name: {security_agent.metadata.name}")
    print(f"  Description: {security_agent.metadata.description}")
    print(f"  LLM required: No (uses Semgrep)")
    print()
    
    # Compliance Agent
    print("📋 Compliance Agent (Rule-based)")
    compliance_config = ComplianceAgentConfig(
        llm_enabled=False,
    )
    compliance_agent = ComplianceAgent(config=compliance_config)
    await compliance_agent.load_rules()
    print(f"  Name: {compliance_agent.metadata.name}")
    print(f"  Description: {compliance_agent.metadata.description}")
    print(f"  Rules loaded: {len(compliance_agent._rules)}")
    print()
    
    # Coding Agent
    print("💻 Coding Agent (Patch-only)")
    coding_config = CodingAgentConfig()
    coding_agent = CodingAgent(config=coding_config)
    print(f"  Name: {coding_agent.metadata.name}")
    print(f"  Description: {coding_agent.metadata.description}")
    print(f"  Output: Unified diff only (never writes files)")
    print()
    
    print("✅ All agents initialized successfully")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="OMNI Demo Mode")
    parser.add_argument(
        "--agents",
        action="store_true",
        help="Show agent types demo"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full demo"
    )
    
    args = parser.parse_args()
    
    if args.agents:
        asyncio.run(run_agent_demo())
    elif args.full:
        asyncio.run(run_demo())
        asyncio.run(run_agent_demo())
    else:
        asyncio.run(run_demo())


if __name__ == "__main__":
    main()

# Domain-Specific Patterns

> Last updated: 2026-01-10T15:19:07.626348

Domain logic and specialized patterns detected in the codebase.

## 💬 Chat System

Chat/conversation management components:

- `vscode-extension\src\views\chatViewProvider.ts` — Page Component
- `vscode-extension\out\views\chatViewProvider.d.ts` — Page Component
- `vscode-extension\out\views\chatViewProvider.js` — Page Component

## 📚 RAG (Retrieval-Augmented Generation)

Knowledge retrieval and context injection:

- `backend\adapters\vectordb\chroma_adapter.py` — ChromaDB Vector Database Adapter
- `backend\rag\service.py` — RAG Service using LlamaIndex
- `backend\core\interfaces\vectordb.py` — Vector Database Provider Interface
- `backend\rag\__init__.py` — RAG (Retrieval-Augmented Generation) Module
- `backend\adapters\vectordb\base.py` — Base Vector Database Adapter
- `backend\agents\rag_agent.py` — RAG Agent
- `backend\adapters\vectordb\qdrant_adapter.py` — Qdrant Vector Database Adapter
- `backend\adapters\vectordb\__init__.py` — Vector Database Adapters Package
- `backend\tests\core\test_vectordb_adapter.py` — Unit Tests for VectorDB Adapter Interface
- `backend\adapters\vectordb\faiss_adapter.py` — FAISS Vector Database Adapter

**Typical Flow:**
1. Query embedding generation
2. Vector similarity search
3. Context retrieval from knowledge base
4. Prompt augmentation with retrieved context
5. LLM response generation

## 🔐 Authentication

User authentication and session management:

- `demo\sample_project\auth.py` — Sample Authentication Module

## 🤖 AI Agents

AI agent implementations:

- `backend\tests\agents\test_context_persistence.py` — Tests for Context Agent persistence and unified DetailedFileSummary.
- `backend\agents\base_agents.py` — Base Agent Implementations
- `backend\agents\__init__.py` — Agent Plugin System
- `backend\tests\agents\__init__.py` — Agent Tests Package
- `backend\agents\loader.py` — Agent Loader and Registry
- `backend\agents\context_agent.py` — Context Agent
- `backend\core\interfaces\agent.py` — Agent Interface
- `vscode-extension\out\views\agentsTreeProvider.d.ts` — Page Component
- `backend\agents\coding_agent.py` — Coding Agent Plugin
- `backend\tests\agents\test_registry.py` — Unit Tests for Agent Registry

---

**Detected Domains:** chat, rag, auth, agents
"""
Unit Tests for LLM Adapter Interface

Tests the FakeLLMProvider and validates the LLMProvider interface contract.

Run:
    pytest backend/tests/core/test_llm_adapter.py -v
    pytest backend/tests/core/test_llm_adapter.py -v -k "health"  # run specific test
"""

import pytest
from typing import List

from backend.core.interfaces.llm import LLMMessage, LLMResponse, MessageRole
from backend.tests.conftest import FakeLLMProvider


class TestFakeLLMProviderHealth:
    """Tests for LLM provider health check functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_returns_false_before_init(self, fake_llm: FakeLLMProvider):
        """Health check should return False before initialization."""
        # Provider not initialized yet
        result = await fake_llm.health_check()
        assert result is False, "Health check should fail before initialize()"
    
    @pytest.mark.asyncio
    async def test_health_check_returns_true_after_init(self, fake_llm: FakeLLMProvider):
        """Health check should return True after initialization."""
        await fake_llm.initialize()
        
        result = await fake_llm.health_check()
        assert result is True, "Health check should pass after initialize()"
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_health_check_can_be_set_unhealthy(self, fake_llm: FakeLLMProvider):
        """Health check should return False when explicitly set unhealthy."""
        await fake_llm.initialize()
        fake_llm.set_healthy(False)
        
        result = await fake_llm.health_check()
        assert result is False, "Health check should fail when set unhealthy"
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_health_check_returns_false_after_shutdown(self, fake_llm: FakeLLMProvider):
        """Health check should return False after shutdown."""
        await fake_llm.initialize()
        await fake_llm.shutdown()
        
        result = await fake_llm.health_check()
        assert result is False, "Health check should fail after shutdown()"


class TestFakeLLMProviderComplete:
    """Tests for LLM provider text generation (complete) functionality."""
    
    @pytest.mark.asyncio
    async def test_complete_returns_response(
        self,
        fake_llm: FakeLLMProvider,
        sample_messages: List[LLMMessage],
    ):
        """Complete should return an LLMResponse with content."""
        await fake_llm.initialize()
        
        response = await fake_llm.complete(sample_messages)
        
        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert len(response.content) > 0
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_complete_returns_configured_response(
        self,
        fake_llm: FakeLLMProvider,
        sample_messages: List[LLMMessage],
    ):
        """Complete should return the configured response text."""
        await fake_llm.initialize()
        expected = "This is my custom test response!"
        fake_llm.set_response(expected)
        
        response = await fake_llm.complete(sample_messages)
        
        assert response.content == expected
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_complete_includes_model_in_response(
        self,
        fake_llm: FakeLLMProvider,
        sample_messages: List[LLMMessage],
    ):
        """Complete should include the model name in the response."""
        await fake_llm.initialize()
        
        response = await fake_llm.complete(sample_messages)
        
        assert response.model == fake_llm.config.model
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_complete_includes_usage_stats(
        self,
        fake_llm: FakeLLMProvider,
        sample_messages: List[LLMMessage],
    ):
        """Complete should include token usage statistics."""
        await fake_llm.initialize()
        
        response = await fake_llm.complete(sample_messages)
        
        assert "prompt_tokens" in response.usage
        assert "completion_tokens" in response.usage
        assert response.usage["prompt_tokens"] >= 0
        assert response.usage["completion_tokens"] >= 0
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_complete_increments_call_count(
        self,
        fake_llm: FakeLLMProvider,
        sample_messages: List[LLMMessage],
    ):
        """Complete should increment the call count."""
        await fake_llm.initialize()
        
        assert fake_llm.get_call_count() == 0
        
        await fake_llm.complete(sample_messages)
        assert fake_llm.get_call_count() == 1
        
        await fake_llm.complete(sample_messages)
        assert fake_llm.get_call_count() == 2
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_complete_stores_last_messages(
        self,
        fake_llm: FakeLLMProvider,
        sample_messages: List[LLMMessage],
    ):
        """Complete should store the last messages for inspection."""
        await fake_llm.initialize()
        
        await fake_llm.complete(sample_messages)
        
        last_messages = fake_llm.get_last_messages()
        assert len(last_messages) == len(sample_messages)
        assert last_messages[0].role == sample_messages[0].role
        assert last_messages[0].content == sample_messages[0].content
        
        await fake_llm.shutdown()


class TestFakeLLMProviderStream:
    """Tests for LLM provider streaming functionality."""
    
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(
        self,
        fake_llm: FakeLLMProvider,
        sample_messages: List[LLMMessage],
    ):
        """Stream should yield text chunks."""
        await fake_llm.initialize()
        
        chunks = []
        async for chunk in fake_llm.stream(sample_messages):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_stream_yields_configured_chunks(
        self,
        fake_llm: FakeLLMProvider,
        sample_messages: List[LLMMessage],
    ):
        """Stream should yield the configured chunks."""
        await fake_llm.initialize()
        expected_chunks = ["Hello", " ", "World", "!"]
        fake_llm.set_stream_chunks(expected_chunks)
        
        chunks = []
        async for chunk in fake_llm.stream(sample_messages):
            chunks.append(chunk)
        
        assert chunks == expected_chunks
        
        await fake_llm.shutdown()


class TestFakeLLMProviderEmbed:
    """Tests for LLM provider embedding functionality."""
    
    @pytest.mark.asyncio
    async def test_embed_returns_embeddings(self, fake_llm: FakeLLMProvider):
        """Embed should return embeddings for input texts."""
        await fake_llm.initialize()
        
        texts = ["Hello world", "Test text"]
        embeddings = await fake_llm.embed(texts)
        
        assert len(embeddings) == len(texts)
        assert all(isinstance(e, list) for e in embeddings)
        assert all(isinstance(v, float) for e in embeddings for v in e)
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_embed_returns_consistent_dimension(self, fake_llm: FakeLLMProvider):
        """Embed should return embeddings of consistent dimension."""
        await fake_llm.initialize()
        
        texts = ["Short", "A much longer text for testing"]
        embeddings = await fake_llm.embed(texts)
        
        assert len(embeddings[0]) == len(embeddings[1])
        
        await fake_llm.shutdown()
    
    @pytest.mark.asyncio
    async def test_embed_returns_configured_embedding(self, fake_llm: FakeLLMProvider):
        """Embed should return configured embedding for specific text."""
        await fake_llm.initialize()
        text = "specific text"
        expected = [0.1, 0.2, 0.3, 0.4, 0.5]
        fake_llm.set_embedding(text, expected)
        
        embeddings = await fake_llm.embed([text])
        
        assert embeddings[0] == expected
        
        await fake_llm.shutdown()

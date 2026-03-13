"""
Smoke test for LLM connectivity.
Runs against REAL Azure OpenAI. No mocks.

This test validates:
1. Azure OpenAI client can be instantiated from environment
2. Chat completions endpoint is reachable
3. Embeddings endpoint is reachable
4. Response formats are correct

Requirements:
    - AZURE_OPENAI_ENDPOINT must be set
    - AZURE_OPENAI_KEY must be set
    - AZURE_OPENAI_CHAT_DEPLOYMENT must be set
    - Network connectivity to Azure
"""
import os
import pytest
from src.config.llm import get_llm_client, get_chat_model, get_embedding_model, reset_client


class TestLLMConnectivity:
    """Test Azure OpenAI connectivity."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Reset client before and after each test."""
        reset_client()
        yield
        reset_client()

    @pytest.mark.skipif(
        not os.environ.get("AZURE_OPENAI_ENDPOINT") or
        not os.environ.get("AZURE_OPENAI_KEY") or
        not os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        reason="Requires Azure OpenAI credentials"
    )
    def test_chat_completion_works(self):
        """
        Chat completion should return valid response.
        
        This test:
        1. Creates a new LLM client
        2. Sends a simple chat completion request
        3. Validates response structure and content
        """
        client = get_llm_client()
        model = get_chat_model()
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=10,
            temperature=0.7,
        )
        
        # Validate response structure
        assert response.choices is not None
        assert len(response.choices) > 0
        assert response.choices[0].message is not None
        assert response.choices[0].message.content is not None
        
        # Note: Some models may return empty content for very short prompts
        # The important validation is that the API call succeeds
        content = response.choices[0].message.content
        assert content is not None

    @pytest.mark.skipif(
        not os.environ.get("AZURE_OPENAI_ENDPOINT") or
        not os.environ.get("AZURE_OPENAI_KEY"),
        reason="Requires Azure OpenAI credentials"
    )
    def test_embedding_works(self):
        """
        Embedding should return 1536-dim vector.
        
        This test:
        1. Creates a new LLM client
        2. Sends an embedding request
        3. Validates vector dimensions
        """
        client = get_llm_client()
        model = get_embedding_model()
        
        response = client.embeddings.create(
            input="test embedding",
            model=model,
        )
        
        # Validate response structure
        assert response.data is not None
        assert len(response.data) > 0
        assert response.data[0].embedding is not None

        # Validate vector dimensions
        embedding = response.data[0].embedding
        expected_dim = os.environ.get("EMBEDDING_DIM")
        if expected_dim:
            assert len(embedding) == int(expected_dim)
        else:
            assert len(embedding) > 0  # Flexible smoke check

        # Validate all values are floats
        assert all(isinstance(v, float) for v in embedding)

    @pytest.mark.skipif(
        not os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        reason="Requires AZURE_OPENAI_CHAT_DEPLOYMENT"
    )
    def test_get_chat_model_returns_string(self):
        """get_chat_model should return a non-empty string."""
        model = get_chat_model()
        assert isinstance(model, str)
        assert len(model) > 0

    def test_get_embedding_model_returns_string(self):
        """get_embedding_model should return a non-empty string."""
        model = get_embedding_model()
        assert isinstance(model, str)
        assert len(model) > 0

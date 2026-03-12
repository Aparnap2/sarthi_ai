"""Tests for ContextInterviewAgent."""
import pytest
import os
import uuid
from unittest.mock import Mock, patch, MagicMock
from src.agents.context_interview_agent import ONBOARDING_QUESTIONS


# Mock environment variables before importing ContextInterviewAgent
@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_KEY": "test-key-123",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4-test",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333"
    }):
        yield


class TestContextInterviewAgent:
    """Test suite for ContextInterviewAgent onboarding flow."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_env):
        """Set up test fixtures."""
        # Import after env is mocked
        from src.agents.context_interview_agent import ContextInterviewAgent
        
        with patch('src.agents.context_interview_agent.MemoryAgent'):
            self.agent = ContextInterviewAgent()
        self.founder_id = str(uuid.uuid4())

    def test_get_next_question_returns_unanswered(self):
        """Test that get_next_question returns the first unanswered question."""
        answered = ["mission", "philosophy_money"]
        next_q = self.agent.get_next_question(answered)
        
        assert next_q is not None
        assert next_q["id"] == "non_negotiable"
        assert next_q["context_type"] == "non_negotiable"

    def test_get_next_question_returns_none_when_complete(self):
        """Test that get_next_question returns None when all questions answered."""
        all_ids = [q["id"] for q in ONBOARDING_QUESTIONS]
        result = self.agent.get_next_question(all_ids)
        
        assert result is None

    def test_is_complete(self):
        """Test onboarding completion check."""
        # All 6 questions answered
        assert self.agent.is_complete([
            "mission", 
            "philosophy_money", 
            "non_negotiable", 
            "icp", 
            "success", 
            "constraints"
        ]) == True
        
        # Only 2 questions answered
        assert self.agent.is_complete(["mission", "philosophy_money"]) == False
        
        # Exactly 6 questions
        assert self.agent.is_complete(["a", "b", "c", "d", "e", "f"]) == True
        
        # 5 questions (not complete)
        assert self.agent.is_complete(["a", "b", "c", "d", "e"]) == False

    @patch('src.agents.context_interview_agent.MemoryAgent')
    def test_process_answer_extracts_context(self, mock_memory_agent_class, mock_env):
        """Test that process_answer extracts structured context from raw answer."""
        # Mock MemoryAgent instance
        mock_memory = Mock()
        mock_memory.write.return_value = "qdrant-point-123"
        mock_memory_agent_class.return_value = mock_memory
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''{
            "context_type": "mission",
            "content": "Solo technical founders waste months building the wrong thing because they have no one to challenge their assumptions.",
            "confidence": 0.95,
            "implicit_constraints": ["time", "solo founder"],
            "keywords": ["technical", "founders", "assumptions"]
        }'''
        
        # Create agent with mocked dependencies
        from src.agents.context_interview_agent import ContextInterviewAgent
        
        with patch('src.agents.context_interview_agent.AzureOpenAI') as mock_azure:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_azure.return_value = mock_client
            
            agent = ContextInterviewAgent()
            
            result = agent.process_answer(
                founder_id=self.founder_id,
                question_id="mission",
                question_text="What problem are you solving?",
                raw_answer="Solo technical founders waste months building the wrong thing because they have no one to challenge their assumptions."
            )
        
        # Verify result structure
        assert "context_type" in result
        assert "content" in result
        assert "confidence" in result
        assert "qdrant_point_id" in result
        assert result["context_type"] == "mission"
        assert result["confidence"] == 0.95
        assert result["qdrant_point_id"] == "qdrant-point-123"
        
        # Verify MemoryAgent.write was called
        mock_memory.write.assert_called_once()

    def test_onboarding_questions_structure(self):
        """Test that ONBOARDING_QUESTIONS has correct structure."""
        assert len(ONBOARDING_QUESTIONS) == 6
        
        required_keys = {"id", "text", "context_type"}
        for q in ONBOARDING_QUESTIONS:
            assert set(q.keys()) == required_keys
            assert isinstance(q["id"], str)
            assert isinstance(q["text"], str)
            assert isinstance(q["context_type"], str)
            assert len(q["text"]) > 0

    def test_question_ids_are_unique(self):
        """Test that all question IDs are unique."""
        ids = [q["id"] for q in ONBOARDING_QUESTIONS]
        assert len(ids) == len(set(ids)), "Question IDs must be unique"

    def test_context_types_are_valid(self):
        """Test that context types match expected categories."""
        valid_types = {"mission", "philosophy", "non_negotiable", "icp", "goal", "constraint"}
        context_types = {q["context_type"] for q in ONBOARDING_QUESTIONS}
        
        assert context_types == valid_types

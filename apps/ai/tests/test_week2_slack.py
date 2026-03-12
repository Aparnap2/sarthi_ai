"""Tests for SlackNotifier."""

import pytest
from unittest.mock import MagicMock, patch
from slack_sdk.errors import SlackApiError

from src.services.slack_notifier import SlackNotifier, TRIGGER_EMOJI


class TestSlackNotifierInitialization:
    """Test SlackNotifier initialization."""

    def test_init_with_env_token(self):
        """Test initialization with SLACK_BOT_TOKEN."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            assert notifier.client is not None


class TestTriggerEmojis:
    """Test trigger emoji mapping."""

    def test_all_trigger_types_have_emojis(self):
        """Test that all trigger types have emoji mappings."""
        expected_types = {"commitment_gap", "decision_stall", "market_signal", "momentum_drop"}
        
        assert set(TRIGGER_EMOJI.keys()) == expected_types

    def test_emojis_are_valid_unicode(self):
        """Test that all emojis are valid Unicode strings."""
        for emoji in TRIGGER_EMOJI.values():
            assert isinstance(emoji, str)
            assert len(emoji) > 0

    def test_specific_emoji_mappings(self):
        """Test specific emoji mappings."""
        assert TRIGGER_EMOJI["commitment_gap"] == "🎯"
        assert TRIGGER_EMOJI["decision_stall"] == "⏸️"
        assert TRIGGER_EMOJI["market_signal"] == "📡"
        assert TRIGGER_EMOJI["momentum_drop"] == "📉"


class TestSendIntervention:
    """Test send_intervention method."""

    def test_send_intervention_success(self):
        """Test successful intervention message."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            # Mock Slack client
            mock_response = {"ts": "1234567890.123456"}
            notifier.client.chat_postMessage = MagicMock(return_value=mock_response)
            
            ts = notifier.send_intervention(
                slack_user_id="U123456",
                trigger_type="commitment_gap",
                message="You missed 2 commitments",
                cta="View Commitments",
                workflow_id="workflow-123"
            )
            
            assert ts == "1234567890.123456"
            notifier.client.chat_postMessage.assert_called_once()

    def test_send_intervention_includes_blocks(self):
        """Test that message includes Block Kit blocks."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            mock_response = {"ts": "1234567890.123456"}
            notifier.client.chat_postMessage = MagicMock(return_value=mock_response)
            
            notifier.send_intervention(
                slack_user_id="U123456",
                trigger_type="market_signal",
                message="Test message",
                cta="CTA",
                workflow_id="workflow-123"
            )
            
            # Verify blocks were sent
            call_args = notifier.client.chat_postMessage.call_args
            assert 'blocks' in call_args.kwargs
            assert len(call_args.kwargs['blocks']) >= 4  # Header, Section, Divider, 2x Actions

    def test_send_intervention_includes_emoji(self):
        """Test that correct emoji is included."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            mock_response = {"ts": "1234567890.123456"}
            notifier.client.chat_postMessage = MagicMock(return_value=mock_response)
            
            notifier.send_intervention(
                slack_user_id="U123456",
                trigger_type="momentum_drop",
                message="Test",
                cta="CTA",
                workflow_id="workflow-123"
            )
            
            # Verify header includes 📉
            call_args = notifier.client.chat_postMessage.call_args
            header_block = call_args.kwargs['blocks'][0]
            assert "📉" in str(header_block)

    def test_send_intervention_slack_error(self):
        """Test handling of Slack API errors."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            # Mock Slack API error
            error_response = MagicMock()
            error_response.response = {"error": "channel_not_found"}
            notifier.client.chat_postMessage = MagicMock(side_effect=SlackApiError(
                "channel_not_found",
                error_response.response
            ))
            
            ts = notifier.send_intervention(
                slack_user_id="U123456",
                trigger_type="commitment_gap",
                message="Test",
                cta="CTA",
                workflow_id="workflow-123"
            )
            
            assert ts is None

    def test_send_intervention_unknown_trigger_type(self):
        """Test handling of unknown trigger type."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            mock_response = {"ts": "1234567890.123456"}
            notifier.client.chat_postMessage = MagicMock(return_value=mock_response)
            
            notifier.send_intervention(
                slack_user_id="U123456",
                trigger_type="unknown_type",
                message="Test",
                cta="CTA",
                workflow_id="workflow-123"
            )
            
            # Should use default robot emoji
            call_args = notifier.client.chat_postMessage.call_args
            header_block = call_args.kwargs['blocks'][0]
            assert "🤖" in str(header_block)


class TestSendFollowup:
    """Test send_followup method."""

    def test_send_followup_success(self):
        """Test successful followup message."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            mock_response = {"ts": "1234567890.123457"}
            notifier.client.chat_postMessage = MagicMock(return_value=mock_response)
            
            ts = notifier.send_followup(
                slack_user_id="U123456",
                original_ts="1234567890.123456",
                message="Followup message"
            )
            
            assert ts == "1234567890.123457"
            notifier.client.chat_postMessage.assert_called_once()

    def test_send_followup_in_thread(self):
        """Test that followup is sent in thread."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            mock_response = {"ts": "1234567890.123457"}
            notifier.client.chat_postMessage = MagicMock(return_value=mock_response)
            
            notifier.send_followup(
                slack_user_id="U123456",
                original_ts="1234567890.123456",
                message="Followup"
            )
            
            # Verify thread_ts was set
            call_args = notifier.client.chat_postMessage.call_args
            assert call_args.kwargs['thread_ts'] == "1234567890.123456"

    def test_send_followup_error(self):
        """Test handling of followup errors."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            error_response = MagicMock()
            error_response.response = {"error": "channel_not_found"}
            notifier.client.chat_postMessage = MagicMock(side_effect=SlackApiError(
                "channel_not_found",
                error_response.response
            ))
            
            ts = notifier.send_followup(
                slack_user_id="U123456",
                original_ts="1234567890.123456",
                message="Followup"
            )
            
            assert ts is None


class TestUpdateMessageBlocks:
    """Test update_message_blocks method."""

    def test_update_blocks_success(self):
        """Test successful block update."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            notifier.client.chat_update = MagicMock(return_value={})
            
            from slack_sdk.models.blocks import SectionBlock, PlainTextObject
            
            blocks = [SectionBlock(text=PlainTextObject(text="Updated"))]
            
            result = notifier.update_message_blocks(
                channel="U123456",
                ts="1234567890.123456",
                blocks=blocks
            )
            
            assert result is True
            notifier.client.chat_update.assert_called_once()

    def test_update_blocks_error(self):
        """Test handling of update errors."""
        with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'test-token'}):
            notifier = SlackNotifier()
            
            error_response = MagicMock()
            error_response.response = {"error": "message_not_found"}
            notifier.client.chat_update = MagicMock(side_effect=SlackApiError(
                "message_not_found",
                error_response.response
            ))
            
            result = notifier.update_message_blocks(
                channel="U123456",
                ts="1234567890.123456",
                blocks=[]
            )
            
            assert result is False

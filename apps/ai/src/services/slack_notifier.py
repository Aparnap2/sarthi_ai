"""
SlackNotifier — Block Kit messages with 👍/👎 rating buttons.

Sends intervention DMs to founders via Slack.
Supports CTA buttons, snooze, and feedback collection.
"""

import os
from typing import Optional
import structlog
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.models.blocks import (
    HeaderBlock,
    SectionBlock,
    DividerBlock,
    ActionsBlock,
    ButtonElement,
    PlainTextObject,
)

logger = structlog.get_logger(__name__)

# Trigger type → emoji mapping
TRIGGER_EMOJI = {
    "commitment_gap": "🎯",
    "decision_stall": "⏸️",
    "market_signal": "📡",
    "momentum_drop": "📉",
}


class SlackNotifier:
    """
    Sends Slack messages with Block Kit formatting.
    
    Features:
    - Intervention DMs with CTA buttons
    - Snooze functionality (48h)
    - Feedback collection (👍/👎)
    """

    def __init__(self):
        """Initialize Slack client with bot token."""
        self.client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

    def send_intervention(
        self,
        slack_user_id: str,
        trigger_type: str,
        message: str,
        cta: str,
        workflow_id: str
    ) -> Optional[str]:
        """
        Send Block Kit intervention DM.
        
        Args:
            slack_user_id: Slack user ID (e.g., "U1234567890")
            trigger_type: Type of trigger (commitment_gap, decision_stall, etc.)
            message: Main message text
            cta: Call-to-action button text
            workflow_id: Unique workflow ID for button actions
            
        Returns:
            Slack message timestamp (ts) or None if failed
        """
        emoji = TRIGGER_EMOJI.get(trigger_type, "🤖")
        
        # Build Block Kit message
        blocks = [
            HeaderBlock(
                text=PlainTextObject(text=f"{emoji}  Saarathi Alert")
            ),
            SectionBlock(text=PlainTextObject(text=message)),
            DividerBlock(),
            # Primary actions: CTA + Snooze
            ActionsBlock(elements=[
                ButtonElement(
                    text=PlainTextObject(text=cta, emoji=True),
                    action_id=f"cta_{workflow_id}",
                    style="primary",
                ),
                ButtonElement(
                    text=PlainTextObject(text="⏰ Snooze 48h"),
                    action_id=f"snooze_{workflow_id}",
                ),
            ]),
            # Feedback: 👍/👎 rating
            ActionsBlock(elements=[
                ButtonElement(
                    text=PlainTextObject(text="👍 Useful"),
                    action_id=f"rate_good_{workflow_id}",
                ),
                ButtonElement(
                    text=PlainTextObject(text="👎 Not now"),
                    action_id=f"rate_bad_{workflow_id}",
                ),
            ]),
        ]

        try:
            response = self.client.chat_postMessage(
                channel=slack_user_id,
                text=message,
                blocks=[b.to_dict() for b in blocks],
            )
            
            logger.info(
                "Slack intervention sent",
                user_id=slack_user_id,
                trigger_type=trigger_type,
                ts=response.get("ts")
            )
            
            return response.get("ts")
            
        except SlackApiError as e:
            logger.error(
                "Slack send failed",
                error=e.response["error"],
                user_id=slack_user_id
            )
            return None

    def send_followup(
        self,
        slack_user_id: str,
        original_ts: str,
        message: str
    ) -> Optional[str]:
        """
        Send a follow-up message as a thread reply.
        
        Args:
            slack_user_id: Slack user ID
            original_ts: Original message timestamp
            message: Follow-up message text
            
        Returns:
            Slack message timestamp (ts) or None if failed
        """
        try:
            response = self.client.chat_postMessage(
                channel=slack_user_id,
                text=message,
                thread_ts=original_ts,
            )
            
            logger.info(
                "Slack followup sent",
                user_id=slack_user_id,
                original_ts=original_ts
            )
            
            return response.get("ts")
            
        except SlackApiError as e:
            logger.error(
                "Slack followup failed",
                error=e.response["error"],
                user_id=slack_user_id
            )
            return None

    def update_message_blocks(
        self,
        channel: str,
        ts: str,
        blocks: list
    ) -> bool:
        """
        Update message blocks (e.g., after button click).
        
        Args:
            channel: Channel or user ID
            ts: Message timestamp
            blocks: New blocks to display
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.chat_update(
                channel=channel,
                ts=ts,
                blocks=[b.to_dict() if hasattr(b, 'to_dict') else b for b in blocks],
            )
            
            logger.info("Slack message updated", channel=channel, ts=ts)
            return True
            
        except SlackApiError as e:
            logger.error(
                "Slack update failed",
                error=e.response["error"],
                channel=channel
            )
            return False

import os
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

class SlackClient:
    def __init__(self):
        self.client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        self.socket_client = SocketModeClient(
            app_token=os.getenv("SLACK_APP_TOKEN"),
            web_client=self.client
        )

    async def open_decision_modal(self, trigger_id: str):
        """Open the decision logging modal"""
        modal_view = {
            "type": "modal",
            "callback_id": "decision_modal",
            "title": {
                "type": "plain_text",
                "text": "Log Decision"
            },
            "submit": {
                "type": "plain_text",
                "text": "Log Decision"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "decision_block",
                    "label": {
                        "type": "plain_text",
                        "text": "What did you decide?"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "decision_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., Hire Sarah as CTO"
                        }
                    }
                },
                {
                    "type": "input",
                    "block_id": "alternatives_block",
                    "label": {
                        "type": "plain_text",
                        "text": "What were the alternatives?"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "alternatives_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., Wait 3 months, Hire externally"
                        },
                        "multiline": True
                    },
                    "optional": True
                },
                {
                    "type": "input",
                    "block_id": "reasoning_block",
                    "label": {
                        "type": "plain_text",
                        "text": "Why did you decide this?"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "reasoning_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Key factors, risks considered, etc."
                        },
                        "multiline": True
                    }
                }
            ]
        }

        try:
            response = self.client.views_open(
                trigger_id=trigger_id,
                view=modal_view
            )
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def handle_modal_submit(self, payload: dict, tenant_id: str):
        """Process decision modal submission"""
        # Extract values from modal submission
        values = payload.get("view", {}).get("state", {}).get("values", {})

        decision_data = {
            "decided": values.get("decision_block", {}).get("decision_input", {}).get("value", ""),
            "alternatives": values.get("alternatives_block", {}).get("alternatives_input", {}).get("value", ""),
            "reasoning": values.get("reasoning_block", {}).get("reasoning_input", {}).get("value", ""),
        }

        # Call log_decision activity
        from src.activities.log_decision import log_decision
        result = await log_decision(decision_data, tenant_id)
        return result

    def fetch_channel_messages(self, channel_id: str, limit: int = 20) -> list[dict]:
        """Fetch recent messages from a Slack channel."""
        try:
            response = self.client.conversations_history(
                channel=channel_id,
                limit=limit,
            )

            messages = []
            for msg in response.get("messages", []):
                # Skip bot messages and system messages
                if msg.get("subtype") and msg["subtype"] not in (None, "file_share"):
                    continue

                messages.append({
                    "text": msg.get("text", ""),
                    "user": msg.get("user", "unknown"),
                    "channel": channel_id,
                    "timestamp": msg.get("ts", ""),
                })

            return messages
        except Exception as e:
            # Return empty list on error
            return []

    def get_channel_id_by_name(self, channel_name: str) -> str | None:
        """Get channel ID from channel name."""
        try:
            response = self.client.conversations_list()
            for channel in response.get("channels", []):
                if channel.get("name") == channel_name.lstrip("#"):
                    return channel.get("id")
            return None
        except Exception:
            return None
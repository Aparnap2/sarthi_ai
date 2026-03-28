"""
Shared Slack Activity for Temporal.

Sends messages to Slack using webhook or bot API.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx
from temporalio import activity

log = logging.getLogger(__name__)


def _safe_heartbeat(message: str) -> None:
    """Safely call activity.heartbeat, ignoring errors outside activity context."""
    try:
        activity.heartbeat(message)
    except RuntimeError:
        # Not in activity context (e.g., during testing)
        log.debug("Heartbeat (no context): %s", message)


@activity.defn(name="send_slack_message")
async def send_slack_message(text: str, blocks: list[dict] | None = None) -> dict[str, Any]:
    """
    Send a message to Slack via webhook or bot API.

    This activity:
    1. Validates input (text required)
    2. Sends to Slack webhook URL (if configured) or bot API
    3. Returns success/failure status

    Args:
        text: Plain text message (required)
        blocks: Optional Slack Block Kit blocks for rich formatting

    Returns:
        dict with keys:
            - ok: bool (True on success, False on error)
            - message_id: str (if available)
            - channel: str (if available)
            - error: str (only if ok=False)

    Note:
        Never raises — catches errors and returns {"ok": False, "error": "..."}
    """
    if not text or not text.strip():
        return {"ok": False, "error": "Message text cannot be empty"}

    try:
        _safe_heartbeat(f"Sending Slack message: {text[:50]}...")

        # Get Slack configuration from environment
        slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        slack_bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        slack_channel = os.getenv("SLACK_CHANNEL", "#general")

        payload: dict[str, Any] = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        headers = {"Content-Type": "application/json"}

        if slack_webhook_url:
            # Use webhook URL
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(slack_webhook_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

                _safe_heartbeat(f"Slack webhook response: {result}")

                return {
                    "ok": result.get("ok", True),
                    "message_id": "",
                    "channel": slack_channel,
                }

        elif slack_bot_token:
            # Use bot API
            api_url = "https://slack.com/api/chat.postMessage"
            headers["Authorization"] = f"Bearer {slack_bot_token}"
            payload["channel"] = slack_channel

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

                _safe_heartbeat(f"Slack bot API response: {result}")

                return {
                    "ok": result.get("ok", False),
                    "message_id": result.get("ts", ""),
                    "channel": slack_channel,
                    "error": result.get("error", "") if not result.get("ok") else "",
                }

        else:
            # No Slack configuration - log and return success (dev mode)
            _safe_heartbeat("No Slack configuration found - simulating success (dev mode)")
            return {
                "ok": True,
                "message_id": "simulated-" + str(hash(text)),
                "channel": slack_channel,
            }

    except httpx.HTTPStatusError as e:
        _safe_heartbeat(f"Slack HTTP error: {e}")
        return {"ok": False, "error": f"HTTP error: {e.response.status_code}"}

    except httpx.RequestError as e:
        _safe_heartbeat(f"Slack request error: {e}")
        return {"ok": False, "error": f"Request error: {str(e)}"}

    except Exception as e:
        _safe_heartbeat(f"Slack send failed: {e}")
        return {"ok": False, "error": str(e)}

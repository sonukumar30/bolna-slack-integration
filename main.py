"""
Bolna → Slack Integration
Receives Bolna webhook events when a call ends and sends a Slack alert
with: call id, agent_id, duration, and transcript.
"""

import os
import logging
from typing import Any

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN: str = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL_ID: str = os.environ["SLACK_CHANNEL_ID"]
BOLNA_WEBHOOK_SECRET: str = os.getenv("BOLNA_WEBHOOK_SECRET", "")

COMPLETED_STATUSES = {"completed", "ended"}

app = FastAPI(title="Bolna → Slack Integration", version="1.0.0")


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_slack_blocks(call_id: str, agent_id: str, duration: int, transcript: str) -> list[dict]:
    """Build Slack Block Kit message for a completed call."""

    # Truncate very long transcripts so Slack doesn't reject the payload
    MAX_TRANSCRIPT = 2900
    if len(transcript) > MAX_TRANSCRIPT:
        transcript = transcript[:MAX_TRANSCRIPT] + "\n… *(transcript truncated)*"

    duration_fmt = f"{duration // 60}m {duration % 60}s" if duration else "N/A"

    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Bolna Call Ended",
                "emoji": True,
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Call ID*\n`{call_id}`"},
                {"type": "mrkdwn", "text": f"*Agent ID*\n`{agent_id}`"},
                {"type": "mrkdwn", "text": f"*Duration*\n{duration_fmt}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Transcript*\n```{transcript or 'No transcript available.'}```",
            },
        },
    ]


async def send_slack_alert(call_id: str, agent_id: str, duration: int, transcript: str) -> None:
    """Post a message to the configured Slack channel."""
    blocks = build_slack_blocks(call_id, agent_id, duration, transcript)

    payload = {
        "channel": SLACK_CHANNEL_ID,
        "text": f"Bolna call `{call_id}` ended (duration: {duration}s)",
        "blocks": blocks,
    }

    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            json=payload,
            headers=headers,
        )

    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")

    logger.info("Slack alert sent for call %s", call_id)


def extract_call_fields(payload: dict[str, Any]) -> tuple[str, str, int, str]:
    """
    Extract (call_id, agent_id, duration, transcript) from the Bolna webhook payload.

    Bolna execution payload structure:
    {
        "id": "4c06b4d1-...",
        "agent_id": "3c90c3cc-...",
        "status": "completed",
        "transcript": "<string>",
        "telephony_data": {
            "duration": 42,   # seconds
            ...
        },
        ...
    }
    """
    call_id: str  = str(payload.get("id", "unknown"))
    agent_id: str = str(payload.get("agent_id", "unknown"))
    transcript: str = payload.get("transcript") or ""

    # duration lives inside telephony_data
    telephony: dict = payload.get("telephony_data") or {}
    duration: int = int(telephony.get("duration") or payload.get("conversation_time") or 0)

    return call_id, agent_id, duration, transcript


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/bolna")
async def bolna_webhook(request: Request):
    """
    Receives POST requests from Bolna whenever call execution data is pushed.
    Fires a Slack alert only when the call status is 'completed'.
    """
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    status: str = payload.get("status", "").lower()
    logger.info("Received Bolna webhook — status: %s", status)

    # Only alert on completed calls; silently ack other statuses (queued, in-progress…)
    if status not in COMPLETED_STATUSES:
        return JSONResponse({"received": True, "alerted": False, "status": status})

    try:
        call_id, agent_id, duration, transcript = extract_call_fields(payload)
    except Exception as exc:
        logger.exception("Failed to parse Bolna payload")
        raise HTTPException(status_code=422, detail=f"Payload parse error: {exc}")

    try:
        await send_slack_alert(call_id, agent_id, duration, transcript)
    except Exception as exc:
        logger.exception("Failed to send Slack alert")
        raise HTTPException(status_code=500, detail=f"Slack delivery failed: {exc}")

    return JSONResponse({"received": True, "alerted": True, "call_id": call_id})

"""
test_webhook.py — Manual / CI smoke-test for the Bolna → Slack integration.

Usage:
    # Start the server first:
    uvicorn main:app --reload

    # Then in another terminal:
    python test_webhook.py
"""

import json
import httpx

SERVER_URL = "http://localhost:8000/webhook/bolna"

# ── Sample payloads ───────────────────────────────────────────────────────────

COMPLETED_PAYLOAD = {
    "id": "4c06b4d1-4096-4561-919a-4f94539c8d4a",
    "agent_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
    "batch_id": "baab7cdc833145bf8dd260ff1f0a3f21",
    "conversation_time": 95,
    "total_cost": 0.043,
    "status": "completed",
    "error_message": None,
    "answered_by_voice_mail": False,
    "transcript": (
        "Agent: Hello! Thanks for calling Acme support. How can I help you today?\n"
        "User: Hi, I'd like to check the status of my order #12345.\n"
        "Agent: Sure! Let me look that up for you. Your order is currently in transit and "
        "expected to arrive by Thursday.\n"
        "User: Great, thank you!\n"
        "Agent: You're welcome. Have a wonderful day!"
    ),
    "created_at": "2024-01-23T01:14:37Z",
    "updated_at": "2024-01-29T18:31:22Z",
    "telephony_data": {
        "duration": 95,
        "to_number": "+10123456789",
        "from_number": "+19876543007",
        "recording_url": "https://bolna-call-recordings.s3.amazonaws.com/sample.mp3",
        "hosted_telephony": True,
        "call_type": "outbound",
        "provider": "twilio",
        "hangup_by": "Agent",
        "hangup_reason": "Normal Hangup",
    },
}

IN_PROGRESS_PAYLOAD = {
    "id": "9a1b2c3d-0000-0000-0000-111122223333",
    "agent_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
    "status": "in-progress",
    "transcript": "",
    "telephony_data": {"duration": 0},
}


def post(label: str, payload: dict) -> None:
    print(f"\n{'─'*60}")
    print(f"  TEST: {label}")
    print(f"{'─'*60}")
    try:
        r = httpx.post(SERVER_URL, json=payload, timeout=15)
        print(f"  HTTP {r.status_code}")
        print(f"  Body: {json.dumps(r.json(), indent=2)}")
    except httpx.ConnectError:
        print("Could not connect — is the server running?")


if __name__ == "__main__":
    post("Completed call  → should send Slack alert", COMPLETED_PAYLOAD)
    post("In-progress call → should NOT send Slack alert", IN_PROGRESS_PAYLOAD)
    print("\n✅  Tests finished. Check your Slack channel for the alert!\n")

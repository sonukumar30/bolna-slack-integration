# Bolna → Slack Integration

A lightweight Python/FastAPI webhook server that fires a **Slack alert every time a Bolna voice call ends**, including the call `id`, `agent_id`, `duration`, and `transcript`.

---

## How It Works

```
Bolna Platform
  │
  │  POST /webhook/bolna   (when call status = "completed")
  ▼
FastAPI Server (this app)
  │
  │  POST chat.postMessage
  ▼
Slack Channel
```

1. You configure a **webhook URL** in your Bolna agent's Analytics Tab.
2. Bolna sends a POST request to your server every time the call execution data changes (queued → in-progress → completed).
3. The server ignores intermediate events and fires a Slack message **only when `status = "completed"`**.
4. The Slack message shows call `id`, `agent_id`, `duration`, and the full `transcript` inside a formatted Block Kit card.

---

## Bolna Webhook Payload (relevant fields)

```json
{
  "id": "4c06b4d1-4096-4561-919a-4f94539c8d4a",       ← call ID
  "agent_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a", ← agent ID
  "status": "completed",
  "transcript": "Agent: Hello…\nUser: Hi…",
  "telephony_data": {
    "duration": 95                                      ← seconds
  }
}
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.11+ | `python --version` |
| A Bolna account | [platform.bolna.ai](https://platform.bolna.ai) |
| A Slack app with `chat:write` scope | See setup below |
| A publicly reachable URL | ngrok, Render, Railway, etc. |

---

## Setup

### 1. Clone / copy the project

```bash
git clone <your-repo>
cd bolna-slack-integration
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your `.env`

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```
SLACK_BOT_TOKEN=xoxb-…
SLACK_CHANNEL_ID=C08XXXXXXXXX
```

#### How to get `SLACK_BOT_TOKEN`
1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → From scratch.
2. Under **OAuth & Permissions → Scopes → Bot Token Scopes**, add `chat:write`.
3. Click **Install to Workspace**.
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`).
5. Invite the bot to your channel: `/invite @YourBotName`

#### How to get `SLACK_CHANNEL_ID`
Right-click the channel name in Slack → **View channel details** → scroll to the bottom. Copy the ID (e.g. `C08XXXXXXXXX`).

---

### 4. Run the server

```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### 5. Expose to the internet (local dev)

Use **ngrok** to get a public HTTPS URL:

```bash
ngrok http 8000
```

Copy the forwarding URL, e.g. `https://abc123.ngrok-free.app`.

Your webhook endpoint will be:
```
https://abc123.ngrok-free.app/webhook/bolna
```

---

### 6. Configure Bolna agent

1. Log in to [platform.bolna.ai](https://platform.bolna.ai).
2. Open your agent → **Analytics Tab**.
3. Paste your webhook URL under **"Push all execution data to webhook"**.
4. Click **Save agent**.

> **Whitelist note:** Bolna sends webhooks from IP `13.203.39.153`. If your server has a firewall, allow this IP.

---

### 7. Test without a real call

```bash
python test_webhook.py
```

This fires two test requests against your local server:
- A **completed** call — you should see a Slack message appear in your channel.
- An **in-progress** call — server silently acknowledges, no Slack message.

---

## Project Structure

```
bolna-slack-integration/
├── main.py            ← FastAPI server (webhook + Slack sender)
├── test_webhook.py    ← Smoke-test script
├── requirements.txt   ← Python dependencies
├── .env.example       ← Environment variable template
└── README.md          ← This file
```

---

## Deploying to Production

Any platform that can run a Python web process works. Quick options:

### Railway (one-click)
```bash
railway init
railway up
```
Set your env vars in the Railway dashboard → Variables.

### Render
- New Web Service → connect your repo
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Slack Alert Preview

```
📞 Bolna Call Ended
────────────────────────────────
Call ID         Agent ID
4c06b4d1-…     3c90c3cc-…

Duration
1m 35s
────────────────────────────────
Transcript
Agent: Hello! Thanks for calling...
User: Hi, I'd like to check...
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No Slack message for completed calls | Check `SLACK_CHANNEL_ID` is the channel ID (not name) and the bot is invited |
| `Slack API error: not_in_channel` | Run `/invite @YourBotName` in the Slack channel |
| `422 Unprocessable Entity` from server | Bolna payload changed shape — check logs |
| Bolna not reaching your server | Confirm the webhook URL is public and `13.203.39.153` is not firewalled |

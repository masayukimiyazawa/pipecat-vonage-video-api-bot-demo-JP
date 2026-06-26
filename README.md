# Pipecat Voice Bot — LM Studio + pyopenjtalk + Vonage

Voice conversation bot powered by LM Studio (local LLM/STT) and pyopenjtalk (local Japanese TTS). The frontend uses the Vonage Video JS SDK to connect to a Vonage Video session, and the Audio Connector bridges audio to the bot's Pipecat pipeline.

## Architecture

```
Browser (Vonage Video JS SDK)
    │ publish / subscribe
    ▼
Vonage Cloud
    │ Audio Connector (raw PCM16 WebSocket)
    ▼
Cloudflare Tunnel ───→ localhost:8005/ws
                            │
                       FastAPI + Pipecat
                       Pipeline: STT → LLM → TTS
                            │
                   LM Studio (:1234)    pyopenjtalk (local)
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [LM Studio](https://lmstudio.ai/) with an LLM and Whisper model loaded, listening on `localhost:1234`
- [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) (`brew install cloudflared`)

## Setup

### 1. Environment variables

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Example | Description |
|----------|---------|-------------|
| `LM_STUDIO_BASE_URL` | `http://localhost:1234/v1` | LM Studio API endpoint |
| `STT_LANGUAGE` | `ja` | Whisper language code |
| `VONAGE_APPLICATION_ID` | `abcd1234-...` | Vonage Video Application ID (required) |
| `VONAGE_PRIVATE_KEY` | `-----BEGIN PRIVATE KEY-----...` | Vonage private key (path or inline, required) |
| `WS_URI` | `wss://xxx.trycloudflare.com/ws` | Public WebSocket URL (auto-set by start.sh) |

### 2. Install dependencies

```bash
uv sync
```

## Running

### 3. Start LM Studio

Load an LLM and Whisper model, ensure the server is listening on `localhost:1234`.

### 4. One-command start (recommended)

```bash
bash start.sh
```

This automatically:
1. Starts a Cloudflare Tunnel (`cloudflared`) and captures the public URL
2. Updates `WS_URI` in `.env`
3. Restarts the Python server
4. Prints the URL to open in your browser

### 5. Open browser

Go to the printed URL and click **接続** (Connect).

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves frontend (`static/index.html`) |
| `/health` | GET | Health check |
| `/ws` | WebSocket | Pipecat pipeline endpoint (consumed by Audio Connector) |
| `/connect` | POST | Vonage Audio Connector (legacy, requires `WS_URI` env) |
| `/demo/connect` | POST | One-shot demo: creates session + token + starts Audio Connector |

## Project Structure

```
├── server.py                 # FastAPI server
├── bot.py                    # Pipecat pipeline definition
├── lm_studio_stt.py          # LM Studio STT service (JSON with base64 audio)
├── tts_piper_plus.py         # Piper-plus TTS wrapper (Ja/En)
├── pyproject.toml            # Dependencies
├── setup.sh                  # TTS voice model downloader
├── .env                      # Credentials (git-ignored)
├── .env.example              # Template
├── static/
│   └── index.html            # Frontend (Vonage Video JS SDK)
└── docs/
    ├── PLAN.md
    └── PLAN.ja.md
```

## Demo Flow

1. User opens the tunnel URL in a browser
2. Clicks **接続** → `POST /demo/connect` is called
3. Server creates a Vonage Video session, generates a JWT token, and starts the Audio Connector (pointing to `wss://tunnel-url/ws`)
4. Frontend joins the session via `OT.initSession(applicationId, sessionId)` + `session.connect(token)`
5. Frontend publishes microphone audio and subscribes to the bot's audio stream
6. Audio flows: Browser → Vonage Cloud → Audio Connector → Bot Pipeline → Audio Connector → Browser

## Sequencing

The bot initiates conversation on client connection by queueing an `LLMRunFrame`. No wake word required.
# pipecat-vonage-video-api-bot-demo-JP
# pipecat-vonage-video-api-bot-demo-JP

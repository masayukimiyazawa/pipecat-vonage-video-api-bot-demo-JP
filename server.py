import asyncio
import os
import warnings
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from vonage import Auth, HttpClientOptions, Vonage
from vonage_video import AudioConnectorOptions, TokenOptions

load_dotenv(override=True)

warnings.filterwarnings("ignore", message="'asyncio.iscoroutinefunction' is deprecated")


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise HTTPException(status_code=500, detail=f"Missing env var: {name}")
    return val


def _read_private_key(value: str) -> str:
    if value.startswith("-----"):
        return value
    with open(value) as f:
        return f.read()


def _create_vonage_client(application_id: str, private_key: str) -> Vonage:
    auth = Auth(application_id=application_id, private_key=private_key)
    options = HttpClientOptions(video_host="video.api.vonage.com", timeout=30)
    return Vonage(auth=auth, http_client_options=options)


def _generate_client_token(vng: Vonage, session_id: str) -> str:
    raw = vng.video.generate_client_token(
        TokenOptions(session_id=session_id, role="publisher")
    )
    if isinstance(raw, bytes):
        return raw.decode("utf-8")
    return str(raw)


async def _create_session_async(vng: Vonage) -> str:
    loop = asyncio.get_running_loop()
    session_id = await loop.run_in_executor(
        None, lambda: vng.video.create_session().session_id
    )
    logger.info(f"Created Vonage session: {session_id}")
    return session_id


async def _connect_audio_connector_async(
    vng: Vonage, session_id: str, ws_uri: str, audio_rate: int
) -> None:
    logger.info(
        f"Connecting Vonage Audio Connector: session={session_id}, ws={ws_uri}, rate={audio_rate}"
    )
    token = _generate_client_token(vng, session_id)
    audio_opts = AudioConnectorOptions(
        session_id=session_id,
        token=token,
        websocket={
            "uri": ws_uri,
            "audioRate": audio_rate,
            "bidirectional": True,
        },
    )

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, lambda: vng.video.start_audio_connector(audio_opts)
    )
    logger.info("Audio Connector started successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/connect")
async def connect() -> JSONResponse:
    application_id = _require_env("VONAGE_APPLICATION_ID")
    private_key_raw = _require_env("VONAGE_PRIVATE_KEY")
    private_key = _read_private_key(private_key_raw)
    ws_uri = _require_env("WS_URI")
    audio_rate = int(os.getenv("VONAGE_AUDIO_RATE", "16000"))

    vng = _create_vonage_client(application_id, private_key)
    session_id = await _create_session_async(vng)

    try:
        await _connect_audio_connector_async(vng, session_id, ws_uri, audio_rate)
    except Exception as e:
        logger.warning(f"Audio Connector start failed for session {session_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to connect Audio Connector: {e}"
        )

    return JSONResponse(
        {
            "status": "connect_triggered",
            "session_id": session_id,
            "ws_uri": ws_uri,
            "audio_rate": audio_rate,
        }
    )


@app.post("/demo/connect")
async def demo_connect(request: Request) -> JSONResponse:
    application_id = _require_env("VONAGE_APPLICATION_ID")
    private_key_raw = _require_env("VONAGE_PRIVATE_KEY")
    private_key = _read_private_key(private_key_raw)
    audio_rate = int(os.getenv("VONAGE_AUDIO_RATE", "16000"))

    ws_uri = os.getenv("WS_URI")
    if not ws_uri:
        host = request.headers.get("host", "localhost:8005")
        scheme = "ws" if host.startswith("localhost") else "wss"
        ws_uri = f"{scheme}://{host}/ws"

    vng = _create_vonage_client(application_id, private_key)
    session_id = await _create_session_async(vng)

    try:
        await _connect_audio_connector_async(vng, session_id, ws_uri, audio_rate)
    except Exception as e:
        logger.warning(f"Audio Connector start failed for session {session_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to connect Audio Connector: {e}"
        )

    token = _generate_client_token(vng, session_id)

    return JSONResponse(
        {
            "session_id": session_id,
            "token": token,
            "application_id": application_id,
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected to /ws")

    try:
        from bot import bot
        from pipecat.runner.types import WebSocketRunnerArguments

        runner_args = WebSocketRunnerArguments(websocket=websocket, body={})
        await bot(runner_args)
    except Exception as e:
        logger.exception(f"Pipecat bot error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)

"""OpenEye Gateway Service — API entry point."""

import base64
import json
import uuid

import nats
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException

from shared.config import ServiceConfig
from shared.schemas import HealthResponse, FrameMessage, AnalysisResult

config = ServiceConfig()
nc = None  # NATS connection

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage NATS connection lifecycle."""
    global nc
    nc = await nats.connect(config.nats.url)
    yield
    if nc:
        await nc.close()


app = FastAPI(
    title="OpenEye Gateway",
    version=config.version,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(service="gateway", version=config.version)


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_image(image: UploadFile = File(...)):
    """Upload a single image for synchronous analysis."""
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {image.content_type}. Allowed: {ALLOWED_CONTENT_TYPES}",
        )

    contents = await image.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    image_b64 = base64.b64encode(contents).decode("utf-8")
    frame_id = str(uuid.uuid4())

    frame_msg = FrameMessage(
        frame_id=frame_id,
        source_id="upload",
        source_type="upload",
        image_base64=image_b64,
    )

    try:
        response = await nc.request(
            "rpc.analyze",
            frame_msg.model_dump_json().encode(),
            timeout=30.0,
        )
        result = AnalysisResult(**json.loads(response.data.decode()))
        return result
    except nats.errors.TimeoutError:
        raise HTTPException(status_code=504, detail="Analysis timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

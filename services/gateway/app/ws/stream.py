"""WebSocket endpoint for real-time webcam frame analysis."""

import asyncio
import base64
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared.config import ServiceConfig
from shared.schemas import FrameMessage, AnalysisResult

logger = logging.getLogger("gateway.ws")

router = APIRouter()

config = ServiceConfig()


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time webcam analysis.

    Client sends:
        - JSON: {"image": "<base64 jpeg>", "source_id": "webcam-1"}
        - Or raw binary JPEG frames (source_id defaults to "webcam")

    Server responds with AnalysisResult JSON for each frame.
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    # Get NATS connection from app state
    nc = websocket.app.state.nc

    try:
        while True:
            data = await websocket.receive()

            if "text" in data:
                # JSON message with base64 image
                try:
                    msg = json.loads(data["text"])
                    image_b64 = msg.get("image", "")
                    source_id = msg.get("source_id", "webcam")
                except (json.JSONDecodeError, KeyError):
                    await websocket.send_json({"error": "Invalid JSON format"})
                    continue
            elif "bytes" in data:
                # Raw binary JPEG frame
                image_b64 = base64.b64encode(data["bytes"]).decode("utf-8")
                source_id = "webcam"
            else:
                continue

            if not image_b64:
                await websocket.send_json({"error": "No image data"})
                continue

            frame_id = str(uuid.uuid4())
            frame_msg = FrameMessage(
                frame_id=frame_id,
                source_id=source_id,
                source_type="webcam",
                image_base64=image_b64,
            )

            try:
                response = await nc.request(
                    "rpc.analyze",
                    frame_msg.model_dump_json().encode(),
                    timeout=30.0,
                )
                result = AnalysisResult(**json.loads(response.data.decode()))
                await websocket.send_json(result.model_dump(mode="json"))
            except asyncio.TimeoutError:
                await websocket.send_json({"error": "Analysis timed out"})
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                await websocket.send_json({"error": f"Analysis failed: {str(e)[:200]}"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

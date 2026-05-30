"""Frame capture from video sources (RTSP streams, webcams, video files)."""

import asyncio
import base64
import logging
import uuid
from typing import AsyncGenerator

import cv2
import numpy as np

from shared.config import IngestorConfig

logger = logging.getLogger("ingestor.capture")


def _resize_frame(frame: np.ndarray, max_width: int) -> np.ndarray:
    """Resize frame if wider than max_width, preserving aspect ratio."""
    h, w = frame.shape[:2]
    if w <= max_width:
        return frame
    scale = max_width / w
    new_w = max_width
    new_h = int(h * scale)
    return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _encode_frame(frame: np.ndarray, quality: int = 85) -> str:
    """Encode frame as JPEG and return base64 string."""
    params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode(".jpg", frame, params)
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


async def capture_frames(
    source: str,
    config: IngestorConfig,
    stop_event: asyncio.Event,
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Yield (frame_id, image_base64) tuples from a video source.

    source: RTSP URL, video file path, or device index as string (e.g. "0")
    """
    # Parse source — numeric means device index
    if source.isdigit():
        cap_source = int(source)
    else:
        cap_source = source

    interval = 1.0 / config.fps if config.fps > 0 else 1.0

    while not stop_event.is_set():
        cap = cv2.VideoCapture(cap_source)
        if not cap.isOpened():
            logger.error(f"Cannot open source: {source}")
            await asyncio.sleep(config.reconnect_delay)
            continue

        logger.info(f"Capturing from source: {source} at {config.fps} fps")

        try:
            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"Frame read failed from {source}, reconnecting...")
                    break

                frame = _resize_frame(frame, config.max_width)
                image_b64 = _encode_frame(frame, config.jpeg_quality)
                frame_id = str(uuid.uuid4())

                yield frame_id, image_b64

                await asyncio.sleep(interval)
        finally:
            cap.release()

        if not stop_event.is_set():
            logger.info(f"Reconnecting to {source} in {config.reconnect_delay}s...")
            await asyncio.sleep(config.reconnect_delay)

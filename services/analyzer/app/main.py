"""OpenEye Analyzer Service — Vision model inference."""

import asyncio
import json
import signal
import logging

import nats

from shared.config import ServiceConfig
from shared.schemas import FrameMessage, AnalysisResult
from app.models import analyze_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analyzer")

config = ServiceConfig()
shutdown_event = asyncio.Event()


async def handle_rpc_analyze(msg):
    """Handle synchronous analysis request (single image via request/reply)."""
    try:
        data = json.loads(msg.data.decode())
        frame = FrameMessage(**data)

        result = await analyze_image(
            image_base64=frame.image_base64,
            frame_id=frame.frame_id,
            source_id=frame.source_id,
            config=config.model,
        )

        await msg.respond(result.model_dump_json().encode())
        logger.info(f"Analyzed frame {frame.frame_id}: severity={result.severity}")
    except Exception as e:
        logger.error(f"Error processing rpc.analyze: {e}")
        error_result = AnalysisResult(
            frame_id="unknown",
            source_id="unknown",
            description=f"Analysis error: {str(e)[:200]}",
            severity=0,
            is_alert=False,
            tags=["error"],
        )
        await msg.respond(error_result.model_dump_json().encode())


async def run():
    """Main service loop — connect to NATS and process analysis requests."""
    nc = await nats.connect(config.nats.url)
    logger.info("Analyzer service connected to NATS")

    await nc.subscribe("rpc.analyze", cb=handle_rpc_analyze)
    logger.info("Subscribed to rpc.analyze")

    await shutdown_event.wait()
    await nc.close()
    logger.info("Analyzer service shut down")


def handle_signal():
    shutdown_event.set()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    loop.run_until_complete(run())

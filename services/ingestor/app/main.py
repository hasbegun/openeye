"""OpenEye Ingestor Service — Video/webcam frame extraction and publishing."""

import asyncio
import signal
import logging

import nats

from shared.config import ServiceConfig
from shared.schemas import FrameMessage
from app.capture import capture_frames

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestor")

config = ServiceConfig()
shutdown_event = asyncio.Event()


async def ingest_source(source: str, js):
    """Capture frames from a source and publish to NATS."""
    source_id = f"ingestor-{source.replace('/', '_').replace(':', '_')}"
    frame_count = 0

    async for frame_id, image_b64 in capture_frames(source, config.ingestor, shutdown_event):
        frame_msg = FrameMessage(
            frame_id=frame_id,
            source_id=source_id,
            source_type="rtsp" if source.startswith("rtsp") else "device",
            image_base64=image_b64,
        )

        try:
            await js.publish("frames.new", frame_msg.model_dump_json().encode())
            frame_count += 1
            if frame_count % 10 == 0:
                logger.info(f"Published {frame_count} frames from {source_id}")
        except Exception as e:
            logger.error(f"Failed to publish frame from {source_id}: {e}")


async def run():
    """Main service loop — connect to NATS and start capture tasks."""
    nc = await nats.connect(config.nats.url)
    js = nc.jetstream()
    logger.info("Ingestor service connected to NATS")

    sources = config.ingestor.source_list
    if not sources:
        logger.warning("No sources configured (set INGESTOR_SOURCES env var). Waiting...")
        await shutdown_event.wait()
        await nc.close()
        return

    logger.info(f"Starting capture for {len(sources)} source(s): {sources}")

    tasks = []
    for source in sources:
        task = asyncio.create_task(ingest_source(source, js))
        tasks.append(task)

    await shutdown_event.wait()

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    await nc.close()
    logger.info("Ingestor service shut down")


def handle_signal():
    shutdown_event.set()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    loop.run_until_complete(run())

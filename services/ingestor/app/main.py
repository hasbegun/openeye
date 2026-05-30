"""OpenEye Ingestor Service — Video file processing and frame extraction."""

import asyncio
import signal
import logging

import nats

from shared.config import ServiceConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestor")

config = ServiceConfig()
shutdown_event = asyncio.Event()


async def run():
    """Main service loop — connect to NATS."""
    nc = await nats.connect(config.nats.url)
    js = nc.jetstream()
    logger.info("Ingestor service connected to NATS")

    # Placeholder: video file processing will be implemented in Phase 4

    await shutdown_event.wait()
    await nc.close()
    logger.info("Ingestor service shut down")


def handle_signal():
    shutdown_event.set()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    loop.run_until_complete(run())

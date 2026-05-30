"""OpenEye Guardrails Service — LLM input/output security."""

import asyncio
import signal
import logging

import nats

from shared.config import ServiceConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guardrails")

config = ServiceConfig()
shutdown_event = asyncio.Event()


async def run():
    """Main service loop — connect to NATS and process messages."""
    nc = await nats.connect(config.nats.url)
    js = nc.jetstream()
    logger.info("Guardrails service connected to NATS")

    # Placeholder: subscribe to frames.new and analysis.raw
    # Will be implemented in Phase 3

    await shutdown_event.wait()
    await nc.close()
    logger.info("Guardrails service shut down")


def handle_signal():
    shutdown_event.set()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    loop.run_until_complete(run())

"""OpenEye Alerter Service — Alert filtering and notification delivery."""

import asyncio
import signal
import logging

import nats

from shared.config import ServiceConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alerter")

config = ServiceConfig()
shutdown_event = asyncio.Event()


async def run():
    """Main service loop — connect to NATS and process alerts."""
    nc = await nats.connect(config.nats.url)
    js = nc.jetstream()
    logger.info("Alerter service connected to NATS")

    # Placeholder: subscribe to analysis.results
    # Will be implemented in Phase 5

    await shutdown_event.wait()
    await nc.close()
    logger.info("Alerter service shut down")


def handle_signal():
    shutdown_event.set()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    loop.run_until_complete(run())

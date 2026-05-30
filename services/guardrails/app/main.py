"""OpenEye Guardrails Service — LLM input/output security."""

import asyncio
import json
import signal
import logging
import uuid

import asyncpg
import nats

from shared.config import ServiceConfig
from shared.schemas import FrameMessage, GuardrailViolation
from app.validators import InputValidator, OutputValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guardrails")

config = ServiceConfig()
shutdown_event = asyncio.Event()
db_pool = None
input_validator = InputValidator(config.guardrails)
output_validator = OutputValidator(config.guardrails)


async def init_db():
    """Initialize database connection pool."""
    global db_pool
    db_pool = await asyncpg.create_pool(
        config.database.dsn,
        min_size=1,
        max_size=5,
    )
    logger.info("Database pool created")


async def log_violation(violation: GuardrailViolation):
    """Persist guardrail violation to audit_log."""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (id, frame_id, violation_type, rule, details, action_taken)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                uuid.UUID(violation.violation_id) if len(violation.violation_id) == 36 else uuid.uuid4(),
                violation.frame_id,
                violation.violation_type,
                violation.rule,
                violation.details,
                violation.action_taken,
            )
    except Exception as e:
        logger.error(f"Failed to log violation: {e}")


async def handle_frame(msg):
    """Validate incoming frame and forward if valid."""
    try:
        data = json.loads(msg.data.decode())
        frame = FrameMessage(**data)

        violation = input_validator.validate(frame)
        if violation:
            logger.warning(f"Frame {frame.frame_id} rejected: {violation.rule} - {violation.details}")
            await log_violation(violation)
            await msg.ack()
            return

        # Forward validated frame to frames.validated
        nc = msg._client
        js = nc.jetstream()
        await js.publish("frames.validated", msg.data)
        logger.debug(f"Frame {frame.frame_id} validated and forwarded")
        await msg.ack()
    except Exception as e:
        logger.error(f"Error processing frame: {e}")
        await msg.nak()


async def run():
    """Main service loop — connect to NATS and process messages."""
    await init_db()

    nc = await nats.connect(config.nats.url)
    js = nc.jetstream()
    logger.info("Guardrails service connected to NATS")

    # Retry subscription — streams may not be provisioned yet
    for attempt in range(30):
        try:
            await js.subscribe(
                "frames.new",
                durable="guardrails",
                stream="FRAMES",
                cb=handle_frame,
            )
            logger.info("Subscribed to frames.new (durable=guardrails)")
            break
        except Exception as e:
            if attempt < 29:
                logger.warning(f"Stream not ready (attempt {attempt + 1}/30): {e}")
                await asyncio.sleep(2)
            else:
                raise

    await shutdown_event.wait()
    await nc.close()
    if db_pool:
        await db_pool.close()
    logger.info("Guardrails service shut down")


def handle_signal():
    shutdown_event.set()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    loop.run_until_complete(run())

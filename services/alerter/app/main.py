"""OpenEye Alerter Service — Alert filtering and notification delivery."""

import asyncio
import json
import signal
import logging
import uuid

import asyncpg
import nats

from shared.config import ServiceConfig
from shared.schemas import AnalysisResult, AlertMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alerter")

config = ServiceConfig()
shutdown_event = asyncio.Event()
db_pool = None


async def init_db():
    """Initialize database connection pool."""
    global db_pool
    db_pool = await asyncpg.create_pool(
        config.database.dsn,
        min_size=2,
        max_size=10,
    )
    logger.info("Database pool created")


async def persist_alert(alert: AlertMessage):
    """Save alert to PostgreSQL."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO alerts (id, frame_id, source_id, description, severity, tags, thumbnail_base64, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            uuid.UUID(alert.alert_id),
            alert.frame_id,
            alert.source_id,
            alert.description,
            alert.severity,
            alert.tags,
            alert.thumbnail_base64,
            alert.timestamp,
        )
    logger.info(f"Alert {alert.alert_id} persisted (severity={alert.severity})")


async def handle_analysis_result(msg):
    """Process analysis results — create alerts for high-severity events."""
    try:
        data = json.loads(msg.data.decode())
        result = AnalysisResult(**data)

        if result.severity >= config.alert.severity_threshold:
            alert = AlertMessage(
                alert_id=str(uuid.uuid4()),
                frame_id=result.frame_id,
                source_id=result.source_id,
                description=result.description,
                severity=result.severity,
                tags=result.tags,
            )

            await persist_alert(alert)

            # Publish to alerts.new for WebSocket delivery
            nc = msg._client
            js = nc.jetstream()
            await js.publish("alerts.new", alert.model_dump_json().encode())
            logger.info(f"Alert published: {alert.alert_id}")
        else:
            logger.debug(f"Frame {result.frame_id} below threshold (severity={result.severity})")

        await msg.ack()
    except Exception as e:
        logger.error(f"Error processing analysis result: {e}")
        await msg.nak()


async def run():
    """Main service loop — connect to NATS and process alerts."""
    await init_db()

    nc = await nats.connect(config.nats.url)
    js = nc.jetstream()
    logger.info("Alerter service connected to NATS")

    # Retry subscription — streams may not be provisioned yet
    for attempt in range(30):
        try:
            await js.subscribe(
                "analysis.results",
                durable="alerter",
                stream="ANALYSIS",
                cb=handle_analysis_result,
            )
            logger.info("Subscribed to analysis.results (durable=alerter)")
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
    logger.info("Alerter service shut down")


def handle_signal():
    shutdown_event.set()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    loop.run_until_complete(run())

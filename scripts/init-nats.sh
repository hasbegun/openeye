#!/bin/sh
# Initialize NATS JetStream streams and consumers for OpenEye.
# Runs as an init container after NATS is healthy.

set -e

NATS_URL="${NATS_URL:-nats://nats:4222}"

echo "Initializing NATS JetStream streams..."

# FRAMES stream — holds frame messages for processing
nats -s "$NATS_URL" stream add FRAMES \
  --subjects "frames.new,frames.validated" \
  --retention limits \
  --max-msgs 10000 \
  --max-bytes 1073741824 \
  --max-age 1h \
  --storage file \
  --replicas 1 \
  --discard old \
  --dupe-window 30s \
  --defaults 2>/dev/null || \
nats -s "$NATS_URL" stream update FRAMES \
  --subjects "frames.new,frames.validated" \
  --max-msgs 10000 \
  --max-bytes 1073741824 \
  --max-age 1h 2>/dev/null || true

# ANALYSIS stream — holds analysis results
nats -s "$NATS_URL" stream add ANALYSIS \
  --subjects "analysis.raw,analysis.results" \
  --retention limits \
  --max-msgs 10000 \
  --max-bytes 536870912 \
  --max-age 2h \
  --storage file \
  --replicas 1 \
  --discard old \
  --dupe-window 30s \
  --defaults 2>/dev/null || \
nats -s "$NATS_URL" stream update ANALYSIS \
  --subjects "analysis.raw,analysis.results" \
  --max-msgs 10000 \
  --max-bytes 536870912 \
  --max-age 2h 2>/dev/null || true

# ALERTS stream — holds alert notifications
nats -s "$NATS_URL" stream add ALERTS \
  --subjects "alerts.new" \
  --retention limits \
  --max-msgs 5000 \
  --max-bytes 268435456 \
  --max-age 24h \
  --storage file \
  --replicas 1 \
  --discard old \
  --dupe-window 60s \
  --defaults 2>/dev/null || \
nats -s "$NATS_URL" stream update ALERTS \
  --subjects "alerts.new" \
  --max-msgs 5000 \
  --max-bytes 268435456 \
  --max-age 24h 2>/dev/null || true

# --- Consumers ---

# Guardrails consumes frames.new
nats -s "$NATS_URL" consumer add FRAMES guardrails-input \
  --filter "frames.new" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --wait 30s \
  --defaults 2>/dev/null || true

# Analyzer consumes frames.validated
nats -s "$NATS_URL" consumer add FRAMES analyzer \
  --filter "frames.validated" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --wait 30s \
  --defaults 2>/dev/null || true

# Guardrails consumes analysis.raw
nats -s "$NATS_URL" consumer add ANALYSIS guardrails-output \
  --filter "analysis.raw" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --wait 30s \
  --defaults 2>/dev/null || true

# Alerter consumes analysis.results
nats -s "$NATS_URL" consumer add ANALYSIS alerter \
  --filter "analysis.results" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --wait 30s \
  --defaults 2>/dev/null || true

# Gateway consumes alerts.new (for WebSocket push)
nats -s "$NATS_URL" consumer add ALERTS gateway \
  --filter "alerts.new" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --wait 30s \
  --defaults 2>/dev/null || true

echo "NATS JetStream initialization complete."
echo "Streams:"
nats -s "$NATS_URL" stream ls

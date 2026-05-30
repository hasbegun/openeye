-- OpenEye initial schema

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    frame_id VARCHAR(255) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity INTEGER NOT NULL CHECK (severity >= 0 AND severity <= 10),
    tags TEXT[] DEFAULT '{}',
    thumbnail_base64 TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);
CREATE INDEX IF NOT EXISTS idx_alerts_source_id ON alerts (source_id);

-- Audit log for guardrail violations
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    frame_id VARCHAR(255),
    violation_type VARCHAR(50) NOT NULL,
    rule VARCHAR(255) NOT NULL,
    details TEXT NOT NULL,
    action_taken VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_violation_type ON audit_log (violation_type);

-- Configuration store
CREATE TABLE IF NOT EXISTS config (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert default config
INSERT INTO config (key, value) VALUES
    ('alert_threshold', '{"severity": 6}'),
    ('frame_rate', '{"fps": 1.0}'),
    ('webhooks', '{"urls": []}'),
    ('model', '{"provider": "ollama", "model": "llava"}')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY,
    actor_id UUID REFERENCES users (id),
    actor_email VARCHAR(255) NOT NULL DEFAULT '',
    actor_role VARCHAR(40) NOT NULL DEFAULT '',
    action VARCHAR(40) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id VARCHAR(64) NOT NULL DEFAULT '',
    summary VARCHAR(500) NOT NULL DEFAULT '',
    before_json TEXT NOT NULL DEFAULT '',
    after_json TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs (actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_entity_type ON audit_logs (entity_type);

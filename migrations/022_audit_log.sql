-- FASE 12: Audit Trail — persiste react_steps por sessão
-- Idempotente: usa IF NOT EXISTS

CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL,
    agent       VARCHAR(100) NOT NULL DEFAULT 'optimus',
    step_type   VARCHAR(50)  NOT NULL,  -- 'reason' | 'act' | 'observe' | 'summary'
    tool_name   VARCHAR(100) DEFAULT '',
    content     TEXT         NOT NULL DEFAULT '',
    success     BOOLEAN      DEFAULT TRUE,
    duration_ms FLOAT        DEFAULT 0,
    iteration   INTEGER      DEFAULT 0,
    created_at  TIMESTAMPTZ  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_session_id ON audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

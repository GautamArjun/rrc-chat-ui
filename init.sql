-- Session storage for serverless deployment
-- Run this after rrc_pilot_leads.sql

CREATE TABLE IF NOT EXISTS rrc_sessions (
  session_id    VARCHAR(36) PRIMARY KEY,
  study_id      VARCHAR(40) NOT NULL,
  state         JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rrc_sessions_updated ON rrc_sessions(updated_at);

-- Optional: Clean up old sessions (run periodically)
-- DELETE FROM rrc_sessions WHERE updated_at < NOW() - INTERVAL '24 hours';

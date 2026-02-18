-- FASE 1: User Preferences + Onboarding
-- Stores per-user customization: preferred name, language, agent name, style

-- Add onboarding flag to users
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS has_completed_onboarding BOOLEAN DEFAULT FALSE;

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferred_name VARCHAR(100) DEFAULT '',         -- How user wants to be called
    agent_name VARCHAR(100) DEFAULT 'Optimus',      -- What user calls the agent
    language VARCHAR(10) DEFAULT 'pt-BR',           -- Preferred language (pt-BR, en, es)
    communication_style VARCHAR(20) DEFAULT 'casual', -- casual | formal | technical
    timezone VARCHAR(50) DEFAULT 'America/Sao_Paulo',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

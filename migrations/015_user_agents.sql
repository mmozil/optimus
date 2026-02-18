-- FASE 3: User-Created Dynamic Agents
-- Stores custom agents created by users with their own SOUL.md

CREATE TABLE IF NOT EXISTS user_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_slug VARCHAR(60) NOT NULL UNIQUE,      -- URL-safe key used for routing (e.g. "codereview-a1b2")
    display_name VARCHAR(100) NOT NULL,           -- Human name shown in UI
    role VARCHAR(100) NOT NULL DEFAULT 'Specialist',
    soul_md TEXT NOT NULL DEFAULT '',             -- Full SOUL.md content
    model VARCHAR(50) NOT NULL DEFAULT 'gemini-2.5-flash',
    temperature FLOAT NOT NULL DEFAULT 0.7,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_agents_user_id ON user_agents(user_id);
CREATE INDEX IF NOT EXISTS idx_user_agents_slug ON user_agents(agent_slug);

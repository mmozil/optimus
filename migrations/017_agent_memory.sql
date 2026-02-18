-- FASE 6: Agent Memory Sync to DB
-- Persists WORKING.md and MEMORY.md to PostgreSQL.
-- Enables: multi-worker consistency, container-restart recovery, cross-agent queries.

-- Working Memory: one row per agent (full WORKING.md content)
CREATE TABLE IF NOT EXISTS agent_working_memory (
    agent_name VARCHAR(100) PRIMARY KEY,
    content TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Long-Term Memory: one row per learning entry
CREATE TABLE IF NOT EXISTS agent_long_term_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(100) NOT NULL,
    category VARCHAR(200) NOT NULL,
    learning TEXT NOT NULL,
    source VARCHAR(500) DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lt_memory_agent ON agent_long_term_memory(agent_name);
CREATE INDEX IF NOT EXISTS idx_lt_memory_category ON agent_long_term_memory(agent_name, category);

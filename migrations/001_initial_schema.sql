-- ============================================
-- Agent Optimus — Database Schema
-- Single migration file for initial setup
-- ============================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 1. AGENTS
-- ============================================
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    role VARCHAR(100) NOT NULL,
    soul_md TEXT,
    status VARCHAR(20) DEFAULT 'idle',
    level VARCHAR(20) DEFAULT 'specialist',
    current_task_id UUID,
    model_config JSONB DEFAULT '{}',
    last_heartbeat TIMESTAMPTZ,
    learning_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 2. TASKS
-- ============================================
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'inbox',
    priority VARCHAR(10) DEFAULT 'medium',
    parent_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    assignee_ids UUID[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    due_date TIMESTAMPTZ,
    estimated_effort VARCHAR(20),
    created_by UUID REFERENCES agents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Add FK from agents to tasks (circular dependency resolved)
-- ALTER TABLE agents
--    ADD CONSTRAINT fk_agents_current_task
--    FOREIGN KEY (current_task_id) REFERENCES tasks(id) ON DELETE SET NULL;

-- ============================================
-- 3. MESSAGES (comments on tasks)
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE NOT NULL,
    from_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL NOT NULL,
    content TEXT NOT NULL,
    attachments UUID[] DEFAULT '{}',
    mentions UUID[] DEFAULT '{}',
    confidence_score FLOAT,
    thinking_mode VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 4. ACTIVITIES (event log)
-- ============================================
CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 5. DOCUMENTS
-- ============================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(30),
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    created_by UUID REFERENCES agents(id) ON DELETE SET NULL,
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 6. NOTIFICATIONS
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mentioned_agent_id UUID REFERENCES agents(id) ON DELETE CASCADE NOT NULL,
    source_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    delivered BOOLEAN DEFAULT false,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 7. THREAD SUBSCRIPTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS thread_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE NOT NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE NOT NULL,
    subscribed_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(agent_id, task_id)
);

-- ============================================
-- 8. EMBEDDINGS (RAG + Semantic Memory)
-- ============================================
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768),
    source_type VARCHAR(30),
    source_id VARCHAR(255),
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- ============================================
-- 9. ERROR PATTERNS (UncertaintyQuantifier)
-- ============================================
CREATE TABLE IF NOT EXISTS error_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_text TEXT NOT NULL,
    pattern_embedding vector(768),
    error_type VARCHAR(50),
    frequency INT DEFAULT 1,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assignees ON tasks USING GIN(assignee_ids);
CREATE INDEX IF NOT EXISTS idx_messages_task ON messages(task_id);
CREATE INDEX IF NOT EXISTS idx_activities_agent ON activities(agent_id);
CREATE INDEX IF NOT EXISTS idx_activities_created ON activities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_agent ON notifications(mentioned_agent_id, delivered);
CREATE INDEX IF NOT EXISTS idx_embeddings_source ON embeddings(source_type, source_id);

-- ============================================
-- SEED: Initial Agents
-- ============================================
INSERT INTO agents (name, role, level, model_config, soul_md) VALUES
    ('optimus', 'Lead Orchestrator', 'lead',
     '{"model": "gemini-2.5-pro", "max_tokens": 8192, "temperature": 0.7}',
     'Orquestrador principal. Delega tarefas, monitora progresso, sintetiza resultados.'),
    ('friday', 'Developer', 'specialist',
     '{"model": "gemini-2.5-flash", "max_tokens": 4096, "temperature": 0.3}',
     'Desenvolvedor pragmático. Código limpo, testes sempre, entrega rápida.'),
    ('fury', 'Researcher', 'specialist',
     '{"model": "gemini-2.5-flash", "max_tokens": 4096, "temperature": 0.5}',
     'Pesquisador meticuloso. Evidências primeiro, opiniões fundamentadas.')
ON CONFLICT (name) DO NOTHING;

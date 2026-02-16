-- Migration: Knowledge Base (Phase 17)
-- Adds file tracking and hybrid search capabilities for RAG.

-- 1. Knowledge Files: tracks original documents uploaded to the KB
CREATE TABLE IF NOT EXISTS knowledge_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    content_hash VARCHAR(64), -- SHA-256 to prevent duplicates
    chunk_count INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'processing', -- processing, active, error
    error_message TEXT,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Add Full-Text Search index to embeddings table (Hybrid Search)
-- We use 'portuguese' configuration since the primary language is PT-BR
ALTER TABLE embeddings
    ADD COLUMN IF NOT EXISTS ts_content tsvector
    GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED;

CREATE INDEX IF NOT EXISTS idx_embeddings_ts_content ON embeddings USING GIN(ts_content);

-- 3. Add chunk_index to embeddings for ordered retrieval
ALTER TABLE embeddings
    ADD COLUMN IF NOT EXISTS chunk_index INT DEFAULT 0;

-- 4. Add knowledge_file_id FK to embeddings
ALTER TABLE embeddings
    ADD COLUMN IF NOT EXISTS knowledge_file_id UUID REFERENCES knowledge_files(id) ON DELETE CASCADE;

-- 5. Indexes for fast filtering
CREATE INDEX IF NOT EXISTS idx_knowledge_files_hash ON knowledge_files(content_hash);
CREATE INDEX IF NOT EXISTS idx_embeddings_knowledge_file ON embeddings(knowledge_file_id);

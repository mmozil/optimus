-- FASE 14: Temporal Memory & Decay
-- Adiciona colunas de acesso e arquivamento na tabela embeddings
-- Idempotente: usa IF NOT EXISTS / IF EXISTS

ALTER TABLE embeddings
    ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS access_count      INTEGER     DEFAULT 0,
    ADD COLUMN IF NOT EXISTS archived          BOOLEAN     DEFAULT FALSE;

-- Índice para cron de archiving (busca entradas não arquivadas + velhas)
CREATE INDEX IF NOT EXISTS idx_embeddings_decay
    ON embeddings(archived, last_accessed_at, access_count);

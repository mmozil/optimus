-- 009_files.sql
-- Tabela para metadados de arquivos e anexos

CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    storage_path TEXT NOT NULL,  -- Caminho no bucket (ex: user_123/img.png)
    filename TEXT NOT NULL,      -- Nome original do arquivo
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    public_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_conversation_id ON files(conversation_id);
CREATE INDEX IF NOT EXISTS idx_files_mime_type ON files(mime_type);

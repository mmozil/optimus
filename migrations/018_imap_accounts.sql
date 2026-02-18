-- FASE 4C: IMAP/SMTP Universal Email Accounts
-- Stores IMAP/SMTP credentials for any email provider per user.
-- Covers: Outlook, Office 365, Yahoo, corporate (Locaweb, Hostgator, etc.) and custom IMAP servers.
-- Passwords are encrypted at application level (Fernet + JWT_SECRET derived key).

CREATE TABLE IF NOT EXISTS imap_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    provider VARCHAR(50) DEFAULT 'custom',     -- outlook | office365 | yahoo | gmail | locaweb | custom
    imap_host VARCHAR(255) NOT NULL,
    imap_port INTEGER DEFAULT 993,
    smtp_host VARCHAR(255) NOT NULL,
    smtp_port INTEGER DEFAULT 587,
    username VARCHAR(255) NOT NULL,            -- usually same as email, but can differ (Exchange)
    password_encrypted TEXT NOT NULL,          -- Fernet encrypted
    use_ssl BOOLEAN DEFAULT TRUE,              -- IMAP: SSL on port 993
    use_tls BOOLEAN DEFAULT TRUE,              -- SMTP: STARTTLS on port 587
    display_name VARCHAR(255) DEFAULT '',      -- friendly name shown in UI
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, email)
);

CREATE INDEX IF NOT EXISTS idx_imap_accounts_user_id ON imap_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_imap_accounts_active ON imap_accounts(user_id, is_active);

-- FASE 8: Apple iCloud Credentials
-- Stores Apple ID + App-Specific Password for CalDAV (Calendar, Reminders) and CardDAV (Contacts).
-- iCloud Mail is handled separately by imap_accounts (FASE 4C).
-- App-Specific Password: generate at https://appleid.apple.com → Security → App-Specific Passwords
-- Passwords encrypted at application level (Fernet + JWT_SECRET derived key).

CREATE TABLE IF NOT EXISTS apple_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    apple_id VARCHAR(255) NOT NULL,              -- Apple ID email (e.g. user@icloud.com)
    app_password_encrypted TEXT NOT NULL,        -- Fernet encrypted App-Specific Password
    display_name VARCHAR(100) DEFAULT '',        -- friendly label (optional)
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)                              -- one Apple account per user
);

CREATE INDEX IF NOT EXISTS idx_apple_credentials_user_id ON apple_credentials(user_id);

-- FASE Vivaldi #1: TTS mode per user
-- tts_mode: 'off' | 'always' | 'on_request'
ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS tts_mode VARCHAR(20) DEFAULT 'off',
    ADD COLUMN IF NOT EXISTS tts_voice VARCHAR(100) DEFAULT 'pt-BR-AntonioNeural',
    ADD COLUMN IF NOT EXISTS tts_speed FLOAT DEFAULT 1.0;
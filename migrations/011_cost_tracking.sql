-- Migration: Cost Tracking (Phase 16)
-- Tracks token usage and costs per tenant, enforcing budgets.

-- 1. Cost Entries: individual request costs
CREATE TABLE IF NOT EXISTS cost_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    agent_name VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    cost_usd NUMERIC(10, 6) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_cost_entries_user_id ON cost_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_cost_entries_created_at ON cost_entries(created_at);

-- 2. User Budgets: spending limits per tenant
CREATE TABLE IF NOT EXISTS user_budgets (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    daily_limit_usd NUMERIC(10, 2) DEFAULT 10.00,
    monthly_limit_usd NUMERIC(10, 2) DEFAULT 200.00,
    current_day_spend NUMERIC(10, 6) DEFAULT 0,
    current_month_spend NUMERIC(10, 6) DEFAULT 0,
    last_reset_day DATE DEFAULT CURRENT_DATE,
    last_reset_month DATE DEFAULT CURRENT_DATE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 3. Function to update spending aggregates (could be trigger, but app-level for now)

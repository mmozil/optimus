-- Migration 021: Remove predefined system agents (friday, fury).
-- Only Optimus is kept as the default agent.
-- Users create specialized agents as needed via the Agents page.
-- analyst, writer, guardian were never seeded in the DB (only in-memory), so no DELETE needed.

DELETE FROM agents WHERE name IN ('friday', 'fury');

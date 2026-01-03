-- Migration: 001_initial_schema
-- Description: Initial database schema for tasks table

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    thread_id INTEGER,
    title TEXT NOT NULL,
    details TEXT,
    assignee TEXT,
    deadline DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_chat_thread ON tasks(chat_id, thread_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee) WHERE assignee IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline) WHERE deadline IS NOT NULL;

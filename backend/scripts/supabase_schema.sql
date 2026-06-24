-- Life OS — initial schema for Supabase SQL Editor
-- Safe to re-run (IF NOT EXISTS). Reading module is the core.

CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    total_pages INTEGER NOT NULL,
    current_page INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'READING',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    cover_url VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reading_logs (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    pages_read INTEGER NOT NULL,
    log_date DATE NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    due_date TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'TODO',
    is_sla_critical BOOLEAN NOT NULL DEFAULT FALSE,
    google_event_id VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS job_applications (
    id SERIAL PRIMARY KEY,
    company VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    status VARCHAR(64) NOT NULL,
    tech_stack VARCHAR(512),
    notes TEXT,
    applied_date DATE
);

CREATE TABLE IF NOT EXISTS fitness_logs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(32) NOT NULL,
    activity_type VARCHAR(32) NOT NULL,
    duration_minutes INTEGER NOT NULL,
    date DATE NOT NULL,
    streak_impact BOOLEAN NOT NULL DEFAULT TRUE
);

-- Legacy table (unused by spec; kept for backward compatibility with existing code)
CREATE TABLE IF NOT EXISTS learning_progress (
    id SERIAL PRIMARY KEY,
    resource_type VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    total_units INTEGER NOT NULL DEFAULT 0,
    completed_units INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(64) NOT NULL DEFAULT 'IN_PROGRESS'
);

CREATE INDEX IF NOT EXISTS idx_reading_logs_book_id ON reading_logs(book_id);
CREATE INDEX IF NOT EXISTS idx_reading_logs_log_date ON reading_logs(log_date);
CREATE INDEX IF NOT EXISTS idx_books_is_active ON books(is_active) WHERE is_active = TRUE;

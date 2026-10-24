CREATE TABLE IF NOT EXISTS task_time_entries (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    source timeentrysource NOT NULL,
    manual_reason VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_time_entries_one_running
    ON task_time_entries (employee_id)
    WHERE end_time IS NULL;

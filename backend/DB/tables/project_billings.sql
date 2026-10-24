CREATE TABLE IF NOT EXISTS project_billings (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    entered_by_id UUID REFERENCES users (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, year, month)
);
CREATE INDEX IF NOT EXISTS ix_project_billings_project_id ON project_billings (project_id);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority taskpriority NOT NULL,
    estimated_hours NUMERIC(10, 2) NOT NULL DEFAULT 0,
    due_date DATE,
    assignee_id UUID REFERENCES employees (id),
    status taskstatus NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

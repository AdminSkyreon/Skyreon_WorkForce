CREATE TABLE IF NOT EXISTS timesheet_weeks (
    id UUID PRIMARY KEY,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    status timesheetstatus NOT NULL,
    reviewer_id UUID REFERENCES employees (id),
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_timesheet_week UNIQUE (employee_id, week_start)
);

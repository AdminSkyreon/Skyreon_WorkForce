DO $$ BEGIN CREATE TYPE reimbursementstatus AS ENUM ('submitted', 'approved', 'rejected', 'cancelled'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
CREATE TABLE IF NOT EXISTS reimbursements (
    id UUID PRIMARY KEY,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects (id),
    amount NUMERIC(12, 2) NOT NULL,
    category VARCHAR(40) NOT NULL DEFAULT 'other',
    spend_date DATE NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    status reimbursementstatus NOT NULL,
    reviewer_id UUID REFERENCES employees (id),
    comment TEXT NOT NULL DEFAULT '',
    payroll_year INTEGER,
    payroll_month INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_reimbursements_employee_id ON reimbursements (employee_id);
CREATE INDEX IF NOT EXISTS ix_reimbursements_project_id ON reimbursements (project_id);

CREATE TABLE IF NOT EXISTS payroll_adjustments (
    id UUID PRIMARY KEY,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    bonus NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (employee_id, year, month)
);
CREATE INDEX IF NOT EXISTS ix_payroll_adjustments_employee_id ON payroll_adjustments (employee_id);

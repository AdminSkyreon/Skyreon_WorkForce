CREATE TABLE IF NOT EXISTS employee_payroll (
    id UUID PRIMARY KEY,
    employee_id UUID NOT NULL UNIQUE REFERENCES employees (id) ON DELETE CASCADE,
    currency VARCHAR(8) NOT NULL DEFAULT 'INR',
    basic_salary NUMERIC(12, 2) NOT NULL DEFAULT 0,
    hra NUMERIC(12, 2) NOT NULL DEFAULT 0,
    allowances NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    pf_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    professional_tax NUMERIC(12, 2) NOT NULL DEFAULT 0,
    other_deductions NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_employee_payroll_employee_id ON employee_payroll (employee_id);

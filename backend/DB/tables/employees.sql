CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    employee_code VARCHAR(50) NOT NULL UNIQUE,
    designation VARCHAR(120) NOT NULL,
    department VARCHAR(120) NOT NULL,
    joining_date DATE NOT NULL,
    reporting_manager_id UUID REFERENCES employees (id),
    location_id UUID REFERENCES locations (id),
    hourly_cost_rate NUMERIC(12, 2) NOT NULL DEFAULT 0,
    status employeestatus NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_employees_location_id ON employees (location_id);

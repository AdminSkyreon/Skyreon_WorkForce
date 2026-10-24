CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    project_code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    manager_id UUID NOT NULL REFERENCES employees (id),
    start_date DATE NOT NULL,
    end_date DATE,
    status projectstatus NOT NULL,
    contract_type contracttype NOT NULL,
    revenue_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    revenue_currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    budgeted_hours NUMERIC(10, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

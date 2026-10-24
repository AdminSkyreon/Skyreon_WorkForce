DO $$ BEGIN CREATE TYPE engagement AS ENUM ('staff', 'contractor'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE vendorcategory AS ENUM ('gst_filing', 'ca_audit', 'legal', 'rent_office', 'tools', 'other'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE billstatus AS ENUM ('draft', 'approved', 'paid'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE applicantstage AS ENUM ('applied', 'interview', 'offer', 'joined', 'rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE attendancemark AS ENUM ('present', 'work_from', 'leave', 'absent'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE assetstatus AS ENUM ('available', 'assigned', 'returned', 'lost'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE employees ADD COLUMN IF NOT EXISTS phone VARCHAR(80) NOT NULL DEFAULT '';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS address TEXT NOT NULL DEFAULT '';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS engagement engagement NOT NULL DEFAULT 'staff';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS allow_leave BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS contract_monthly_fee NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE reimbursements ADD COLUMN IF NOT EXISTS paid_separately BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE reimbursements ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS project_payments (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    received_date DATE NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    entered_by_id UUID REFERENCES users (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_project_payments_project_id ON project_payments (project_id);

CREATE TABLE IF NOT EXISTS salary_payments (
    id UUID PRIMARY KEY,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    paid_date DATE NOT NULL,
    reference VARCHAR(80) NOT NULL DEFAULT '',
    marked_by_id UUID REFERENCES users (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (employee_id, year, month)
);

CREATE TABLE IF NOT EXISTS contractor_payments (
    id UUID PRIMARY KEY,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    calculated NUMERIC(12, 2) NOT NULL DEFAULT 0,
    amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    paid_date DATE,
    reference VARCHAR(80) NOT NULL DEFAULT '',
    deduction NUMERIC(12, 2) NOT NULL DEFAULT 0,
    marked_by_id UUID REFERENCES users (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (employee_id, year, month)
);

CREATE TABLE IF NOT EXISTS vendor_bills (
    id UUID PRIMARY KEY,
    vendor_name VARCHAR(255) NOT NULL,
    category vendorcategory NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    gst_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    bill_date DATE NOT NULL,
    paid_date DATE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    project_id UUID REFERENCES projects (id),
    note TEXT NOT NULL DEFAULT '',
    recurring BOOLEAN NOT NULL DEFAULT FALSE,
    status billstatus NOT NULL DEFAULT 'approved',
    entered_by_id UUID REFERENCES users (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    department VARCHAR(120) NOT NULL DEFAULT '',
    location_id UUID REFERENCES locations (id),
    hiring_manager_id UUID REFERENCES employees (id),
    is_open BOOLEAN NOT NULL DEFAULT TRUE,
    opened_on DATE NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS applicants (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    stage applicantstage NOT NULL DEFAULT 'applied',
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_requirements (
    id UUID PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS employee_documents (
    id UUID PRIMARY KEY,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    requirement_id UUID NOT NULL REFERENCES document_requirements (id) ON DELETE CASCADE,
    provided BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (employee_id, requirement_id)
);

CREATE TABLE IF NOT EXISTS attendance_days (
    id UUID PRIMARY KEY,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    mark attendancemark NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (employee_id, work_date)
);

CREATE TABLE IF NOT EXISTS review_cycles (
    id UUID PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_open BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS performance_reviews (
    id UUID PRIMARY KEY,
    cycle_id UUID NOT NULL REFERENCES review_cycles (id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    manager_id UUID REFERENCES employees (id),
    summary TEXT NOT NULL DEFAULT '',
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cycle_id, employee_id)
);

CREATE TABLE IF NOT EXISTS company_assets (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    asset_tag VARCHAR(80) NOT NULL UNIQUE,
    category VARCHAR(40) NOT NULL DEFAULT 'laptop',
    status assetstatus NOT NULL DEFAULT 'available',
    assigned_to_id UUID REFERENCES employees (id),
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

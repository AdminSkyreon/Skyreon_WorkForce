-- common.sql — every table and every script, in run order.
-- Paste this one file in the Supabase SQL Editor, or run the files under tables/ then scripts/.

-- ===== tables/00_types.sql =====
-- Enums used by the tables
DO $$ BEGIN CREATE TYPE userrole AS ENUM ('admin', 'employee'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE employeestatus AS ENUM ('active', 'inactive'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE projectstatus AS ENUM ('planned', 'active', 'on_hold', 'completed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE contracttype AS ENUM ('fixed', 'time_and_material'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE taskpriority AS ENUM ('low', 'medium', 'high'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE taskstatus AS ENUM ('not_started', 'in_progress', 'paused', 'completed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE timeentrysource AS ENUM ('timer', 'manual'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE timesheetstatus AS ENUM ('draft', 'submitted', 'approved', 'rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE leavestatus AS ENUM ('pending', 'approved', 'rejected', 'cancelled'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ===== tables/users.sql =====
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    role userrole NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    must_change_password BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- ===== tables/refresh_tokens.sql =====
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    replaced_by_id UUID REFERENCES refresh_tokens (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id);

-- ===== tables/locations.sql =====
CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    city VARCHAR(120) NOT NULL DEFAULT '',
    country VARCHAR(120) NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_locations_code ON locations (code);

-- ===== tables/employees.sql =====
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

-- ===== tables/employee_payroll.sql =====
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

-- ===== tables/projects.sql =====
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

-- ===== tables/project_members.sql =====
CREATE TABLE IF NOT EXISTS project_members (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_project_member UNIQUE (project_id, employee_id)
);

-- ===== tables/tasks.sql =====
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

-- ===== tables/task_time_entries.sql =====
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

-- ===== tables/timesheet_weeks.sql =====
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

-- ===== tables/holidays.sql =====
CREATE TABLE IF NOT EXISTS holidays (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    location_id UUID REFERENCES locations (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_holidays_location_id ON holidays (location_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_holiday_company_date ON holidays (date) WHERE location_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_holiday_location_date ON holidays (location_id, date) WHERE location_id IS NOT NULL;

-- ===== tables/leave_types.sql =====
CREATE TABLE IF NOT EXISTS leave_types (
    id UUID PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    annual_allocation_days INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===== tables/leave_requests.sql =====
CREATE TABLE IF NOT EXISTS leave_requests (
    id UUID PRIMARY KEY,
    employee_id UUID NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    leave_type_id UUID NOT NULL REFERENCES leave_types (id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_half_day BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT NOT NULL DEFAULT '',
    status leavestatus NOT NULL,
    reviewer_id UUID REFERENCES employees (id),
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===== tables/notifications.sql =====
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    type VARCHAR(80) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    link VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===== scripts/seed_leave_types.sql =====
INSERT INTO leave_types (id, name, code, annual_allocation_days)
VALUES
    (gen_random_uuid(), 'Casual Leave', 'CL', 12),
    (gen_random_uuid(), 'Sick Leave', 'SL', 10),
    (gen_random_uuid(), 'Earned Leave', 'EL', 15),
    (gen_random_uuid(), 'Leave Without Pay', 'LWP', 0)
ON CONFLICT (code) DO NOTHING;

-- ===== tables/reimbursements.sql =====
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

-- ===== tables/project_billings.sql =====
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

-- ===== tables/payroll_periods.sql =====
DO $$ BEGIN CREATE TYPE payrollperiodstatus AS ENUM ('open', 'closed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
CREATE TABLE IF NOT EXISTS payroll_periods (
    id UUID PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    status payrollperiodstatus NOT NULL,
    closed_by_id UUID REFERENCES users (id),
    closed_at TIMESTAMPTZ,
    snapshot_json TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (year, month)
);

-- ===== tables/payroll_adjustments.sql =====
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

-- ===== tables/company_profile.sql =====
CREATE TABLE IF NOT EXISTS company_profile (
    id UUID PRIMARY KEY,
    legal_name VARCHAR(255) NOT NULL DEFAULT 'Skyreon',
    address TEXT NOT NULL DEFAULT '',
    phone VARCHAR(80) NOT NULL DEFAULT '',
    website VARCHAR(255) NOT NULL DEFAULT 'https://www.skyreon.com',
    signatory_name VARCHAR(255) NOT NULL DEFAULT '',
    signatory_title VARCHAR(120) NOT NULL DEFAULT '',
    signature_image TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===== tables/audit_logs.sql =====
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY,
    actor_id UUID REFERENCES users (id),
    actor_email VARCHAR(255) NOT NULL DEFAULT '',
    actor_role VARCHAR(40) NOT NULL DEFAULT '',
    action VARCHAR(40) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id VARCHAR(64) NOT NULL DEFAULT '',
    summary VARCHAR(500) NOT NULL DEFAULT '',
    before_json TEXT NOT NULL DEFAULT '',
    after_json TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===== scripts/seed_locations.sql =====
INSERT INTO locations (id, name, code, city, country, is_active)
VALUES
    (gen_random_uuid(), 'Bhubaneswar', 'BBS', 'Bhubaneswar', 'India', TRUE),
    (gen_random_uuid(), 'Bengaluru', 'BLR', 'Bengaluru', 'India', TRUE),
    (gen_random_uuid(), 'Remote', 'REM', 'Remote', 'Global', TRUE)
ON CONFLICT (code) DO NOTHING;

-- ===== tables/hrms.sql =====
DO $$ BEGIN CREATE TYPE engagement AS ENUM ('staff', 'contractor'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE vendorcategory AS ENUM ('gst_filing', 'ca_audit', 'legal', 'rent_office', 'tools', 'other'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE billstatus AS ENUM ('draft', 'approved', 'paid'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE applicantstage AS ENUM ('applied', 'interview', 'offer', 'joined', 'rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE attendancemark AS ENUM ('present', 'work_from', 'leave', 'absent'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE assetstatus AS ENUM ('available', 'assigned', 'returned', 'lost'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS engagement engagement NOT NULL DEFAULT 'staff';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS allow_leave BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS contract_monthly_fee NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE reimbursements ADD COLUMN IF NOT EXISTS paid_separately BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE reimbursements ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;

-- ===== tables/hrms.sql =====
DO $$ BEGIN CREATE TYPE engagement AS ENUM ('staff', 'contractor'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE vendorcategory AS ENUM ('gst_filing', 'ca_audit', 'legal', 'rent_office', 'tools', 'other'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE billstatus AS ENUM ('draft', 'approved', 'paid'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE applicantstage AS ENUM ('applied', 'interview', 'offer', 'joined', 'rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE attendancemark AS ENUM ('present', 'work_from', 'leave', 'absent'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE assetstatus AS ENUM ('available', 'assigned', 'returned', 'lost'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS engagement engagement NOT NULL DEFAULT 'staff';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS allow_leave BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS contract_monthly_fee NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE reimbursements ADD COLUMN IF NOT EXISTS paid_separately BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE reimbursements ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;

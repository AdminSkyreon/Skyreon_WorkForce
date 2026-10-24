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

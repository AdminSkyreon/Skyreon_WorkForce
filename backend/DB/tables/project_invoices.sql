CREATE TABLE IF NOT EXISTS project_invoices (
    id UUID PRIMARY KEY,
    invoice_no VARCHAR(80) NOT NULL UNIQUE,
    project_id UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    invoice_date DATE NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    entered_by_id UUID REFERENCES users (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_project_invoices_project_id ON project_invoices (project_id);
ALTER TABLE project_payments ADD COLUMN IF NOT EXISTS invoice_id UUID REFERENCES project_invoices (id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_project_payments_invoice_id ON project_payments (invoice_id);

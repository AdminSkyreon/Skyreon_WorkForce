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

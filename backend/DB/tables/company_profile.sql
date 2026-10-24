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

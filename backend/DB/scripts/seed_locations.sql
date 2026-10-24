INSERT INTO locations (id, name, code, city, country, is_active)
VALUES
    (gen_random_uuid(), 'Bhubaneswar', 'BBS', 'Bhubaneswar', 'India', TRUE),
    (gen_random_uuid(), 'Bengaluru', 'BLR', 'Bengaluru', 'India', TRUE),
    (gen_random_uuid(), 'Remote', 'REM', 'Remote', 'Global', TRUE)
ON CONFLICT (code) DO NOTHING;

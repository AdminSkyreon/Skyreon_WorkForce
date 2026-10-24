INSERT INTO leave_types (id, name, code, annual_allocation_days)
VALUES
    (gen_random_uuid(), 'Casual Leave', 'CL', 12),
    (gen_random_uuid(), 'Sick Leave', 'SL', 10),
    (gen_random_uuid(), 'Earned Leave', 'EL', 15)
ON CONFLICT (code) DO NOTHING;

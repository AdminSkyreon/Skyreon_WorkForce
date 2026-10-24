-- Enums used by the tables
DO $$ BEGIN CREATE TYPE userrole AS ENUM ('super_admin', 'admin', 'employee'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE paytype AS ENUM ('fixed', 'hourly'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE employeestatus AS ENUM ('active', 'inactive'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE projectstatus AS ENUM ('planned', 'active', 'on_hold', 'completed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE contracttype AS ENUM ('fixed', 'time_and_material'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE taskpriority AS ENUM ('low', 'medium', 'high'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE taskstatus AS ENUM ('not_started', 'in_progress', 'paused', 'completed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE timeentrysource AS ENUM ('timer', 'manual'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE timesheetstatus AS ENUM ('draft', 'submitted', 'approved', 'rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE leavestatus AS ENUM ('pending', 'approved', 'rejected', 'cancelled'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE engagement AS ENUM ('staff', 'contractor'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE vendorcategory AS ENUM ('gst_filing', 'ca_audit', 'legal', 'rent_office', 'tools', 'other'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE billstatus AS ENUM ('draft', 'approved', 'paid'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE applicantstage AS ENUM ('applied', 'interview', 'offer', 'joined', 'rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE attendancemark AS ENUM ('present', 'work_from', 'leave', 'absent'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE assetstatus AS ENUM ('available', 'assigned', 'returned', 'lost'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

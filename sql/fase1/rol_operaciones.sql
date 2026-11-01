\set ON_ERROR_STOP on
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='habits_operaciones') THEN
        CREATE ROLE habits_operaciones NOLOGIN;
    END IF;
END;
$$;

-- Ampliación aditiva posterior al core. Ejecutar en una transacción explícita.
CREATE TABLE IF NOT EXISTS sesiones (
    token_hash TEXT PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES usuarios(usuario_id) ON DELETE CASCADE,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_en TIMESTAMPTZ NOT NULL,
    CHECK (expira_en > creada_en)
);
CREATE INDEX IF NOT EXISTS idx_sesiones_usuario ON sesiones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_sesiones_expiracion ON sesiones(expira_en);

CREATE OR REPLACE FUNCTION revocar_sesiones_usuario() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.password_hash IS DISTINCT FROM NEW.password_hash
       OR OLD.rol IS DISTINCT FROM NEW.rol
       OR OLD.activo IS DISTINCT FROM NEW.activo
       OR OLD.sucursal_id IS DISTINCT FROM NEW.sucursal_id THEN
        EXECUTE format('DELETE FROM %I.sesiones WHERE usuario_id = $1', TG_TABLE_SCHEMA)
        USING NEW.usuario_id;
    END IF;
    RETURN NULL;
END;
$$;
CREATE OR REPLACE TRIGGER revocar_sesiones_usuario
AFTER UPDATE ON usuarios
FOR EACH ROW EXECUTE FUNCTION revocar_sesiones_usuario();

CREATE OR REPLACE FUNCTION revocar_sesiones_sucursal() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.activa IS DISTINCT FROM NEW.activa THEN
        EXECUTE format(
            'DELETE FROM %I.sesiones WHERE usuario_id IN
             (SELECT usuario_id FROM %I.usuarios WHERE sucursal_id = $1)',
            TG_TABLE_SCHEMA, TG_TABLE_SCHEMA
        ) USING NEW.sucursal_id;
    END IF;
    RETURN NULL;
END;
$$;
CREATE OR REPLACE TRIGGER revocar_sesiones_sucursal
AFTER UPDATE ON sucursales
FOR EACH ROW EXECUTE FUNCTION revocar_sesiones_sucursal();

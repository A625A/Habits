-- Instalar después de 01_core.sql y dentro de una transacción.
-- Solo registra cambios confirmados; no es un registro de intentos fallidos.
CREATE TABLE IF NOT EXISTS auditoria (
    auditoria_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    esquema TEXT NOT NULL,
    tabla TEXT NOT NULL,
    registro_id TEXT NOT NULL,
    operacion TEXT NOT NULL CHECK (operacion IN ('INSERT', 'UPDATE', 'DELETE')),
    usuario_id BIGINT,
    actor_db TEXT NOT NULL DEFAULT CURRENT_USER,
    datos_anteriores JSONB,
    datos_nuevos JSONB
);
-- Sin FK al actor: borrar personal no debe borrar ni invalidar su historial.
CREATE INDEX IF NOT EXISTS idx_auditoria_registro
    ON auditoria(tabla, registro_id, fecha);

CREATE OR REPLACE FUNCTION auditar_cambio() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    anterior JSONB;
    nuevo JSONB;
    pk TEXT;
    permitidos TEXT[] := TG_ARGV[1:TG_NARGS - 1];
BEGIN
    IF TG_NARGS < 2 THEN
        RAISE EXCEPTION 'Auditoría requiere PK y lista explícita de campos permitidos';
    END IF;
    IF TG_OP <> 'INSERT' THEN
        pk := to_jsonb(OLD)->>TG_ARGV[0];
        SELECT jsonb_object_agg(key, value) INTO anterior
        FROM jsonb_each(to_jsonb(OLD)) WHERE key = ANY(permitidos);
    END IF;
    IF TG_OP <> 'DELETE' THEN
        pk := to_jsonb(NEW)->>TG_ARGV[0];
        SELECT jsonb_object_agg(key, value) INTO nuevo
        FROM jsonb_each(to_jsonb(NEW)) WHERE key = ANY(permitidos);
    END IF;
    -- El schema de la tabla evita escribir en la bitácora de otro schema de prueba.
    EXECUTE format(
        'INSERT INTO %I.auditoria (esquema, tabla, registro_id, operacion, usuario_id, datos_anteriores, datos_nuevos)
         VALUES ($1, $2, $3, $4, $5, $6, $7)', TG_TABLE_SCHEMA
    ) USING TG_TABLE_SCHEMA, TG_TABLE_NAME, pk, TG_OP,
        NULLIF(current_setting('habits.usuario_id', true), '')::BIGINT, anterior, nuevo;
    RETURN NULL;
END;
$$;

CREATE OR REPLACE TRIGGER auditar_sucursales
AFTER INSERT OR UPDATE OR DELETE ON sucursales
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('sucursal_id', 'sucursal_id', 'codigo', 'nombre', 'activa');

-- Lista permitida: no registrar hashes, contraseñas, correos ni nombres del personal.
CREATE OR REPLACE TRIGGER auditar_usuarios
AFTER INSERT OR UPDATE OR DELETE ON usuarios
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('usuario_id', 'usuario_id', 'sucursal_id', 'rol', 'activo');

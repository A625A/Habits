-- Aplicar explícitamente como propietario dentro de una transacción; sin datos ni tablas nuevas.
-- El rol de operaciones administra maestros; ventas/saldos siguen detrás de procedimientos.
GRANT INSERT, UPDATE ON clientes TO habits_operaciones;
GRANT USAGE ON SEQUENCE clientes_cliente_id_seq TO habits_operaciones;
DO $$
BEGIN
    EXECUTE format('ALTER FUNCTION auditar_cambio() SECURITY DEFINER');
    EXECUTE format('ALTER FUNCTION auditar_cambio() SET search_path TO %I, pg_temp', current_schema());
END;
$$;
REVOKE ALL ON FUNCTION auditar_cambio() FROM PUBLIC;
GRANT INSERT, UPDATE, DELETE ON preferencias_cliente TO habits_operaciones;
GRANT INSERT ON observaciones_cliente TO habits_operaciones;
GRANT UPDATE(observacion) ON observaciones_cliente TO habits_operaciones;
GRANT USAGE ON SEQUENCE preferencias_cliente_preferencia_id_seq,
    observaciones_cliente_observacion_id_seq TO habits_operaciones;
GRANT INSERT, UPDATE ON mesas TO habits_operaciones;
GRANT INSERT ON reservas,visitas TO habits_operaciones;
GRANT UPDATE(estado) ON reservas TO habits_operaciones;
GRANT USAGE ON SEQUENCE mesas_mesa_id_seq,reservas_reserva_id_seq,visitas_visita_id_seq
    TO habits_operaciones;
-- Estos triggers consultan operadores o toman bloqueos de maestros bajo su dueño.
DO $$
DECLARE nombre TEXT;
BEGIN
    FOREACH nombre IN ARRAY ARRAY['validar_reserva','proteger_visita'] LOOP
        EXECUTE format('ALTER FUNCTION %I() SECURITY DEFINER', nombre);
        EXECUTE format('ALTER FUNCTION %I() SET search_path TO %I, pg_temp', nombre, current_schema());
        EXECUTE format('REVOKE ALL ON FUNCTION %I() FROM PUBLIC', nombre);
    END LOOP;
END;
$$;
GRANT UPDATE(nombre,precio,activo) ON productos TO habits_operaciones;
GRANT INSERT, UPDATE ON ingredientes TO habits_operaciones;
GRANT INSERT, UPDATE, DELETE ON receta_ingrediente TO habits_operaciones;
GRANT USAGE ON SEQUENCE ingredientes_ingrediente_id_seq,receta_ingrediente_receta_ingrediente_id_seq
    TO habits_operaciones;
GRANT INSERT ON inventario_ingrediente TO habits_operaciones;
GRANT UPDATE(cantidad_referencia) ON inventario_ingrediente TO habits_operaciones;
GRANT USAGE ON SEQUENCE inventario_ingrediente_inventario_id_seq TO habits_operaciones;

-- Una recepción siempre crea un lote con saldo igual a la cantidad recibida.
-- No concede INSERT/UPDATE de saldos al rol de operaciones.
CREATE OR REPLACE PROCEDURE registrar_recepcion(p_inventario BIGINT,p_usuario BIGINT,
    p_cantidad NUMERIC,p_vencimiento DATE,INOUT p_lote BIGINT)
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE sede BIGINT;
BEGIN
    SELECT sucursal_id INTO sede FROM inventario_ingrediente WHERE inventario_id=p_inventario;
    PERFORM validar_operador(p_usuario,sede);
    PERFORM 1 FROM inventario_ingrediente c JOIN ingredientes i USING(ingrediente_id)
        WHERE inventario_id=p_inventario AND i.activo FOR SHARE OF c,i;
    IF NOT FOUND THEN RAISE EXCEPTION 'Inventario o ingrediente no disponible'; END IF;
    INSERT INTO lotes_ingrediente(inventario_id,usuario_id,cantidad_inicial,cantidad_disponible,fecha_vencimiento)
    VALUES(p_inventario,p_usuario,p_cantidad,p_cantidad,p_vencimiento) RETURNING lote_id INTO p_lote;
END;
$$;
DO $$
BEGIN
    EXECUTE format('ALTER PROCEDURE registrar_recepcion(BIGINT,BIGINT,NUMERIC,DATE,BIGINT)
        SET search_path TO %I, pg_temp', current_schema());
END;
$$;
REVOKE ALL ON PROCEDURE registrar_recepcion(BIGINT,BIGINT,NUMERIC,DATE,BIGINT) FROM PUBLIC;
GRANT EXECUTE ON PROCEDURE registrar_recepcion(BIGINT,BIGINT,NUMERIC,DATE,BIGINT) TO habits_operaciones;

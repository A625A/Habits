-- El dueño instala; habits_operaciones usa procedimientos, sin DML de ventas o saldos.
DO $$
DECLARE
    objeto RECORD;
    esquema TEXT := current_schema();
BEGIN
    IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='habits_operaciones') THEN
        RAISE EXCEPTION 'Ejecutar rol_operaciones.sql como administrador PostgreSQL primero';
    END IF;
    FOR objeto IN
        SELECT p.oid::regprocedure AS firma,p.prokind,p.proname FROM pg_proc p
        JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname=esquema AND p.proname IN (
            'registrar_llegada','cancelar_reserva','registrar_produccion','registrar_venta',
            'consumir_receta','validar_operador','comprobar_llegada','venta_con_detalles')
    LOOP
        IF objeto.prokind='p' THEN
            EXECUTE format('ALTER PROCEDURE %s SECURITY DEFINER',objeto.firma);
            EXECUTE format('ALTER PROCEDURE %s SET search_path TO %I, pg_temp',objeto.firma,esquema);
            EXECUTE format('REVOKE ALL ON PROCEDURE %s FROM PUBLIC',objeto.firma);
            EXECUTE format('GRANT EXECUTE ON PROCEDURE %s TO habits_operaciones',objeto.firma);
        ELSE
            IF objeto.proname IN ('comprobar_llegada','venta_con_detalles') THEN
                EXECUTE format('ALTER FUNCTION %s SECURITY DEFINER',objeto.firma);
                EXECUTE format('ALTER FUNCTION %s SET search_path TO %I, pg_temp',objeto.firma,esquema);
            END IF;
            EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC',objeto.firma);
        END IF;
    END LOOP;
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO habits_operaciones',esquema);
END;
$$;
GRANT SELECT ON sucursales,mesas,clientes,productos,ingredientes,receta_ingrediente,
    inventario_ingrediente,lotes_ingrediente,producciones,preferencias_cliente,reservas,
    visitas,observaciones_cliente,ventas,detalle_ventas,v_stock_ingredientes,
    v_stock_terminados,v_totales_ventas TO habits_operaciones;

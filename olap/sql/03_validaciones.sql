-- Solo lectura. Por defecto exige la entrega de 10,000 tickets.
-- Para fixtures pequeños: SET habits_olap.tickets_esperados = '4';
-- Sin BEGIN/COMMIT para reutilizarlo dentro de la transacción del ETL.
-- Fuera del ETL: psql -X -v ON_ERROR_STOP=1 --single-transaction -f este_archivo.sql

DO $$
DECLARE
    esperados BIGINT := COALESCE(NULLIF(current_setting('habits_olap.tickets_esperados', true), ''),
                                '10000')::bigint;
    reales BIGINT;
BEGIN
    IF esperados <= 0 THEN RAISE EXCEPTION 'El número esperado debe ser positivo'; END IF;

    IF EXISTS (
        SELECT ticket_id FROM olap.fact_ventas GROUP BY ticket_id
        HAVING COUNT(DISTINCT fecha) <> 1 OR COUNT(DISTINCT sucursal_id) <> 1
            OR COUNT(DISTINCT tipo_venta) <> 1
    ) THEN RAISE EXCEPTION 'Tickets incoherentes: revisar fecha, sucursal y tipo'; END IF;

    SELECT COUNT(DISTINCT ticket_id) INTO reales FROM olap.fact_ventas;
    IF reales <> esperados THEN
        RAISE EXCEPTION 'Se esperaban % tickets; se encontraron %', esperados, reales;
    END IF;

    IF (SELECT COUNT(*) FROM olap.dim_producto) <> 12 OR EXISTS (
        SELECT 'HAB-' || lpad(n::text, 2, '0') FROM generate_series(1, 12) AS ids(n)
        EXCEPT SELECT codigo FROM olap.dim_producto
    ) OR EXISTS (
        SELECT 1 FROM olap.dim_producto
        WHERE categoria <> CASE WHEN codigo <= 'HAB-06' THEN 'bebida'
                                WHEN codigo <= 'HAB-10' THEN 'panaderia' ELSE 'postre' END
    ) THEN RAISE EXCEPTION 'Se requieren los 12 productos originales y sus categorías'; END IF;

    IF (SELECT COUNT(*) FROM olap.dim_sucursal) <> 2 OR EXISTS (
        SELECT codigo FROM (VALUES ('DEMO-01'), ('DEMO-02')) AS original(codigo)
        EXCEPT SELECT codigo FROM olap.dim_sucursal
    ) THEN RAISE EXCEPTION 'Se requieren las dos sucursales originales'; END IF;

    IF (SELECT COUNT(*) FROM olap.dim_fecha) <> 365 OR
       (SELECT COUNT(*) FROM olap.dim_tipo_venta) <> 2 THEN
        RAISE EXCEPTION 'Calendario o tipos de venta incompletos';
    END IF;

    IF (SELECT COUNT(*) FROM dm.v_ventas_detalle) <> (SELECT COUNT(*) FROM olap.fact_ventas)
       OR (SELECT COUNT(DISTINCT detalle_id) FROM dm.v_ventas_detalle) <>
          (SELECT COUNT(*) FROM olap.fact_ventas)
       OR (SELECT SUM(importe) FROM dm.v_ventas_detalle) IS DISTINCT FROM
          (SELECT SUM(importe) FROM olap.fact_ventas)
       OR (SELECT SUM(ingresos) FROM dm.v_ventas_mensuales) IS DISTINCT FROM
          (SELECT SUM(importe) FROM olap.fact_ventas)
       OR (SELECT SUM(ingresos) FROM dm.v_productos) IS DISTINCT FROM
          (SELECT SUM(importe) FROM olap.fact_ventas)
       OR (SELECT SUM(ingresos) FROM dm.v_sucursales) IS DISTINCT FROM
          (SELECT SUM(importe) FROM olap.fact_ventas)
       OR (SELECT SUM(tickets) FROM dm.v_ventas_mensuales) <> reales
       OR (SELECT SUM(tickets) FROM dm.v_sucursales) <> reales THEN
        RAISE EXCEPTION 'DataMart no reconcilia: filas, ingresos o tickets duplicados';
    END IF;
END;
$$;

SELECT COUNT(*) AS detalles, COUNT(DISTINCT ticket_id) AS tickets,
       MIN(fecha) AS primera_fecha, MAX(fecha) AS ultima_fecha,
       SUM(cantidad) AS unidades, SUM(importe) AS ingresos_gtq,
       SUM(importe) / NULLIF(COUNT(DISTINCT ticket_id), 0) AS ticket_promedio_gtq
FROM olap.fact_ventas;

SELECT * FROM dm.v_ventas_mensuales ORDER BY mes_inicio, sucursal_id, tipo_venta;

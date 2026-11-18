-- Ejecutar con psql desde la raíz. Solo lectura, misma instantánea para los casos.
-- Comparar con los filtros de VALIDACION.md. No cargar fixtures aquí.
\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SELECT current_database() AS base, current_user AS lector,
       current_setting('server_version') AS version_postgresql;

-- Esta consulta informa el estado; la aprobación de ETL exige además SQL 03.
SELECT COUNT(*) AS filas_detalle, COUNT(DISTINCT detalle_id) AS detalles_distintos,
       COUNT(DISTINCT ticket_id) AS tickets_distintos,
       COUNT(DISTINCT ticket_id) = 10000 AS cumple_10000,
       MIN(fecha) AS primera_fecha, MAX(fecha) AS ultima_fecha,
       COUNT(*) FILTER (WHERE fecha < DATE '2025-11-01'
                        OR fecha >= DATE '2026-11-01') AS detalles_fuera_periodo
FROM dm.v_ventas_detalle;

-- Ceros y NULL coinciden con las medidas DAX de Brian.
WITH casos(caso, desde, hasta, sucursal, categoria) AS (
    VALUES
    ('Total general', DATE '2025-11-01', DATE '2026-11-01', NULL::text, NULL::text),
    ('Sucursal DEMO-01', DATE '2025-11-01', DATE '2026-11-01', 'DEMO-01', NULL),
    ('Categoría bebida', DATE '2025-11-01', DATE '2026-11-01', NULL, 'bebida'),
    ('Combinación noviembre / DEMO-01 / bebida', DATE '2025-11-01', DATE '2025-12-01', 'DEMO-01', 'bebida'),
    ('Fuera del calendario: sin ventas', DATE '2026-11-01', DATE '2026-11-02', NULL, NULL)
)
SELECT c.*, r.* FROM casos c
CROSS JOIN LATERAL (
    SELECT COALESCE(SUM(d.importe), 0) AS ingresos_gtq,
           COUNT(DISTINCT d.ticket_id) AS ventas_distintas,
           COALESCE(SUM(d.cantidad), 0) AS unidades,
           SUM(d.importe) / NULLIF(COUNT(DISTINCT d.ticket_id), 0) AS ticket_promedio_gtq
    FROM dm.v_ventas_detalle d
    WHERE d.fecha >= c.desde AND d.fecha < c.hasta
      AND (c.sucursal IS NULL OR d.codigo_sucursal = c.sucursal)
      AND (c.categoria IS NULL OR d.categoria = c.categoria)
) r ORDER BY c.desde, c.caso;

-- Doce meses aunque alguno carezca de ventas. No sumar distintos por producto.
WITH meses AS (
    SELECT generate_series(DATE '2025-11-01', DATE '2026-10-01', INTERVAL '1 month')::date AS inicio
)
SELECT m.inicio AS mes, COALESCE(SUM(d.importe), 0) AS ingresos_gtq,
       COUNT(DISTINCT d.ticket_id) AS ventas_distintas,
       COALESCE(SUM(d.cantidad), 0) AS unidades,
       SUM(d.importe) / NULLIF(COUNT(DISTINCT d.ticket_id), 0) AS ticket_promedio_gtq
FROM meses m LEFT JOIN dm.v_ventas_detalle d
  ON d.fecha >= m.inicio AND d.fecha < m.inicio + INTERVAL '1 month'
GROUP BY m.inicio ORDER BY m.inicio;

-- Cero filas = ticket coherente. Detener comparación si aparecen anomalías.
SELECT ticket_id FROM dm.v_ventas_detalle
GROUP BY ticket_id HAVING COUNT(DISTINCT fecha) <> 1
    OR COUNT(DISTINCT codigo_sucursal) <> 1 OR COUNT(DISTINCT tipo_venta) <> 1;

-- Selección reproducible: menor ID numérico, no menor texto lexicográfico.
-- Si no hay candidatos, no hay filas: registrar «no existe», no «aprobado».
WITH candidatos AS (
    SELECT ticket_id, COUNT(*) AS productos, COUNT(DISTINCT categoria) AS categorias
    FROM dm.v_ventas_detalle GROUP BY ticket_id
), elegidos AS (
    SELECT 'Multíproducto' AS caso, (
        SELECT ticket_id FROM candidatos WHERE productos > 1 ORDER BY ticket_id LIMIT 1
    ) AS ticket_id
    UNION ALL
    SELECT 'Multicategoría', (
        SELECT ticket_id FROM candidatos WHERE categorias > 1 ORDER BY ticket_id LIMIT 1
    )
)
SELECT e.caso, e.ticket_id::text, d.categoria,
       COALESCE(SUM(d.importe), 0) AS ingresos_gtq,
       COUNT(DISTINCT d.ticket_id) AS ventas_distintas,
       COALESCE(SUM(d.cantidad), 0) AS unidades,
       SUM(d.importe) / NULLIF(COUNT(DISTINCT d.ticket_id), 0) AS ticket_promedio_gtq,
       GROUPING(d.categoria) = 1 AS total_ticket
FROM elegidos e JOIN dm.v_ventas_detalle d USING(ticket_id)
GROUP BY GROUPING SETS ((e.caso,e.ticket_id), (e.caso,e.ticket_id,d.categoria))
ORDER BY e.caso, total_ticket DESC, d.categoria;

-- Fuentes para comparar los cinco gráficos, sin filtros iniciales.
-- Aplicar los mismos predicados WHERE en cada consulta al comprobar selecciones.
SELECT codigo_producto, producto, categoria, SUM(cantidad) AS unidades,
       SUM(importe) AS ingresos_gtq, COUNT(DISTINCT ticket_id) AS ventas_distintas
FROM dm.v_ventas_detalle GROUP BY codigo_producto, producto, categoria
ORDER BY unidades DESC, codigo_producto;

SELECT tipo_venta, SUM(importe) AS ingresos_gtq
FROM dm.v_ventas_detalle GROUP BY tipo_venta ORDER BY tipo_venta;

COMMIT;

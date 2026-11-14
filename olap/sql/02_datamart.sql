BEGIN;

CREATE SCHEMA dm;

CREATE VIEW dm.v_ventas_detalle AS
SELECT f.detalle_id, f.ticket_id, f.fecha, d.dia, d.mes, d.trimestre, d.anio,
       f.producto_id, p.codigo AS codigo_producto, p.nombre AS producto, p.categoria,
       f.sucursal_id, s.codigo AS codigo_sucursal, s.nombre AS sucursal,
       f.tipo_venta, f.cantidad, f.precio_unitario, f.importe
FROM olap.fact_ventas AS f
JOIN olap.dim_fecha AS d ON d.fecha = f.fecha
JOIN olap.dim_producto AS p ON p.producto_id = f.producto_id
JOIN olap.dim_sucursal AS s ON s.sucursal_id = f.sucursal_id
JOIN olap.dim_tipo_venta AS t ON t.tipo_venta = f.tipo_venta;

-- Grano: mes + sucursal + tipo. No agrega por categoría.
CREATE VIEW dm.v_ventas_mensuales AS
SELECT make_date(anio, mes, 1) AS mes_inicio, anio, mes,
       sucursal_id, codigo_sucursal, sucursal, tipo_venta,
       SUM(importe) AS ingresos, COUNT(DISTINCT ticket_id) AS tickets,
       SUM(cantidad) AS unidades,
       SUM(importe) / NULLIF(COUNT(DISTINCT ticket_id), 0) AS ticket_promedio
FROM dm.v_ventas_detalle
GROUP BY anio, mes, sucursal_id, codigo_sucursal, sucursal, tipo_venta;

CREATE VIEW dm.v_productos AS
SELECT p.producto_id, p.codigo AS codigo_producto, p.nombre AS producto, p.categoria,
       COALESCE(SUM(f.importe), 0::numeric) AS ingresos,
       COUNT(DISTINCT f.ticket_id) AS tickets,
       COALESCE(SUM(f.cantidad), 0::bigint) AS unidades,
       SUM(f.importe) / NULLIF(COUNT(DISTINCT f.ticket_id), 0) AS ticket_promedio
FROM olap.dim_producto AS p
LEFT JOIN olap.fact_ventas AS f ON f.producto_id = p.producto_id
GROUP BY p.producto_id, p.codigo, p.nombre, p.categoria;

CREATE VIEW dm.v_sucursales AS
SELECT s.sucursal_id, s.codigo AS codigo_sucursal, s.nombre AS sucursal,
       COALESCE(SUM(f.importe), 0::numeric) AS ingresos,
       COUNT(DISTINCT f.ticket_id) AS tickets,
       COALESCE(SUM(f.cantidad), 0::bigint) AS unidades,
       SUM(f.importe) / NULLIF(COUNT(DISTINCT f.ticket_id), 0) AS ticket_promedio
FROM olap.dim_sucursal AS s
LEFT JOIN olap.fact_ventas AS f ON f.sucursal_id = s.sucursal_id
GROUP BY s.sucursal_id, s.codigo, s.nombre;

COMMENT ON VIEW dm.v_ventas_detalle IS
'Fuente principal para Power BI: filtros y KPIs con COUNT(DISTINCT ticket_id). Una fila por detalle.';
COMMENT ON VIEW dm.v_ventas_mensuales IS
'Mes/sucursal/tipo. Meses sin ventas no generan fila; no promediar ticket_promedio sin ponderar.';
COMMENT ON VIEW dm.v_productos IS
'Acumulado de todo el período por producto. Tickets NO aditivos entre productos/categorías.';
COMMENT ON VIEW dm.v_sucursales IS
'Acumulado de todo el período por sucursal. Para filtrar fecha/categoría, usar detalle.';

COMMIT;

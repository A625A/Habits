-- PENDIENTE DE INTEGRACIÓN: no ejecutar hasta que existan ambas vistas contratadas.
-- No crea tablas ni vistas de módulos ajenos. No se aplica con db-upgrade.
-- Rodrigo: reporte_ventas_confirmadas, una fila por venta confirmada (sin canceladas).
-- Chris: reporte_reservas_vigentes, una fila por reserva no cancelada.
-- Desde inclusivo / hasta exclusivo, timestamptz; sucursal_id NULL = todas.
-- Cada agregado conserva una fila por sede ANTES del JOIN, evitando multiplicación.
WITH ventas_por_sucursal AS (
    SELECT sucursal_id, COUNT(*) AS ventas, SUM(total) AS importe_ventas
    FROM reporte_ventas_confirmadas
    WHERE fecha >= %(desde)s AND fecha < %(hasta)s
    GROUP BY sucursal_id
), reservas_por_sucursal AS (
    SELECT sucursal_id, COUNT(*) AS reservas
    FROM reporte_reservas_vigentes
    WHERE inicio >= %(desde)s AND inicio < %(hasta)s
    GROUP BY sucursal_id
)
SELECT s.sucursal_id, s.codigo, s.nombre,
       COALESCE(r.reservas, 0) AS reservas,
       COALESCE(v.ventas, 0) AS ventas,
       COALESCE(v.importe_ventas, 0) AS importe_ventas
FROM sucursales s
LEFT JOIN ventas_por_sucursal v USING (sucursal_id)
LEFT JOIN reservas_por_sucursal r USING (sucursal_id)
WHERE (%(sucursal_id)s::BIGINT IS NULL OR s.sucursal_id = %(sucursal_id)s)
ORDER BY s.codigo;

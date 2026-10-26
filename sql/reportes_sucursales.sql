-- Comparación disponible hoy: personal por sucursal, incluidas sedes sin personal.
-- Ventas/reservas NULL = módulo no integrado, no cero operaciones.
-- %(sucursal_id)s: NULL para administrador, ID obligatorio para gerente.
WITH personal AS (
    SELECT sucursal_id,
           COUNT(*) AS usuarios_totales,
           COUNT(*) FILTER (WHERE activo) AS usuarios_activos,
           COUNT(*) FILTER (WHERE activo AND rol = 'administrador') AS administradores_activos,
           COUNT(*) FILTER (WHERE activo AND rol = 'gerente') AS gerentes_activos,
           COUNT(*) FILTER (WHERE activo AND rol = 'mesero') AS meseros_activos
    FROM usuarios
    GROUP BY sucursal_id
)
SELECT s.sucursal_id, s.codigo, s.nombre, s.activa,
       COALESCE(p.usuarios_totales, 0) AS usuarios_totales,
       COALESCE(p.usuarios_activos, 0) AS usuarios_activos,
       COALESCE(p.administradores_activos, 0) AS administradores_activos,
       COALESCE(p.gerentes_activos, 0) AS gerentes_activos,
       COALESCE(p.meseros_activos, 0) AS meseros_activos,
       NULL::BIGINT AS reservas, NULL::BIGINT AS ventas,
       NULL::NUMERIC AS importe_ventas
FROM sucursales s LEFT JOIN personal p USING (sucursal_id)
WHERE (%(sucursal_id)s::BIGINT IS NULL OR s.sucursal_id = %(sucursal_id)s)
ORDER BY s.codigo;

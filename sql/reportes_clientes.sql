-- REPORTE 2: Top 10 Clientes Frecuentes
-- Criterio: Solo contabiliza visitas efectivas (confirmadas o completadas) para no inflar métricas con cancelaciones.
SELECT 
    c.cliente_id,
    c.nombre,
    c.telefono,
    COUNT(r.reserva_id) AS total_visitas,
    MAX(r.fecha_inicio) AS ultima_visita
FROM clientes c
JOIN reservas r ON c.cliente_id = r.cliente_id
WHERE r.estado IN ('completada', 'confirmada')
GROUP BY c.cliente_id, c.nombre, c.telefono
ORDER BY total_visitas DESC, ultima_visita DESC
LIMIT 10;

-- REPORTE 3: Top 5 Clientes con Más Reservas y sus Preferencias
-- Criterio: Cuenta reservas acumuladas activas y consolida sus preferencias en una sola línea sin duplicar filas.
WITH top_clientes AS (
    SELECT 
        c.cliente_id,
        c.nombre,
        COUNT(r.reserva_id) AS total_reservas
    FROM clientes c
    JOIN reservas r ON c.cliente_id = r.cliente_id
    WHERE r.estado != 'cancelada'
    GROUP BY c.cliente_id, c.nombre
    ORDER BY total_reservas DESC
    LIMIT 5
)
SELECT 
    tc.cliente_id,
    tc.nombre,
    tc.total_reservas,
    COALESCE(
        STRING_AGG(DISTINCT p.nombre || CASE WHEN pref.nota_preferencia IS NOT NULL THEN ' (' || pref.nota_preferencia || ')' ELSE '' END, ', '),
        'Sin preferencias registradas'
    ) AS productos_preferidos
FROM top_clientes tc
LEFT JOIN preferencias_cliente pref ON tc.cliente_id = pref.cliente_id
LEFT JOIN productos p ON pref.producto_id = p.producto_id
GROUP BY tc.cliente_id, tc.nombre, tc.total_reservas
ORDER BY tc.total_reservas DESC;
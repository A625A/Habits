-- Consultas de revisión: se pueden ejecutar en pgAdmin sin cambiar datos.
BEGIN TRANSACTION READ ONLY;

-- Reservas con su mesa y horario. Una cancelada conserva su historial.
SELECT s.codigo AS sucursal,m.numero_mesa,m.capacidad,c.nombre AS cliente,
       r.personas,r.fecha_inicio AT TIME ZONE 'America/Guatemala' AS inicio,
       r.fecha_fin AT TIME ZONE 'America/Guatemala' AS fin,r.estado
FROM reservas r JOIN sucursales s USING(sucursal_id)
JOIN mesas m ON m.mesa_id=r.mesa_id
JOIN clientes c USING(cliente_id)
ORDER BY s.codigo,r.fecha_inicio,m.numero_mesa;

-- Debe devolver cero filas: dos reservas activas no deben ocupar la misma mesa.
-- Si una termina justo cuando comienza otra, no se considera un cruce.
SELECT a.reserva_id AS primera,b.reserva_id AS segunda,a.mesa_id
FROM reservas a JOIN reservas b ON a.mesa_id=b.mesa_id AND a.reserva_id<b.reserva_id
WHERE a.estado IN ('pendiente','confirmada','completada')
AND b.estado IN ('pendiente','confirmada','completada')
AND tstzrange(a.fecha_inicio,a.fecha_fin,'[)') && tstzrange(b.fecha_inicio,b.fecha_fin,'[)');

-- Existencias utilizables por sede: los lotes vencidos no se suman.
SELECT s.codigo AS sucursal,i.nombre AS ingrediente,i.unidad,
       v.cantidad_disponible,v.cantidad_referencia,
       stock_bajo(v.cantidad_disponible,v.cantidad_referencia) AS alerta_quince_por_ciento
FROM v_stock_ingredientes v JOIN sucursales s USING(sucursal_id)
JOIN ingredientes i USING(ingrediente_id)
ORDER BY s.codigo,i.nombre;

-- Revisar todos los lotes con saldo, incluso si vencen en otro mes.
SELECT s.codigo AS sucursal,g.nombre AS ingrediente,l.lote_id,
       l.cantidad_disponible,l.fecha_vencimiento,
       CASE WHEN l.fecha_vencimiento<h.hoy THEN 'vencido'
            WHEN l.fecha_vencimiento<=h.hoy+7 THEN 'proximo'
            ELSE 'posterior' END AS estado
FROM lotes_ingrediente l JOIN inventario_ingrediente i USING(inventario_id)
JOIN sucursales s USING(sucursal_id) JOIN ingredientes g USING(ingrediente_id)
CROSS JOIN (SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date AS hoy) h
WHERE l.cantidad_disponible>0
ORDER BY s.codigo,g.nombre,l.fecha_vencimiento,l.lote_id;

COMMIT;

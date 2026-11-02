-- Consultas ejecutables de presentación. Requieren Fase 1 y Fase 2 instaladas.
-- Solo lectura. Ejecutar como propietario para consultar también la bitácora.
BEGIN READ ONLY;

-- 1. Índices ya instalados; no crear duplicados para la presentación.
SELECT tablename,indexname,indexdef FROM pg_indexes
WHERE schemaname=current_schema()
AND tablename IN ('reservas','visitas','ventas','lotes_ingrediente','producciones')
ORDER BY tablename,indexname;

-- Plan y tiempos reales del historial de un cliente existente (si hay alguno).
EXPLAIN (ANALYZE, BUFFERS)
SELECT reserva_id,fecha_inicio,estado FROM reservas
WHERE cliente_id=(SELECT min(cliente_id) FROM clientes)
ORDER BY fecha_inicio DESC LIMIT 50;

-- 2. Vistas: saldo utilizable y alerta del 15 % según referencia configurada.
SELECT s.inventario_id,s.sucursal_id,i.nombre,i.unidad,s.cantidad_disponible,
    s.cantidad_referencia,stock_bajo(s.cantidad_disponible,s.cantidad_referencia) AS bajo_stock
FROM v_stock_ingredientes s JOIN ingredientes i USING(ingrediente_id)
ORDER BY s.sucursal_id,i.nombre;

SELECT sucursal_id,producto_id,cantidad_disponible
FROM v_stock_terminados ORDER BY sucursal_id,producto_id;

SELECT venta_id,sucursal_id,fecha,unidades,total
FROM v_totales_ventas ORDER BY fecha DESC,venta_id DESC LIMIT 20;

-- CTE: agregar visitas y compras por separado evita multiplicarlas al unir.
WITH atenciones AS (
    SELECT sucursal_id,count(*) AS visitas FROM visitas GROUP BY sucursal_id
), compras AS (
    SELECT sucursal_id,count(*) AS ventas,sum(total) AS importe
    FROM v_totales_ventas GROUP BY sucursal_id
)
SELECT s.codigo,coalesce(a.visitas,0) AS visitas,coalesce(c.ventas,0) AS ventas,
    coalesce(c.importe,0) AS importe
FROM sucursales s LEFT JOIN atenciones a USING(sucursal_id)
LEFT JOIN compras c USING(sucursal_id) ORDER BY s.codigo;

-- 3. Funciones existentes: intervalo [desde,hasta) del mes actual en Guatemala.
SELECT * FROM reporte_sucursales(
    date_trunc('month',CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala') AT TIME ZONE 'America/Guatemala',
    (date_trunc('month',CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala') + interval '1 month') AT TIME ZONE 'America/Guatemala'
);

-- 4. Triggers reales de negocio: definición, momento y operaciones que los disparan.
SELECT c.relname AS tabla,t.tgname,pg_get_triggerdef(t.oid) AS definicion
FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname=current_schema() AND NOT t.tgisinternal
AND c.relname IN ('reservas','visitas','ventas','lotes_ingrediente')
ORDER BY c.relname,t.tgname;

-- Eventos confirmados; se omiten snapshots con información de clientes.
SELECT tabla,registro_id,operacion,usuario_id,fecha
FROM auditoria ORDER BY auditoria_id DESC LIMIT 20;
COMMIT;

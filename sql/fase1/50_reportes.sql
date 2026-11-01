CREATE FUNCTION reporte_productos(desde TIMESTAMPTZ,hasta TIMESTAMPTZ)
RETURNS TABLE(producto_id BIGINT,nombre TEXT,unidades BIGINT,importe NUMERIC)
LANGUAGE sql STABLE AS $$
    SELECT p.producto_id,p.nombre::text,SUM(d.cantidad),SUM(d.cantidad*d.precio_unitario)
    FROM ventas v JOIN detalle_ventas d USING(venta_id) JOIN productos p USING(producto_id)
    WHERE v.fecha >= desde AND v.fecha < hasta
    GROUP BY p.producto_id ORDER BY SUM(d.cantidad) DESC,p.producto_id LIMIT 10;
$$;

CREATE FUNCTION reporte_frecuentes(desde TIMESTAMPTZ,hasta TIMESTAMPTZ)
RETURNS TABLE(cliente_id BIGINT,nombre TEXT,visitas BIGINT)
LANGUAGE sql STABLE AS $$
    WITH frecuencia AS (
        SELECT cliente_id,COUNT(*) AS visitas FROM visitas
        WHERE atendida_en >= desde AND atendida_en < hasta GROUP BY cliente_id
    )
    SELECT c.cliente_id,c.nombre::text,f.visitas FROM frecuencia f JOIN clientes c USING(cliente_id)
    ORDER BY f.visitas DESC,c.cliente_id LIMIT 10;
$$;

CREATE FUNCTION reporte_reservas(desde TIMESTAMPTZ,hasta TIMESTAMPTZ)
RETURNS TABLE(cliente_id BIGINT,nombre TEXT,confirmadas BIGINT,completadas BIGINT,reservas BIGINT,preferencias TEXT[])
LANGUAGE sql STABLE AS $$
    WITH conteos AS (
        SELECT cliente_id,COUNT(*) FILTER(WHERE estado='confirmada') AS confirmadas,
            COUNT(*) FILTER(WHERE estado='completada') AS completadas,COUNT(*) AS reservas
        FROM reservas WHERE fecha_inicio >= desde AND fecha_inicio < hasta
        AND estado IN ('confirmada','completada') GROUP BY cliente_id
    )
    SELECT c.cliente_id,c.nombre::text,r.confirmadas,r.completadas,r.reservas,
        ARRAY(SELECT p.nombre::text FROM preferencias_cliente f JOIN productos p USING(producto_id)
            WHERE f.cliente_id=c.cliente_id ORDER BY p.producto_id)
    FROM conteos r JOIN clientes c USING(cliente_id)
    ORDER BY r.reservas DESC,c.cliente_id LIMIT 5;
$$;

CREATE FUNCTION reporte_inventario(mes DATE)
RETURNS TABLE(sucursal_id BIGINT,ingrediente_id BIGINT,disponible_actual NUMERIC,
    referencia NUMERIC,bajo_stock BOOLEAN,lote_id BIGINT,vencimiento DATE,saldo_lote NUMERIC,estado TEXT)
LANGUAGE sql STABLE AS $$
    SELECT v.sucursal_id,v.ingrediente_id,v.cantidad_disponible,v.cantidad_referencia,
        stock_bajo(v.cantidad_disponible,v.cantidad_referencia),l.lote_id,l.fecha_vencimiento,l.cantidad_disponible,
        CASE WHEN l.lote_id IS NULL THEN 'sin vencimientos en el mes'
            WHEN l.fecha_vencimiento < (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date THEN 'vencido'
            WHEN l.fecha_vencimiento <= (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date+7 THEN 'proximo'
            ELSE 'posterior' END
    FROM v_stock_ingredientes v LEFT JOIN lotes_ingrediente l ON l.inventario_id=v.inventario_id
        AND l.cantidad_disponible > 0
        AND l.fecha_vencimiento >= date_trunc('month',mes::timestamp)::date
        AND l.fecha_vencimiento < (date_trunc('month',mes::timestamp)+interval '1 month')::date
    WHERE stock_bajo(v.cantidad_disponible,v.cantidad_referencia) OR l.lote_id IS NOT NULL
    ORDER BY v.sucursal_id,v.ingrediente_id,l.fecha_vencimiento,l.lote_id;
$$;

CREATE FUNCTION reporte_sucursales(desde TIMESTAMPTZ,hasta TIMESTAMPTZ)
RETURNS TABLE(sucursal_id BIGINT,nombre TEXT,confirmadas BIGINT,completadas BIGINT,
    reservas BIGINT,ventas BIGINT,importe NUMERIC)
LANGUAGE sql STABLE AS $$
    WITH r AS (
        SELECT sucursal_id,COUNT(*) FILTER(WHERE estado='confirmada') AS confirmadas,
            COUNT(*) FILTER(WHERE estado='completada') AS completadas,COUNT(*) AS reservas
        FROM reservas WHERE fecha_inicio >= desde AND fecha_inicio < hasta
        AND estado IN ('confirmada','completada') GROUP BY sucursal_id
    ), v AS (
        SELECT sucursal_id,COUNT(*) AS ventas,SUM(total) AS importe FROM v_totales_ventas
        WHERE fecha >= desde AND fecha < hasta GROUP BY sucursal_id
    )
    SELECT s.sucursal_id,s.nombre::text,COALESCE(r.confirmadas,0),COALESCE(r.completadas,0),
        COALESCE(r.reservas,0),COALESCE(v.ventas,0),COALESCE(v.importe,0)
    FROM sucursales s LEFT JOIN r USING(sucursal_id) LEFT JOIN v USING(sucursal_id)
    ORDER BY s.sucursal_id;
$$;

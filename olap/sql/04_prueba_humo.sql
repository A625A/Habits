-- Se puede repetir. No deja hechos ni dimensiones de prueba, incluso en una BD con datos.
-- Ejecutar con psql -X -v ON_ERROR_STOP=1 -f ... en una base OLAP de práctica.
BEGIN;

DO $$
DECLARE
    producto_a BIGINT;
    producto_b BIGINT;
    sede BIGINT;
    ticket BIGINT;
    detalle BIGINT;
    codigo_a TEXT;
    codigo_b TEXT;
    codigo_s TEXT;
BEGIN
    SELECT COALESCE(MAX(producto_id), 0) + 1 INTO producto_a FROM olap.dim_producto;
    producto_b := producto_a + 1;
    SELECT COALESCE(MAX(sucursal_id), 0) + 1 INTO sede FROM olap.dim_sucursal;
    SELECT COALESCE(MAX(ticket_id), 0) + 1 INTO ticket FROM olap.fact_ventas;
    SELECT COALESCE(MAX(detalle_id), 0) + 1 INTO detalle FROM olap.fact_ventas;
    codigo_a := 'TEST-' || producto_a;
    codigo_b := 'TEST-' || producto_b;
    codigo_s := 'TEST-' || sede;
    IF EXISTS (SELECT 1 FROM olap.dim_producto WHERE codigo IN (codigo_a, codigo_b))
       OR EXISTS (SELECT 1 FROM olap.dim_sucursal WHERE codigo = codigo_s) THEN
        RAISE EXCEPTION 'Código de prueba ocupado; usar una base OLAP vacía';
    END IF;
    INSERT INTO olap.dim_producto(producto_id,codigo,nombre,categoria) VALUES
        (producto_a,codigo_a,'Bebida de prueba','bebida'),
        (producto_b,codigo_b,'Pan de prueba','panaderia');
    INSERT INTO olap.dim_sucursal(sucursal_id,codigo,nombre)
        VALUES (sede,codigo_s,'Sucursal de prueba');
    INSERT INTO olap.fact_ventas
        (detalle_id,ticket_id,fecha,producto_id,sucursal_id,tipo_venta,cantidad,precio_unitario)
    VALUES (detalle,ticket,'2025-11-01',producto_a,sede,'local',2,10),
           (detalle+1,ticket,'2025-11-01',producto_b,sede,'local',1,5);

    IF (SELECT COUNT(*) FROM dm.v_ventas_detalle WHERE ticket_id=ticket) <> 2
       OR (SELECT SUM(importe) FROM dm.v_ventas_detalle WHERE ticket_id=ticket) <> 25
       OR (SELECT tickets FROM dm.v_ventas_mensuales
           WHERE sucursal_id=sede AND mes_inicio=DATE '2025-11-01' AND tipo_venta='local') <> 1
       OR (SELECT ticket_promedio FROM dm.v_sucursales WHERE sucursal_id=sede) <> 25
       OR (SELECT unidades FROM dm.v_productos WHERE producto_id=producto_a) <> 2 THEN
        RAISE EXCEPTION 'Falló la prueba de humo del DataMart';
    END IF;
    RAISE NOTICE 'Humo OK: 2 detalles, 1 ticket, 3 unidades, Q25; se revertirá toda la prueba';
END;
$$;

ROLLBACK;

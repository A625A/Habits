CREATE TABLE ventas (
    venta_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sucursal_id BIGINT NOT NULL REFERENCES sucursales ON DELETE RESTRICT,
    usuario_id BIGINT NOT NULL REFERENCES usuarios ON DELETE RESTRICT,
    visita_id BIGINT,
    mesa_id BIGINT,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('local','llevar')),
    fecha TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY(visita_id,sucursal_id) REFERENCES visitas(visita_id,sucursal_id) ON DELETE RESTRICT,
    FOREIGN KEY(mesa_id,sucursal_id) REFERENCES mesas(mesa_id,sucursal_id) ON DELETE RESTRICT,
    CHECK(tipo <> 'llevar' OR mesa_id IS NULL)
);
CREATE TABLE detalle_ventas (
    detalle_venta_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    venta_id BIGINT NOT NULL REFERENCES ventas ON DELETE RESTRICT,
    producto_id BIGINT NOT NULL REFERENCES productos ON DELETE RESTRICT,
    cantidad INTEGER NOT NULL CHECK(cantidad > 0),
    precio_unitario NUMERIC(12,2) NOT NULL CHECK(precio_unitario > 0 AND precio_unitario <> 'NaN'),
    UNIQUE(venta_id,producto_id)
);

CREATE FUNCTION validar_venta() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v visitas%ROWTYPE;
BEGIN
    PERFORM validar_operador(NEW.usuario_id,NEW.sucursal_id);
    IF NEW.mesa_id IS NOT NULL THEN
        PERFORM 1 FROM mesas WHERE mesa_id=NEW.mesa_id AND activa FOR SHARE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Mesa inactiva'; END IF;
    END IF;
    IF NEW.visita_id IS NOT NULL THEN
        SELECT * INTO v FROM visitas WHERE visita_id=NEW.visita_id FOR SHARE;
        IF NOT FOUND OR (v.tipo,v.mesa_id) IS DISTINCT FROM (NEW.tipo,NEW.mesa_id) THEN
            RAISE EXCEPTION 'La venta debe coincidir con la atención';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_venta BEFORE INSERT ON ventas FOR EACH ROW EXECUTE FUNCTION validar_venta();
CREATE TRIGGER conservar_venta BEFORE UPDATE OR DELETE ON ventas
FOR EACH ROW EXECUTE FUNCTION conservar_datos('venta_id','sucursal_id','usuario_id','visita_id','mesa_id','tipo','fecha');
CREATE TRIGGER conservar_detalle BEFORE UPDATE OR DELETE ON detalle_ventas
FOR EACH ROW EXECUTE FUNCTION conservar_datos('detalle_venta_id','venta_id','producto_id','cantidad','precio_unitario');

CREATE FUNCTION venta_con_detalles() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM detalle_ventas WHERE venta_id=NEW.venta_id) THEN
        RAISE EXCEPTION 'La venta debe tener detalles';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER venta_con_detalles AFTER INSERT ON ventas
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION venta_con_detalles();

CREATE FUNCTION validar_categoria() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.categoria <> OLD.categoria AND (
        EXISTS(SELECT 1 FROM producciones WHERE producto_id=OLD.producto_id) OR
        EXISTS(SELECT 1 FROM detalle_ventas WHERE producto_id=OLD.producto_id)
    ) THEN RAISE EXCEPTION 'No cambiar categoría de un producto utilizado'; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_categoria BEFORE UPDATE ON productos
FOR EACH ROW EXECUTE FUNCTION validar_categoria();

CREATE PROCEDURE registrar_venta(p_sucursal BIGINT,p_usuario BIGINT,p_tipo TEXT,
    p_visita BIGINT,p_mesa BIGINT,p_lineas JSONB,INOUT p_venta BIGINT)
LANGUAGE plpgsql AS $$
DECLARE
    linea RECORD;
    producto productos%ROWTYPE;
    lote RECORD;
    restante INTEGER;
    consumo INTEGER;
BEGIN
    PERFORM validar_operador(p_usuario,p_sucursal);
    IF p_lineas IS NULL OR jsonb_typeof(p_lineas) <> 'array' THEN
        RAISE EXCEPTION 'Se requiere una lista de productos';
    END IF;
    IF jsonb_array_length(p_lineas)=0 OR EXISTS (
        SELECT 1 FROM jsonb_array_elements(p_lineas) AS e
        WHERE jsonb_typeof(e) <> 'object' OR NOT (e ? 'producto_id' AND e ? 'cantidad')
        OR (e->>'producto_id') IS NULL OR (e->>'cantidad') IS NULL
        OR (e->>'cantidad') !~ '^[1-9][0-9]*$' OR (e->>'producto_id') !~ '^[1-9][0-9]*$'
    ) THEN RAISE EXCEPTION 'Productos o cantidades inválidos'; END IF;
    PERFORM 1 FROM sucursales WHERE sucursal_id=p_sucursal AND activa FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Sucursal no disponible'; END IF;
    INSERT INTO ventas(sucursal_id,usuario_id,visita_id,mesa_id,tipo)
    VALUES(p_sucursal,p_usuario,p_visita,p_mesa,p_tipo) RETURNING venta_id INTO p_venta;
    FOR linea IN
        SELECT producto_id,SUM(cantidad)::integer AS cantidad
        FROM jsonb_to_recordset(p_lineas) AS x(producto_id BIGINT,cantidad INTEGER)
        GROUP BY producto_id ORDER BY producto_id
    LOOP
        SELECT * INTO producto FROM productos WHERE producto_id=linea.producto_id AND activo FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Producto no disponible'; END IF;
        IF producto.categoria='bebida' THEN
            PERFORM consumir_receta(p_sucursal,producto.producto_id,linea.cantidad);
        ELSE
            restante := linea.cantidad;
            FOR lote IN
                SELECT produccion_id,cantidad_disponible FROM producciones
                WHERE sucursal_id=p_sucursal AND producto_id=producto.producto_id
                AND cantidad_disponible > 0 AND fecha_vencimiento >=
                    (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date
                ORDER BY fecha_vencimiento,produccion_id FOR UPDATE
            LOOP
                consumo := LEAST(restante,lote.cantidad_disponible);
                UPDATE producciones SET cantidad_disponible=cantidad_disponible-consumo
                WHERE produccion_id=lote.produccion_id;
                restante := restante-consumo;
                EXIT WHEN restante=0;
            END LOOP;
            IF restante > 0 THEN RAISE EXCEPTION 'Producto sin unidades suficientes'; END IF;
        END IF;
        INSERT INTO detalle_ventas(venta_id,producto_id,cantidad,precio_unitario)
        VALUES(p_venta,producto.producto_id,linea.cantidad,producto.precio);
    END LOOP;
END;
$$;

CREATE VIEW v_totales_ventas AS
SELECT v.venta_id,v.sucursal_id,v.visita_id,v.fecha,
    SUM(d.cantidad) AS unidades,SUM(d.cantidad*d.precio_unitario) AS total
FROM ventas v JOIN detalle_ventas d USING(venta_id) GROUP BY v.venta_id;
CREATE INDEX idx_ventas_sucursal_fecha ON ventas(sucursal_id,fecha);
CREATE INDEX idx_ventas_visita ON ventas(visita_id);
CREATE INDEX idx_detalles_producto ON detalle_ventas(producto_id);

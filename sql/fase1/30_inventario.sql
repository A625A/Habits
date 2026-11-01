CREATE TABLE lotes_ingrediente (
    lote_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    inventario_id BIGINT NOT NULL REFERENCES inventario_ingrediente ON DELETE RESTRICT,
    usuario_id BIGINT NOT NULL REFERENCES usuarios ON DELETE RESTRICT,
    recibido_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_vencimiento DATE NOT NULL CHECK (isfinite(fecha_vencimiento)),
    cantidad_inicial NUMERIC(14,3) NOT NULL CHECK (cantidad_inicial > 0 AND cantidad_inicial <> 'NaN'),
    cantidad_disponible NUMERIC(14,3) NOT NULL,
    CHECK (cantidad_disponible BETWEEN 0 AND cantidad_inicial)
);

CREATE TABLE producciones (
    produccion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sucursal_id BIGINT NOT NULL REFERENCES sucursales ON DELETE RESTRICT,
    producto_id BIGINT NOT NULL REFERENCES productos ON DELETE RESTRICT,
    usuario_id BIGINT NOT NULL REFERENCES usuarios ON DELETE RESTRICT,
    producida_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_vencimiento DATE NOT NULL CHECK (isfinite(fecha_vencimiento)),
    cantidad_producida INTEGER NOT NULL CHECK (cantidad_producida > 0),
    cantidad_disponible INTEGER NOT NULL,
    CHECK (cantidad_disponible BETWEEN 0 AND cantidad_producida),
    CHECK (fecha_vencimiento >= (producida_en AT TIME ZONE 'America/Guatemala')::date)
);

CREATE FUNCTION conservar_datos() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE campo TEXT;
BEGIN
    IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Conservar historial de %', TG_TABLE_NAME; END IF;
    FOREACH campo IN ARRAY TG_ARGV LOOP
        IF to_jsonb(NEW)->campo IS DISTINCT FROM to_jsonb(OLD)->campo THEN
            RAISE EXCEPTION 'No se puede cambiar %.%', TG_TABLE_NAME, campo;
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;
CREATE TRIGGER conservar_lote BEFORE UPDATE OR DELETE ON lotes_ingrediente
FOR EACH ROW EXECUTE FUNCTION conservar_datos('lote_id','inventario_id','usuario_id','recibido_en','cantidad_inicial','fecha_vencimiento');
CREATE TRIGGER conservar_produccion BEFORE UPDATE OR DELETE ON producciones
FOR EACH ROW EXECUTE FUNCTION conservar_datos('produccion_id','sucursal_id','producto_id','usuario_id','producida_en','cantidad_producida','fecha_vencimiento');

CREATE FUNCTION validar_inventario() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.sucursal_id,NEW.ingrediente_id) IS DISTINCT FROM (OLD.sucursal_id,OLD.ingrediente_id)
        AND EXISTS(SELECT 1 FROM lotes_ingrediente WHERE inventario_id=OLD.inventario_id) THEN
        RAISE EXCEPTION 'No reasignar inventario con lotes';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_inventario BEFORE UPDATE ON inventario_ingrediente
FOR EACH ROW EXECUTE FUNCTION validar_inventario();

CREATE FUNCTION validar_unidad() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.unidad <> OLD.unidad AND (
        EXISTS(SELECT 1 FROM receta_ingrediente WHERE ingrediente_id=OLD.ingrediente_id) OR
        EXISTS(SELECT 1 FROM inventario_ingrediente WHERE ingrediente_id=OLD.ingrediente_id)
    ) THEN RAISE EXCEPTION 'No cambiar unidad de un ingrediente utilizado'; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_unidad BEFORE UPDATE ON ingredientes
FOR EACH ROW EXECUTE FUNCTION validar_unidad();

CREATE FUNCTION bloquear_receta() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='UPDATE' AND (NEW.producto_id,NEW.ingrediente_id) IS DISTINCT FROM (OLD.producto_id,OLD.ingrediente_id) THEN
        RAISE EXCEPTION 'Eliminar y agregar la fila para cambiar un ingrediente de receta';
    END IF;
    PERFORM 1 FROM productos WHERE producto_id=COALESCE(NEW.producto_id,OLD.producto_id) FOR UPDATE;
    PERFORM 1 FROM ingredientes WHERE ingrediente_id=COALESCE(NEW.ingrediente_id,OLD.ingrediente_id) FOR SHARE;
    RETURN COALESCE(NEW,OLD);
END;
$$;
CREATE TRIGGER bloquear_receta BEFORE INSERT OR UPDATE OR DELETE ON receta_ingrediente
FOR EACH ROW EXECUTE FUNCTION bloquear_receta();

CREATE FUNCTION validar_produccion() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE categoria_actual TEXT;
BEGIN
    PERFORM validar_operador(NEW.usuario_id,NEW.sucursal_id);
    SELECT categoria INTO categoria_actual FROM productos WHERE producto_id=NEW.producto_id AND activo FOR UPDATE;
    IF categoria_actual IS NULL OR categoria_actual NOT IN ('panaderia','postre') THEN
        RAISE EXCEPTION 'Solo producir panadería o postres activos';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_produccion BEFORE INSERT ON producciones
FOR EACH ROW EXECUTE FUNCTION validar_produccion();

CREATE FUNCTION stock_bajo(actual NUMERIC, referencia NUMERIC) RETURNS BOOLEAN
LANGUAGE sql IMMUTABLE STRICT AS $$ SELECT actual <= referencia*0.15; $$;

CREATE VIEW v_stock_ingredientes AS
SELECT i.inventario_id,i.sucursal_id,i.ingrediente_id,i.cantidad_referencia,
    COALESCE(SUM(l.cantidad_disponible) FILTER (WHERE l.fecha_vencimiento >=
        (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date),0) AS cantidad_disponible
FROM inventario_ingrediente i LEFT JOIN lotes_ingrediente l USING(inventario_id)
GROUP BY i.inventario_id;

CREATE VIEW v_stock_terminados AS
SELECT s.sucursal_id,p.producto_id,
    COALESCE(SUM(t.cantidad_disponible) FILTER (WHERE t.fecha_vencimiento >=
        (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date),0) AS cantidad_disponible
FROM sucursales s CROSS JOIN productos p
LEFT JOIN producciones t ON t.sucursal_id=s.sucursal_id AND t.producto_id=p.producto_id
WHERE p.categoria IN ('panaderia','postre') GROUP BY s.sucursal_id,p.producto_id;

CREATE FUNCTION consumir_receta(p_sucursal BIGINT,p_producto BIGINT,p_cantidad INTEGER)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    ingrediente RECORD;
    lote RECORD;
    restante NUMERIC;
    consumo NUMERIC;
BEGIN
    IF p_cantidad IS NULL OR p_cantidad <= 0 THEN RAISE EXCEPTION 'Cantidad inválida'; END IF;
    PERFORM 1 FROM sucursales WHERE sucursal_id=p_sucursal AND activa FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Sucursal no disponible'; END IF;
    PERFORM 1 FROM productos WHERE producto_id=p_producto AND activo FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Producto no disponible'; END IF;
    IF NOT EXISTS(SELECT 1 FROM receta_ingrediente WHERE producto_id=p_producto) THEN
        RAISE EXCEPTION 'Producto sin receta';
    END IF;
    FOR ingrediente IN
        SELECT r.ingrediente_id,r.cantidad,i.activo FROM receta_ingrediente r
        JOIN ingredientes i USING(ingrediente_id) WHERE r.producto_id=p_producto
        ORDER BY r.ingrediente_id FOR SHARE OF i
    LOOP
        IF NOT ingrediente.activo THEN RAISE EXCEPTION 'Ingrediente inactivo'; END IF;
        restante := ingrediente.cantidad*p_cantidad;
        FOR lote IN
            SELECT l.lote_id,l.cantidad_disponible FROM lotes_ingrediente l
            JOIN inventario_ingrediente i USING(inventario_id)
            WHERE i.sucursal_id=p_sucursal AND i.ingrediente_id=ingrediente.ingrediente_id
            AND l.cantidad_disponible > 0 AND l.fecha_vencimiento >=
                (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date
            ORDER BY l.fecha_vencimiento,l.lote_id FOR UPDATE OF l
        LOOP
            consumo := LEAST(restante,lote.cantidad_disponible);
            UPDATE lotes_ingrediente SET cantidad_disponible=cantidad_disponible-consumo WHERE lote_id=lote.lote_id;
            restante := restante-consumo;
            EXIT WHEN restante=0;
        END LOOP;
        IF restante > 0 THEN RAISE EXCEPTION 'Ingrediente sin existencias suficientes'; END IF;
    END LOOP;
END;
$$;

CREATE PROCEDURE registrar_produccion(p_sucursal BIGINT,p_producto BIGINT,p_usuario BIGINT,
    p_cantidad INTEGER,p_vencimiento DATE,INOUT p_produccion BIGINT)
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM validar_operador(p_usuario,p_sucursal);
    PERFORM consumir_receta(p_sucursal,p_producto,p_cantidad);
    INSERT INTO producciones(sucursal_id,producto_id,usuario_id,fecha_vencimiento,cantidad_producida,cantidad_disponible)
    VALUES(p_sucursal,p_producto,p_usuario,p_vencimiento,p_cantidad,p_cantidad)
    RETURNING produccion_id INTO p_produccion;
END;
$$;

CREATE INDEX idx_lotes_fefo ON lotes_ingrediente(inventario_id,fecha_vencimiento,lote_id)
WHERE cantidad_disponible > 0;
CREATE INDEX idx_producciones_fefo ON producciones(sucursal_id,producto_id,fecha_vencimiento,produccion_id)
WHERE cantidad_disponible > 0;

CREATE TRIGGER auditar_mesas
AFTER INSERT OR UPDATE OR DELETE ON mesas
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('mesa_id', 'mesa_id', 'sucursal_id', 'numero_mesa', 'capacidad', 'activa');

CREATE TRIGGER auditar_clientes
AFTER INSERT OR UPDATE OR DELETE ON clientes
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('cliente_id', 'cliente_id', 'activo');

CREATE TRIGGER auditar_productos
AFTER INSERT OR UPDATE OR DELETE ON productos
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('producto_id', 'producto_id', 'codigo', 'nombre', 'categoria', 'precio', 'activo');

CREATE TRIGGER auditar_ingredientes
AFTER INSERT OR UPDATE OR DELETE ON ingredientes
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('ingrediente_id', 'ingrediente_id', 'nombre', 'unidad', 'activo');

CREATE TRIGGER auditar_receta_ingrediente
AFTER INSERT OR UPDATE OR DELETE ON receta_ingrediente
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('receta_ingrediente_id', 'receta_ingrediente_id', 'producto_id', 'ingrediente_id', 'cantidad');

CREATE TRIGGER auditar_inventario_ingrediente
AFTER INSERT OR UPDATE OR DELETE ON inventario_ingrediente
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('inventario_id', 'inventario_id', 'sucursal_id', 'ingrediente_id', 'cantidad_referencia');

CREATE TRIGGER auditar_lotes_ingrediente
AFTER INSERT OR UPDATE OR DELETE ON lotes_ingrediente
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('lote_id', 'lote_id', 'inventario_id', 'usuario_id', 'recibido_en', 'fecha_vencimiento', 'cantidad_inicial', 'cantidad_disponible');

CREATE TRIGGER auditar_producciones
AFTER INSERT OR UPDATE OR DELETE ON producciones
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('produccion_id', 'produccion_id', 'sucursal_id', 'producto_id', 'usuario_id', 'producida_en', 'fecha_vencimiento', 'cantidad_producida', 'cantidad_disponible');

CREATE TRIGGER auditar_preferencias_cliente
AFTER INSERT OR UPDATE OR DELETE ON preferencias_cliente
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('preferencia_id', 'preferencia_id', 'cliente_id', 'producto_id', 'nota_preferencia');

CREATE TRIGGER auditar_reservas
AFTER INSERT OR UPDATE OR DELETE ON reservas
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('reserva_id', 'reserva_id', 'sucursal_id', 'mesa_id', 'cliente_id', 'fecha_inicio', 'fecha_fin', 'personas', 'estado');

CREATE TRIGGER auditar_visitas
AFTER INSERT OR UPDATE OR DELETE ON visitas
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('visita_id', 'visita_id', 'cliente_id', 'sucursal_id', 'reserva_id', 'mesa_id', 'tipo', 'atendida_en', 'usuario_id');

CREATE TRIGGER auditar_observaciones_cliente
AFTER INSERT OR UPDATE OR DELETE ON observaciones_cliente
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('observacion_id', 'observacion_id', 'cliente_id', 'visita_id', 'usuario_id', 'observacion', 'fecha_creacion');

CREATE TRIGGER auditar_ventas
AFTER INSERT OR UPDATE OR DELETE ON ventas
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('venta_id', 'venta_id', 'sucursal_id', 'usuario_id', 'visita_id', 'mesa_id', 'tipo', 'fecha');

CREATE TRIGGER auditar_detalle_ventas
AFTER INSERT OR UPDATE OR DELETE ON detalle_ventas
FOR EACH ROW EXECUTE FUNCTION auditar_cambio('detalle_venta_id', 'detalle_venta_id', 'venta_id', 'producto_id', 'cantidad', 'precio_unitario');

CREATE FUNCTION validar_operador(p_usuario BIGINT,p_sucursal BIGINT) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM 1 FROM sucursales WHERE sucursal_id=p_sucursal AND activa FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Sucursal no disponible'; END IF;
    PERFORM 1 FROM usuarios WHERE usuario_id=p_usuario AND activo
        AND (rol='administrador' OR sucursal_id=p_sucursal) FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Personal no autorizado para esta sucursal'; END IF;
    PERFORM set_config('habits.usuario_id',p_usuario::text,true);
END;
$$;

CREATE FUNCTION bloquear_ingrediente_inventario() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM 1 FROM ingredientes WHERE ingrediente_id=NEW.ingrediente_id FOR SHARE;
    RETURN NEW;
END;
$$;
CREATE TRIGGER bloquear_ingrediente_inventario BEFORE INSERT OR UPDATE ON inventario_ingrediente
FOR EACH ROW EXECUTE FUNCTION bloquear_ingrediente_inventario();

CREATE FUNCTION validar_entrada_lote() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE sede BIGINT;
BEGIN
    SELECT sucursal_id INTO sede FROM inventario_ingrediente WHERE inventario_id=NEW.inventario_id FOR SHARE;
    PERFORM validar_operador(NEW.usuario_id,sede);
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_entrada_lote BEFORE INSERT ON lotes_ingrediente
FOR EACH ROW EXECUTE FUNCTION validar_entrada_lote();

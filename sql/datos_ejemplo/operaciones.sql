-- Personas y compras ficticias. Ejecutar mediante cargar_demo.psql.
-- Los correos example.test identifican este conjunto; no se envían mensajes.
DO $$
DECLARE
    operador BIGINT := current_setting('habits.usuario_carga')::BIGINT;
    sede RECORD;
    persona RECORD;
    producto RECORD;
    cliente BIGINT;
    mesa BIGINT;
    reserva BIGINT;
    visita BIGINT;
    produccion BIGINT;
    venta BIGINT;
    bebida BIGINT;
    terminado BIGINT;
    primera_visita BIGINT;
    numero INTEGER;
    orden INTEGER;
    recibidos INTEGER;
    correo TEXT;
    instante TIMESTAMPTZ := CURRENT_TIMESTAMP;
    hoy DATE := (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM usuarios
        WHERE usuario_id=operador AND activo AND rol='administrador') THEN
        RAISE EXCEPTION 'Elegir un administrador activo para la demostración';
    END IF;

    -- Si el conjunto ya está completo, no se repiten compras ni se repone stock.
    SELECT count(*) INTO recibidos FROM clientes
    WHERE lower(email) IN (
        'habits.demo.1.1@example.test','habits.demo.1.2@example.test','habits.demo.1.3@example.test',
        'habits.demo.2.1@example.test','habits.demo.2.2@example.test','habits.demo.2.3@example.test');
    IF recibidos > 0 THEN
        IF recibidos <> 6 OR EXISTS (
            SELECT 1 FROM clientes c
            WHERE lower(c.email) IN (
                'habits.demo.1.1@example.test','habits.demo.1.2@example.test','habits.demo.1.3@example.test',
                'habits.demo.2.1@example.test','habits.demo.2.2@example.test','habits.demo.2.3@example.test')
            AND (NOT EXISTS (SELECT 1 FROM visitas v WHERE v.cliente_id=c.cliente_id)
                 OR NOT EXISTS (SELECT 1 FROM reservas r WHERE r.cliente_id=c.cliente_id)
                 OR NOT EXISTS (SELECT 1 FROM ventas x JOIN visitas v USING(visita_id)
                                WHERE v.cliente_id=c.cliente_id))
        ) THEN
            RAISE EXCEPTION 'Los correos reservados de la demo ya tienen datos incompletos; revisar sin borrarlos';
        END IF;
        RAISE NOTICE 'La demostración ya fue cargada; se conservan sus operaciones y existencias';
        RETURN;
    END IF;

    FOR sede IN SELECT sucursal_id,codigo FROM sucursales
        WHERE codigo IN ('DEMO-01','DEMO-02') ORDER BY codigo
    LOOP
        numero := CASE sede.codigo WHEN 'DEMO-01' THEN 1 ELSE 2 END;
        -- Preparar cuatro unidades de cada pan y postre usando las recetas reales de la base.
        FOR producto IN SELECT producto_id FROM productos
            WHERE codigo IN ('HAB-07','HAB-08','HAB-09','HAB-10','HAB-11','HAB-12') ORDER BY codigo
        LOOP
            CALL registrar_produccion(sede.sucursal_id,producto.producto_id,operador,4,hoy+2,produccion);
        END LOOP;

        orden := 0;
        primera_visita := NULL;
        FOR persona IN SELECT * FROM (VALUES
            (1,'Ana Ejemplo',3),(2,'Luis Ejemplo',2),(3,'Sofía Ejemplo',1)
        ) AS lista(indice,nombre,visitas)
        LOOP
            correo := format('habits.demo.%s.%s@example.test',numero,persona.indice);
            INSERT INTO clientes(nombre,telefono,email)
            VALUES (persona.nombre || ' · Sucursal ' || numero,'DEMO-' || numero || persona.indice,correo)
            RETURNING cliente_id INTO cliente;

            -- Dos preferencias por persona para mostrar productos distintos en el reporte.
            INSERT INTO preferencias_cliente(cliente_id,producto_id,nota_preferencia)
            SELECT cliente,p.producto_id,'Preferencia ficticia para la presentación'
            FROM productos p WHERE p.codigo IN (
                'HAB-' || lpad(persona.indice::text,2,'0'),
                'HAB-' || lpad((persona.indice+6)::text,2,'0'));

            -- Buscar una mesa libre en vez de mover o cancelar reservas de otras personas.
            SELECT m.mesa_id INTO mesa FROM mesas m
            WHERE m.sucursal_id=sede.sucursal_id AND m.activa AND m.capacidad>=2
            AND NOT EXISTS (SELECT 1 FROM reservas r WHERE r.mesa_id=m.mesa_id
                AND r.estado IN ('pendiente','confirmada','completada')
                AND tstzrange(r.fecha_inicio,r.fecha_fin,'[)') &&
                    tstzrange(instante,instante+interval '90 minutes','[)'))
            ORDER BY m.numero_mesa LIMIT 1 FOR UPDATE;
            IF mesa IS NULL THEN
                RAISE EXCEPTION 'No hay mesa libre para la demostración en %; no se cambiaron reservas existentes',sede.codigo;
            END IF;
            INSERT INTO reservas(sucursal_id,mesa_id,cliente_id,fecha_inicio,fecha_fin,personas,estado)
            VALUES(sede.sucursal_id,mesa,cliente,instante,instante+interval '90 minutes',2,'confirmada')
            RETURNING reserva_id INTO reserva;

            FOR numero_visita IN 1..persona.visitas LOOP
                IF numero_visita=1 THEN
                    CALL registrar_llegada(reserva,operador,visita);
                ELSE
                    -- Son otras atenciones, para llevar, sin duplicar la llegada de la reserva.
                    INSERT INTO visitas(cliente_id,sucursal_id,tipo,usuario_id)
                    VALUES(cliente,sede.sucursal_id,'llevar',operador) RETURNING visita_id INTO visita;
                END IF;
                IF primera_visita IS NULL THEN primera_visita := visita; END IF;
                orden := orden+1;
                SELECT producto_id INTO bebida FROM productos WHERE codigo='HAB-' || lpad(orden::text,2,'0');
                SELECT producto_id INTO terminado FROM productos WHERE codigo='HAB-' || lpad((orden+6)::text,2,'0');
                CALL registrar_venta(sede.sucursal_id,operador,
                    CASE WHEN numero_visita=1 THEN 'local' ELSE 'llevar' END,visita,
                    CASE WHEN numero_visita=1 THEN mesa ELSE NULL END,
                    jsonb_build_array(jsonb_build_object('producto_id',bebida,'cantidad',numero),
                                      jsonb_build_object('producto_id',terminado,'cantidad',1)),venta);
            END LOOP;

            IF persona.indice=1 THEN
                -- Una reserva futura confirmada y otra cancelada conservan ambos estados.
                INSERT INTO reservas(sucursal_id,mesa_id,cliente_id,fecha_inicio,fecha_fin,personas,estado)
                VALUES(sede.sucursal_id,mesa,cliente,instante+interval '1 day',
                       instante+interval '1 day 90 minutes',2,'confirmada');
                INSERT INTO reservas(sucursal_id,mesa_id,cliente_id,fecha_inicio,fecha_fin,personas,estado)
                VALUES(sede.sucursal_id,mesa,cliente,instante+interval '2 days',
                       instante+interval '2 days 90 minutes',2,'confirmada')
                RETURNING reserva_id INTO reserva;
                CALL cancelar_reserva(reserva);
            END IF;
        END LOOP;

        -- Dos compras de una misma atención siguen contando como una sola visita.
        SELECT producto_id INTO bebida FROM productos WHERE codigo='HAB-01';
        SELECT mesa_id INTO mesa FROM visitas WHERE visita_id=primera_visita;
        CALL registrar_venta(sede.sucursal_id,operador,'local',primera_visita,mesa,
            jsonb_build_array(jsonb_build_object('producto_id',bebida,'cantidad',1)),venta);

        -- Dejar un lote con saldo que vence hoy garantiza una alerta en el mes actual,
        -- incluso si la demo se carga el último día del mes.
        INSERT INTO lotes_ingrediente(inventario_id,usuario_id,fecha_vencimiento,cantidad_inicial,cantidad_disponible)
        SELECT i.inventario_id,operador,hoy,25,25 FROM inventario_ingrediente i
        JOIN ingredientes g USING(ingrediente_id)
        WHERE i.sucursal_id=sede.sucursal_id AND lower(g.nombre)=lower('Café');
    END LOOP;
END;
$$;

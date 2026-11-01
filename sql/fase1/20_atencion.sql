CREATE TABLE reservas (
    reserva_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sucursal_id BIGINT NOT NULL REFERENCES sucursales ON DELETE RESTRICT,
    mesa_id BIGINT NOT NULL,
    cliente_id BIGINT NOT NULL REFERENCES clientes ON DELETE RESTRICT,
    fecha_inicio TIMESTAMPTZ NOT NULL CHECK (isfinite(fecha_inicio)),
    fecha_fin TIMESTAMPTZ NOT NULL,
    personas INTEGER NOT NULL CHECK (personas > 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','confirmada','completada','cancelada')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mesa_id,sucursal_id) REFERENCES mesas(mesa_id,sucursal_id) ON DELETE RESTRICT,
    UNIQUE (reserva_id,sucursal_id,cliente_id,mesa_id),
    CHECK (fecha_fin = fecha_inicio + interval '90 minutes'),
    EXCLUDE USING gist (mesa_id WITH =, tstzrange(fecha_inicio,fecha_fin,'[)') WITH &&)
        WHERE (estado IN ('pendiente','confirmada','completada'))
);

CREATE TABLE visitas (
    visita_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes ON DELETE RESTRICT,
    sucursal_id BIGINT NOT NULL REFERENCES sucursales ON DELETE RESTRICT,
    reserva_id BIGINT UNIQUE,
    mesa_id BIGINT,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('local','llevar')),
    atendida_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    usuario_id BIGINT NOT NULL REFERENCES usuarios ON DELETE RESTRICT,
    FOREIGN KEY (mesa_id,sucursal_id) REFERENCES mesas(mesa_id,sucursal_id) ON DELETE RESTRICT,
    FOREIGN KEY (reserva_id,sucursal_id,cliente_id,mesa_id)
        REFERENCES reservas(reserva_id,sucursal_id,cliente_id,mesa_id) ON DELETE RESTRICT,
    CHECK (tipo <> 'llevar' OR (mesa_id IS NULL AND reserva_id IS NULL)),
    CHECK (reserva_id IS NULL OR mesa_id IS NOT NULL),
    UNIQUE (visita_id,sucursal_id),
    UNIQUE (visita_id,cliente_id)
);

CREATE TABLE observaciones_cliente (
    observacion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes ON DELETE RESTRICT,
    visita_id BIGINT,
    usuario_id BIGINT NOT NULL REFERENCES usuarios ON DELETE RESTRICT,
    observacion TEXT NOT NULL CHECK (btrim(observacion) <> ''),
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (visita_id,cliente_id) REFERENCES visitas(visita_id,cliente_id) ON DELETE RESTRICT
);

CREATE FUNCTION validar_reserva() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    mesa mesas%ROWTYPE;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Conservar reservas; cancelar en lugar de borrar';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF (NEW.reserva_id,NEW.sucursal_id,NEW.mesa_id,NEW.cliente_id,NEW.fecha_inicio,NEW.fecha_fin)
            IS DISTINCT FROM
           (OLD.reserva_id,OLD.sucursal_id,OLD.mesa_id,OLD.cliente_id,OLD.fecha_inicio,OLD.fecha_fin) THEN
            RAISE EXCEPTION 'Conservar identidad y horario; cancelar y crear otra reserva';
        END IF;
        IF NEW.estado <> OLD.estado AND NOT (
            (OLD.estado='pendiente' AND NEW.estado IN ('confirmada','cancelada')) OR
            (OLD.estado='confirmada' AND NEW.estado IN ('completada','cancelada'))
        ) THEN
            RAISE EXCEPTION 'Transición de reserva inválida';
        END IF;
        IF OLD.estado IN ('completada','cancelada') AND NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION 'La reserva ya finalizó';
        END IF;
    END IF;
    SELECT * INTO mesa FROM mesas WHERE mesa_id=NEW.mesa_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Mesa inexistente';
    END IF;
    IF TG_OP='INSERT' OR NEW.personas IS DISTINCT FROM OLD.personas THEN
        IF NEW.personas > mesa.capacidad THEN
            RAISE EXCEPTION 'Capacidad insuficiente';
        END IF;
    END IF;
    IF TG_OP='INSERT' THEN
        IF NOT mesa.activa OR NOT EXISTS (SELECT 1 FROM sucursales WHERE sucursal_id=NEW.sucursal_id AND activa)
            OR NOT EXISTS (SELECT 1 FROM clientes WHERE cliente_id=NEW.cliente_id AND activo) THEN
            RAISE EXCEPTION 'Mesa, sucursal o cliente inactivo';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_reserva BEFORE INSERT OR UPDATE OR DELETE ON reservas
FOR EACH ROW EXECUTE FUNCTION validar_reserva();

CREATE FUNCTION validar_capacidad_mesa() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.capacidad < OLD.capacidad AND EXISTS (
        SELECT 1 FROM reservas WHERE mesa_id=OLD.mesa_id AND estado <> 'cancelada'
        AND fecha_fin > clock_timestamp() AND personas > NEW.capacidad
    ) THEN
        RAISE EXCEPTION 'Capacidad incompatible con reservas vigentes';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_capacidad_mesa BEFORE UPDATE ON mesas
FOR EACH ROW EXECUTE FUNCTION validar_capacidad_mesa();

CREATE FUNCTION comprobar_llegada() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    id BIGINT;
    estado_actual TEXT;
    hay_visita BOOLEAN;
BEGIN
    id := NEW.reserva_id;
    IF id IS NULL THEN RETURN NULL; END IF;
    SELECT estado INTO estado_actual FROM reservas WHERE reserva_id=id FOR UPDATE;
    SELECT EXISTS(SELECT 1 FROM visitas WHERE reserva_id=id) INTO hay_visita;
    IF (estado_actual='completada') IS DISTINCT FROM hay_visita THEN
        RAISE EXCEPTION 'Reserva completada y visita deben registrarse juntas';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER comprobar_llegada_reserva AFTER INSERT OR UPDATE ON reservas
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION comprobar_llegada();
CREATE CONSTRAINT TRIGGER comprobar_llegada_visita AFTER INSERT ON visitas
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION comprobar_llegada();

CREATE FUNCTION proteger_visita() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'La visita real se conserva sin modificar';
    END IF;
    IF NOT isfinite(NEW.atendida_en) OR NEW.atendida_en > clock_timestamp() THEN
        RAISE EXCEPTION 'Una visita no puede tener fecha futura';
    END IF;
    PERFORM validar_operador(NEW.usuario_id,NEW.sucursal_id);
    PERFORM 1 FROM clientes WHERE cliente_id=NEW.cliente_id AND activo FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Cliente inactivo'; END IF;
    IF NEW.mesa_id IS NOT NULL THEN
        PERFORM 1 FROM mesas WHERE mesa_id=NEW.mesa_id AND activa FOR SHARE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Mesa inactiva'; END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER proteger_visita BEFORE INSERT OR UPDATE OR DELETE ON visitas
FOR EACH ROW EXECUTE FUNCTION proteger_visita();

CREATE PROCEDURE registrar_llegada(p_reserva BIGINT, p_usuario BIGINT, INOUT p_visita BIGINT)
LANGUAGE plpgsql AS $$
DECLARE
    r reservas%ROWTYPE;
BEGIN
    SELECT * INTO r FROM reservas WHERE reserva_id=p_reserva FOR UPDATE;
    IF NOT FOUND OR r.estado <> 'confirmada' THEN
        RAISE EXCEPTION 'La reserva debe estar confirmada';
    END IF;
    PERFORM validar_operador(p_usuario,r.sucursal_id);
    INSERT INTO visitas(cliente_id,sucursal_id,reserva_id,mesa_id,tipo,usuario_id)
    VALUES (r.cliente_id,r.sucursal_id,r.reserva_id,r.mesa_id,'local',p_usuario)
    RETURNING visita_id INTO p_visita;
    UPDATE reservas SET estado='completada' WHERE reserva_id=p_reserva;
END;
$$;

CREATE PROCEDURE cancelar_reserva(p_reserva BIGINT) LANGUAGE plpgsql AS $$
BEGIN
    UPDATE reservas SET estado='cancelada'
    WHERE reserva_id=p_reserva AND estado IN ('pendiente','confirmada');
    IF NOT FOUND THEN RAISE EXCEPTION 'Reserva no cancelable'; END IF;
END;
$$;

CREATE INDEX idx_reservas_cliente_fecha ON reservas(cliente_id,fecha_inicio);
CREATE INDEX idx_reservas_sucursal_fecha ON reservas(sucursal_id,fecha_inicio);
CREATE INDEX idx_visitas_cliente_fecha ON visitas(cliente_id,atendida_en);
CREATE INDEX idx_visitas_sucursal_fecha ON visitas(sucursal_id,atendida_en);
CREATE INDEX idx_observaciones_cliente_fecha ON observaciones_cliente(cliente_id,fecha_creacion);

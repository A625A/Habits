-- Extensión requerida para índices de exclusión GiST con tipos de datos estándar
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- 1. Catálogo de mesas por sucursal
CREATE TABLE IF NOT EXISTS mesas (
    mesa_id SERIAL PRIMARY KEY,
    sucursal_id INT NOT NULL REFERENCES sucursales(sucursal_id) ON DELETE CASCADE,
    numero_mesa INT NOT NULL,
    capacidad INT NOT NULL CHECK (capacidad > 0),
    ubicacion VARCHAR(50) DEFAULT 'Interior',
    CONSTRAINT uq_sucursal_mesa UNIQUE (sucursal_id, numero_mesa)
);

-- 2. Registro de clientes
CREATE TABLE IF NOT EXISTS clientes (
    cliente_id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    email VARCHAR(120) UNIQUE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Preferencias y observaciones asociadas al cliente
CREATE TABLE IF NOT EXISTS preferencias_cliente (
    preferencia_id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    producto_id INT REFERENCES productos(producto_id) ON DELETE SET NULL,
    nota_preferencia VARCHAR(150),
    CONSTRAINT uq_cliente_producto UNIQUE (cliente_id, producto_id)
);

CREATE TABLE IF NOT EXISTS observaciones_cliente (
    observacion_id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    observacion TEXT NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Reservas con control de concurrencia y prevención de traslapes
CREATE TABLE IF NOT EXISTS reservas (
    reserva_id SERIAL PRIMARY KEY,
    sucursal_id INT NOT NULL REFERENCES sucursales(sucursal_id),
    mesa_id INT NOT NULL REFERENCES mesas(mesa_id),
    cliente_id INT NOT NULL REFERENCES clientes(cliente_id),
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_fin TIMESTAMP NOT NULL,
    personas INT NOT NULL CHECK (personas > 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' 
        CHECK (estado IN ('pendiente', 'confirmada', 'completada', 'cancelada')),
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_duracion_valida CHECK (fecha_fin > fecha_inicio),
    -- Regla crítica: la mesa no puede ocuparse dos veces en rangos que coincidan
    CONSTRAINT no_traslape_mesa EXCLUDE USING gist (
        mesa_id WITH =,
        tsrange(fecha_inicio, fecha_fin, '[)') WITH &&
    ) WHERE (estado IN ('pendiente', 'confirmada'))
);

-- Índices para optimizar búsquedas e historiales
CREATE INDEX IF NOT EXISTS idx_reservas_cliente ON reservas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_reservas_sucursal_fecha ON reservas(sucursal_id, fecha_inicio);
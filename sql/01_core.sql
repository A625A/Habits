-- Fase 1, Andrew. Ejecutar dentro de una transacción contra una BD vacía.
-- Nunca se ejecuta al arrancar Flask. No borra ni reemplaza tablas existentes.
CREATE TABLE sucursales (
    sucursal_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE CHECK (BTRIM(codigo) <> ''),
    nombre VARCHAR(120) NOT NULL CHECK (BTRIM(nombre) <> ''),
    direccion TEXT,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE usuarios (
    usuario_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(sucursal_id) ON DELETE RESTRICT,
    nombre VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL,
    password_hash TEXT NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('administrador', 'mesero', 'gerente')),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Búsquedas de personal por sucursal y validación de referencias al eliminar sedes.
CREATE INDEX idx_usuarios_sucursal ON usuarios(sucursal_id);

CREATE UNIQUE INDEX uq_usuarios_email ON usuarios(LOWER(email));

ALTER TABLE usuarios
    ADD CONSTRAINT ck_usuarios_nombre CHECK (BTRIM(nombre) <> ''),
    ADD CONSTRAINT ck_usuarios_email CHECK (email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
    ADD CONSTRAINT ck_usuarios_password_hash CHECK (BTRIM(password_hash) <> '');

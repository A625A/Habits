CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;

CREATE TABLE mesas (
    mesa_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sucursal_id BIGINT NOT NULL REFERENCES sucursales ON DELETE RESTRICT,
    numero_mesa INTEGER NOT NULL CHECK (numero_mesa > 0),
    capacidad INTEGER NOT NULL CHECK (capacidad > 0),
    activa BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (sucursal_id, numero_mesa),
    UNIQUE (mesa_id, sucursal_id)
);

CREATE TABLE clientes (
    cliente_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL CHECK (btrim(nombre) <> ''),
    telefono VARCHAR(30) CHECK (btrim(telefono) <> ''),
    email VARCHAR(254) CHECK (email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
    activo BOOLEAN NOT NULL DEFAULT true,
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (telefono IS NOT NULL OR email IS NOT NULL)
);
CREATE UNIQUE INDEX uq_clientes_email ON clientes(lower(email));

CREATE TABLE productos (
    producto_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE CHECK (btrim(codigo) <> ''),
    nombre VARCHAR(120) NOT NULL CHECK (btrim(nombre) <> ''),
    categoria VARCHAR(20) NOT NULL CHECK (categoria IN ('bebida', 'panaderia', 'postre')),
    precio NUMERIC(12,2) NOT NULL CHECK (precio > 0 AND precio <> 'NaN'),
    activo BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE ingredientes (
    ingrediente_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL CHECK (btrim(nombre) <> ''),
    unidad VARCHAR(10) NOT NULL CHECK (unidad IN ('g', 'ml', 'unidad')),
    activo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX uq_ingredientes_nombre ON ingredientes(lower(nombre));

CREATE TABLE receta_ingrediente (
    receta_ingrediente_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto_id BIGINT NOT NULL REFERENCES productos ON DELETE RESTRICT,
    ingrediente_id BIGINT NOT NULL REFERENCES ingredientes ON DELETE RESTRICT,
    cantidad NUMERIC(14,3) NOT NULL CHECK (cantidad > 0 AND cantidad <> 'NaN'),
    UNIQUE (producto_id, ingrediente_id)
);

CREATE TABLE inventario_ingrediente (
    inventario_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sucursal_id BIGINT NOT NULL REFERENCES sucursales ON DELETE RESTRICT,
    ingrediente_id BIGINT NOT NULL REFERENCES ingredientes ON DELETE RESTRICT,
    cantidad_referencia NUMERIC(14,3) NOT NULL
        CHECK (cantidad_referencia > 0 AND cantidad_referencia <> 'NaN'),
    UNIQUE (sucursal_id, ingrediente_id)
);

CREATE TABLE preferencias_cliente (
    preferencia_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes ON DELETE RESTRICT,
    producto_id BIGINT NOT NULL REFERENCES productos ON DELETE RESTRICT,
    nota_preferencia VARCHAR(150),
    UNIQUE (cliente_id, producto_id)
);

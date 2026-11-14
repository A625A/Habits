-- Instalación única. No utiliza ni modifica tablas de Proyecto 2.
BEGIN;

CREATE SCHEMA olap;

CREATE TABLE olap.dim_fecha (
    fecha DATE PRIMARY KEY CHECK (fecha BETWEEN DATE '2025-11-01' AND DATE '2026-10-31'),
    dia SMALLINT GENERATED ALWAYS AS (EXTRACT(DAY FROM fecha)::smallint) STORED,
    mes SMALLINT GENERATED ALWAYS AS (EXTRACT(MONTH FROM fecha)::smallint) STORED,
    trimestre SMALLINT GENERATED ALWAYS AS (EXTRACT(QUARTER FROM fecha)::smallint) STORED,
    anio SMALLINT GENERATED ALWAYS AS (EXTRACT(YEAR FROM fecha)::smallint) STORED
);

CREATE TABLE olap.dim_producto (
    producto_id BIGINT PRIMARY KEY CHECK (producto_id > 0),
    codigo VARCHAR(30) NOT NULL UNIQUE CHECK (btrim(codigo) <> ''),
    nombre VARCHAR(120) NOT NULL CHECK (btrim(nombre) <> ''),
    categoria VARCHAR(20) NOT NULL CHECK (categoria IN ('bebida', 'panaderia', 'postre'))
);

CREATE TABLE olap.dim_sucursal (
    sucursal_id BIGINT PRIMARY KEY CHECK (sucursal_id > 0),
    codigo VARCHAR(30) NOT NULL UNIQUE CHECK (btrim(codigo) <> ''),
    nombre VARCHAR(120) NOT NULL CHECK (btrim(nombre) <> '')
);

CREATE TABLE olap.dim_tipo_venta (
    tipo_venta VARCHAR(10) PRIMARY KEY CHECK (tipo_venta IN ('local', 'llevar'))
);

CREATE TABLE olap.fact_ventas (
    detalle_id BIGINT PRIMARY KEY CHECK (detalle_id > 0),
    ticket_id BIGINT NOT NULL CHECK (ticket_id > 0),
    fecha DATE NOT NULL REFERENCES olap.dim_fecha(fecha) ON DELETE RESTRICT,
    producto_id BIGINT NOT NULL REFERENCES olap.dim_producto(producto_id) ON DELETE RESTRICT,
    sucursal_id BIGINT NOT NULL REFERENCES olap.dim_sucursal(sucursal_id) ON DELETE RESTRICT,
    tipo_venta VARCHAR(10) NOT NULL REFERENCES olap.dim_tipo_venta(tipo_venta) ON DELETE RESTRICT,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12,2) NOT NULL CHECK (precio_unitario > 0 AND precio_unitario <> 'NaN'),
    importe NUMERIC(22,2) GENERATED ALWAYS AS (cantidad::numeric * precio_unitario) STORED,
    UNIQUE (ticket_id, producto_id)
);

-- UNIQUE(ticket_id,producto_id) ya cubre búsquedas por ticket.
CREATE INDEX idx_fact_ventas_fecha ON olap.fact_ventas(fecha);
CREATE INDEX idx_fact_ventas_producto ON olap.fact_ventas(producto_id);
CREATE INDEX idx_fact_ventas_sucursal_fecha ON olap.fact_ventas(sucursal_id, fecha);
CREATE INDEX idx_fact_ventas_tipo ON olap.fact_ventas(tipo_venta);

INSERT INTO olap.dim_fecha(fecha)
SELECT DATE '2025-11-01' + n FROM generate_series(0, 364) AS dias(n);
INSERT INTO olap.dim_tipo_venta(tipo_venta) VALUES ('local'), ('llevar');

COMMENT ON TABLE olap.fact_ventas IS
'Un producto por ticket simulado; IDs globales del ETL, independientes del OLTP. Importes en GTQ.';
COMMENT ON COLUMN olap.fact_ventas.ticket_id IS
'Dimensión degenerada. Mismo ticket: misma fecha, sucursal y tipo; verificar antes del COMMIT del ETL.';
COMMENT ON COLUMN olap.fact_ventas.precio_unitario IS
'Precio histórico cobrado por unidad, nunca el precio actual del catálogo.';

COMMIT;

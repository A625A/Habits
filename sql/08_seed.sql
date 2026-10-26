-- Datos ficticios para desarrollo. No son nombres comerciales aprobados.
-- No contiene usuarios, contraseñas, productos ni precios inventados.
INSERT INTO sucursales (codigo, nombre)
VALUES ('DEMO-01', 'Sucursal demo 1'), ('DEMO-02', 'Sucursal demo 2')
ON CONFLICT (codigo) DO NOTHING;

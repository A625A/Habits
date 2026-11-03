-- Datos ficticios para practicar; las cantidades no son recetas comerciales.
-- Ejecutar con cargar.psql para guardar todo junto o deshacerlo si hay un error.
DO $$
DECLARE
    operador BIGINT := current_setting('habits.usuario_carga')::BIGINT;
BEGIN
    -- Un administrador puede registrar entradas para las dos sucursales.
    IF NOT EXISTS (SELECT 1 FROM usuarios
        WHERE usuario_id=operador AND activo AND rol='administrador') THEN
        RAISE EXCEPTION 'Elegir un administrador activo para la carga de ejemplo';
    END IF;
    IF (SELECT count(*) FROM sucursales
        WHERE codigo IN ('DEMO-01','DEMO-02') AND activa) <> 2 THEN
        RAISE EXCEPTION 'Se necesitan las dos sucursales activas del catálogo inicial';
    END IF;
    IF (SELECT count(*) FROM productos
        WHERE codigo IN ('HAB-01','HAB-02','HAB-03','HAB-04','HAB-05','HAB-06',
                         'HAB-07','HAB-08','HAB-09','HAB-10','HAB-11','HAB-12')
        AND activo) <> 12 THEN
        RAISE EXCEPTION 'Primero cargar los doce productos del catálogo inicial';
    END IF;
END;
$$;

-- Cada sede tiene mesas para grupos pequeños, medianos y grandes.
INSERT INTO mesas(sucursal_id,numero_mesa,capacidad)
SELECT s.sucursal_id,m.numero,m.capacidad
FROM sucursales s CROSS JOIN (VALUES (1,2),(2,4),(3,6)) AS m(numero,capacidad)
WHERE s.codigo IN ('DEMO-01','DEMO-02')
ON CONFLICT (sucursal_id,numero_mesa) DO NOTHING;

DO $$
DECLARE
    insumo RECORD;
    id_ingrediente BIGINT;
    unidad_actual TEXT;
BEGIN
    FOR insumo IN SELECT * FROM (VALUES
        ('Café','g'),('Leche','ml'),('Cardamomo','g'),('Miel','g'),
        ('Chocolate','g'),('Panela','g'),('Naranja','ml'),('Vainilla','ml'),
        ('Canela','g'),('Chai','g'),('Harina','g'),('Mantequilla','g'),
        ('Guayaba','g'),('Queso crema','g'),('Azúcar','g'),('Huevo','unidad'),
        ('Banano','g'),('Espinaca','g'),('Tomate','g'),('Avellana','g')
    ) AS lista(nombre,unidad) LOOP
        INSERT INTO ingredientes(nombre,unidad) VALUES (insumo.nombre,insumo.unidad)
        ON CONFLICT (lower(nombre)) DO NOTHING;
        SELECT ingrediente_id,unidad INTO id_ingrediente,unidad_actual
        FROM ingredientes WHERE lower(nombre)=lower(insumo.nombre);
        -- No mezclar gramos y mililitros si el ingrediente ya estaba registrado.
        IF unidad_actual <> insumo.unidad OR NOT EXISTS (
            SELECT 1 FROM ingredientes WHERE ingrediente_id=id_ingrediente AND activo
        ) THEN
            RAISE EXCEPTION 'Revisar unidad o estado del ingrediente %',insumo.nombre;
        END IF;
    END LOOP;
END;
$$;

-- Una receta indica lo necesario para una unidad del producto.
-- Si un producto ya tiene receta, se conserva completa sin agregarle ingredientes.
WITH recetas(codigo,nombre,cantidad) AS (VALUES
    ('HAB-01','Café',18),('HAB-01','Leche',200),('HAB-01','Cardamomo',1),('HAB-01','Miel',15),
    ('HAB-02','Café',18),('HAB-02','Leche',200),('HAB-02','Chocolate',25),
    ('HAB-03','Café',25),('HAB-03','Panela',20),('HAB-03','Naranja',50),
    ('HAB-04','Café',18),('HAB-04','Leche',200),('HAB-04','Vainilla',5),('HAB-04','Canela',1),
    ('HAB-05','Café',18),('HAB-05','Chai',10),('HAB-05','Leche',200),
    ('HAB-06','Chai',10),('HAB-06','Leche',200),('HAB-06','Vainilla',5),('HAB-06','Panela',15),
    ('HAB-07','Harina',60),('HAB-07','Mantequilla',25),('HAB-07','Guayaba',20),('HAB-07','Queso crema',20),
    ('HAB-08','Harina',60),('HAB-08','Mantequilla',15),('HAB-08','Canela',3),('HAB-08','Azúcar',20),('HAB-08','Café',2),
    ('HAB-09','Harina',50),('HAB-09','Banano',60),('HAB-09','Azúcar',20),('HAB-09','Huevo',1),
    ('HAB-10','Harina',60),('HAB-10','Mantequilla',25),('HAB-10','Espinaca',15),('HAB-10','Queso crema',20),('HAB-10','Tomate',20),
    ('HAB-11','Queso crema',80),('HAB-11','Café',5),('HAB-11','Panela',25),('HAB-11','Huevo',1),
    ('HAB-12','Harina',30),('HAB-12','Chocolate',20),('HAB-12','Avellana',15),('HAB-12','Mantequilla',10),('HAB-12','Azúcar',15)
)
INSERT INTO receta_ingrediente(producto_id,ingrediente_id,cantidad)
SELECT p.producto_id,i.ingrediente_id,r.cantidad
FROM recetas r JOIN productos p ON p.codigo=r.codigo
JOIN ingredientes i ON lower(i.nombre)=lower(r.nombre)
WHERE NOT EXISTS (SELECT 1 FROM receta_ingrediente anterior
                  WHERE anterior.producto_id=p.producto_id);

-- La cantidad de referencia permite calcular después la alerta del 15 %.
INSERT INTO inventario_ingrediente(sucursal_id,ingrediente_id,cantidad_referencia)
SELECT s.sucursal_id,i.ingrediente_id,CASE i.unidad WHEN 'unidad' THEN 100 ELSE 10000 END
FROM sucursales s CROSS JOIN ingredientes i
WHERE s.codigo IN ('DEMO-01','DEMO-02') AND EXISTS (
    SELECT 1 FROM receta_ingrediente r JOIN productos p USING(producto_id)
    WHERE r.ingrediente_id=i.ingrediente_id
    AND p.codigo IN ('HAB-01','HAB-02','HAB-03','HAB-04','HAB-05','HAB-06',
                     'HAB-07','HAB-08','HAB-09','HAB-10','HAB-11','HAB-12')
)
ON CONFLICT (sucursal_id,ingrediente_id) DO NOTHING;

-- Dos lotes por inventario vacío: uno vence pronto y otro más adelante.
-- Si ya hay lotes, incluso agotados o vencidos, no se agrega ni repone stock.
INSERT INTO lotes_ingrediente(inventario_id,usuario_id,fecha_vencimiento,
                             cantidad_inicial,cantidad_disponible)
SELECT inv.inventario_id,current_setting('habits.usuario_carga')::BIGINT,
       (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date+l.dias,
       inv.cantidad_referencia*l.fraccion,inv.cantidad_referencia*l.fraccion
FROM inventario_ingrediente inv JOIN sucursales s USING(sucursal_id)
CROSS JOIN (VALUES (3,0.2),(30,0.8)) AS l(dias,fraccion)
WHERE s.codigo IN ('DEMO-01','DEMO-02')
AND EXISTS (SELECT 1 FROM receta_ingrediente r JOIN productos p USING(producto_id)
    WHERE r.ingrediente_id=inv.ingrediente_id
    AND p.codigo IN ('HAB-01','HAB-02','HAB-03','HAB-04','HAB-05','HAB-06',
                     'HAB-07','HAB-08','HAB-09','HAB-10','HAB-11','HAB-12'))
AND NOT EXISTS (SELECT 1 FROM lotes_ingrediente anterior
                WHERE anterior.inventario_id=inv.inventario_id);

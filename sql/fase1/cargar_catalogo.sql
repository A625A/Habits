-- Precios iniciales propuestos por Andrew/Codex en GTQ, no precios verificados.
INSERT INTO sucursales(codigo,nombre)
VALUES ('DEMO-01','Habits Sucursal 1'),('DEMO-02','Habits Sucursal 2')
ON CONFLICT(codigo) DO NOTHING;

INSERT INTO productos(codigo,nombre,categoria,precio) VALUES
('HAB-01','Latte de cardamomo y miel','bebida',26),
('HAB-02','Mocha de chocolate','bebida',28),
('HAB-03','Cold Brew de panela y naranja','bebida',25),
('HAB-04','Latte helado de vainilla y canela','bebida',27),
('HAB-05','Dirty Chai','bebida',29),
('HAB-06','Chai de vainilla y panela','bebida',25),
('HAB-07','Croissant de guayaba y queso crema','panaderia',22),
('HAB-08','Rollo de canela con glaseado de café','panaderia',20),
('HAB-09','Pan de banano','panaderia',16),
('HAB-10','Croissant de espinaca, queso crema y tomate','panaderia',24),
('HAB-11','Cheesecake de café y panela','postre',30),
('HAB-12','Galletas tipo Ferrero Rocher','postre',18)
ON CONFLICT(codigo) DO NOTHING;

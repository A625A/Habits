# Contrato ETL para Rodrigo

Andrew entrega estructura, vistas y validaciones. Rodrigo genera los CSV y escribe
el ETL. Objetivo final: **10,000 tickets distintos**, con una o más líneas cada uno,
entre 2025-11-01 y 2026-10-31, en GTQ. El número de detalles será normalmente mayor.
No generar ventas en `public.ventas` ni en `public.detalle_ventas`.

## Archivos obligatorios

CSV UTF-8, separador coma, encabezado en el orden indicado, comillas dobles para
texto con comas. Sin campos vacíos/NULL, espacios añadidos ni separadores de miles.
IDs enteros positivos de 64 bits; cantidades enteras de 32 bits; decimales con punto
y **máximo dos decimales**. Validar esa escala antes de insertar: PostgreSQL
redondea entradas con más decimales al convertirlas a `NUMERIC(12,2)`.

| Archivo | Columnas obligatorias, en orden | Tipos |
|---|---|---|
| `productos.csv` | `producto_id,codigo,nombre,categoria` | BIGINT, VARCHAR(30), VARCHAR(120), VARCHAR(20) |
| `sucursales.csv` | `sucursal_id,codigo,nombre` | BIGINT, VARCHAR(30), VARCHAR(120) |
| `tickets.csv` | `ticket_id,fecha,sucursal_id,tipo_venta` | BIGINT, DATE, BIGINT, VARCHAR(10) |
| `detalle_ventas.csv` | `detalle_id,ticket_id,producto_id,cantidad,precio_unitario` | BIGINT, BIGINT, BIGINT, INTEGER, NUMERIC(12,2) |

`fecha` usa `AAAA-MM-DD` (ejemplo `2025-11-01`), día civil de Guatemala. Si el
origen usa timestamps, convertir primero con `AT TIME ZONE 'America/Guatemala'`.
`tipo_venta` solo acepta `local` o `llevar`, sin variantes como `para llevar`.
`cantidad > 0`; `0 < precio_unitario <= 9999999999.99`; no NaN/infinito.
No enviar `importe`: PostgreSQL lo genera. No se solicita un total de cabecera.

`producto_id`, `sucursal_id`, `ticket_id` y `detalle_id` son globales dentro del
conjunto, no contadores reiniciados por sucursal, mes o archivo. Conservarlos
estables entre ejecuciones. Los IDs analíticos no necesitan coincidir con los de
una base operativa; sí deben coincidir entre estos cuatro CSV.

Relaciones: detalle → ticket y producto; ticket → sucursal. Cada ticket tiene al
menos un detalle. No hay detalles huérfanos ni pares ticket/producto repetidos.
Si un producto aparece varias veces, generar una línea con cantidad acumulada
y un solo precio histórico; este proyecto no contempla dos precios de ese producto
en un mismo ticket. La fecha/sucursal/tipo se toman de la cabecera, no se inventan
por detalle. No hay cancelaciones, devoluciones ni ventas con importe cero.

## Catálogo original

Los IDs los asigna Rodrigo; estos códigos, nombres y categorías deben conservarse.
Los precios iniciales de Proyecto 2 son ejemplos académicos; el precio histórico
se guarda en el CSV de detalles, sin depender del precio actual.

| Código | Nombre | Categoría |
|---|---|---|
| HAB-01 | Latte de cardamomo y miel | bebida |
| HAB-02 | Mocha de chocolate | bebida |
| HAB-03 | Cold Brew de panela y naranja | bebida |
| HAB-04 | Latte helado de vainilla y canela | bebida |
| HAB-05 | Dirty Chai | bebida |
| HAB-06 | Chai de vainilla y panela | bebida |
| HAB-07 | Croissant de guayaba y queso crema | panaderia |
| HAB-08 | Rollo de canela con glaseado de café | panaderia |
| HAB-09 | Pan de banano | panaderia |
| HAB-10 | Croissant de espinaca, queso crema y tomate | panaderia |
| HAB-11 | Cheesecake de café y panela | postre |
| HAB-12 | Galletas tipo Ferrero Rocher | postre |

Sucursales: `DEMO-01 / Habits Sucursal 1` y `DEMO-02 / Habits Sucursal 2`.
No copiar usuarios, clientes, contactos o credenciales al DataMart.

## Orden y transacción de carga

1. Instalar SQL 01 y 02 en una **base nueva dedicada**, siguiendo la guía.
2. Abrir una única conexión/transacción de ETL. Crear cuatro tablas TEMP de staging
   con esas columnas, NOT NULL, PK por ID y las FK entre staging (cargar primero
   productos y sucursales, luego tickets y detalles). Usar `ON COMMIT DROP`.
3. Cargar los CSV con `COPY ... FROM STDIN` de psycopg o `\copy` de psql, siempre
   con lista explícita de columnas y `FORMAT CSV, HEADER true`. No concatenar datos
   dentro del SQL: usar COPY o parámetros `%s`.
4. Validar staging antes de los INSERT: exactamente 10,000 cabeceras únicas,
   ningún ticket sin detalle, ningún detalle huérfano, catálogo y sedes originales,
   fechas y tipos válidos, cantidades/precios válidos y ticket/producto único.
   Usar Decimal, no float, para validar precios en el lector de CSV.
5. Insertar dimensiones y hechos como se indica abajo. El destino debe estar vacío
   de productos, sucursales y hechos; calendario y tipos ya están instalados.
6. Ejecutar íntegramente **`03_validaciones.sql` sobre la misma conexión**, antes
   del COMMIT, sin cambiar la configuración `habits_olap.tickets_esperados` (el
   valor predeterminado es 10000). El archivo no abre/cierra la transacción.
7. Reconciliar IDs, filas, unidades e importes con staging. Si algo falla, ROLLBACK;
   si todo pasa, COMMIT. Registrar cantidades y resultados de la carga sin secretos.

Solo un ETL debe escribir durante la carga. No usar `ON CONFLICT DO NOTHING`:
una recarga accidental debe fallar sin duplicar ni ocultar diferencias. Si ya hay
una carga, verificarla y detenerse; no usar TRUNCATE/DROP para repetirla.

SQL de mapeo para implementar dentro del ETL (los nombres `stg_*` son tablas TEMP
que Rodrigo creará, no tablas de Proyecto 2):

```sql
INSERT INTO olap.dim_producto(producto_id,codigo,nombre,categoria)
SELECT producto_id,codigo,nombre,categoria FROM stg_productos;
INSERT INTO olap.dim_sucursal(sucursal_id,codigo,nombre)
SELECT sucursal_id,codigo,nombre FROM stg_sucursales;
INSERT INTO olap.fact_ventas
    (detalle_id,ticket_id,fecha,producto_id,sucursal_id,tipo_venta,cantidad,precio_unitario)
SELECT d.detalle_id,t.ticket_id,t.fecha,d.producto_id,t.sucursal_id,t.tipo_venta,
       d.cantidad,d.precio_unitario
FROM stg_detalle_ventas AS d
JOIN stg_tickets AS t ON t.ticket_id=d.ticket_id;
```

Antes del mapeo, estas consultas deben devolver cero filas; convertir cualquier
resultado en un error del ETL. Las PK/FK de staging también deben rechazar errores:

```sql
-- Un INNER JOIN por sí solo ocultaría estos errores de archivos.
SELECT t.ticket_id FROM stg_tickets t
LEFT JOIN stg_detalle_ventas d USING(ticket_id) WHERE d.detalle_id IS NULL;
SELECT d.detalle_id FROM stg_detalle_ventas d
LEFT JOIN stg_tickets t USING(ticket_id) WHERE t.ticket_id IS NULL;
SELECT ticket_id,producto_id FROM stg_detalle_ventas
GROUP BY ticket_id,producto_id HAVING COUNT(*) > 1;
```

Antes del COMMIT, ambos lados deben coincidir (el destino debe haber comenzado vacío):

```sql
SELECT
  (SELECT COUNT(*) FROM stg_tickets) AS tickets_csv,
  (SELECT COUNT(DISTINCT ticket_id) FROM olap.fact_ventas) AS tickets_olap,
  (SELECT COUNT(*) FROM stg_detalle_ventas) AS detalles_csv,
  (SELECT COUNT(*) FROM olap.fact_ventas) AS detalles_olap,
  (SELECT SUM(cantidad) FROM stg_detalle_ventas) AS unidades_csv,
  (SELECT SUM(cantidad) FROM olap.fact_ventas) AS unidades_olap,
  (SELECT SUM(cantidad::numeric*precio_unitario) FROM stg_detalle_ventas) AS importe_csv,
  (SELECT SUM(importe) FROM olap.fact_ventas) AS importe_olap;
-- Cero filas: ningún ID omitido o añadido.
(SELECT detalle_id FROM stg_detalle_ventas EXCEPT SELECT detalle_id FROM olap.fact_ventas)
UNION ALL
(SELECT detalle_id FROM olap.fact_ventas EXCEPT SELECT detalle_id FROM stg_detalle_ventas);
```

La verificación de 10000 tickets en hechos no detecta cabeceras vacías que no llegaron
al destino: por eso son obligatorias también las validaciones de staging.

## Verificación final independiente

Desde la raíz del repositorio, usando la conexión privada de la guía:

```bash
psql -X -v ON_ERROR_STOP=1 --single-transaction \
  -f olap/sql/03_validaciones.sql
```

Debe terminar sin errores y mostrar `tickets = 10000`. También entrega el total de
detalles, unidades, ingresos, ticket promedio y resumen mensual. No confundir
`COUNT(*)` de hechos con tickets. El 04 de humo usa ROLLBACK; no genera la historia.

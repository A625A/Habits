# Modelo estrella de Habits

La tabla central `olap.fact_ventas` registra **un producto dentro de un ticket**.
Un ticket de tres productos tiene tres filas, pero sigue siendo un ticket.
`ticket_id` es una dimensión degenerada: identifica la compra sin añadir una
quinta dimensión ni una cabecera OLAP. No representa una visita o una reserva.

| Tabla | Clave | Contenido |
|---|---|---|
| `dim_fecha` | `fecha DATE` | Día, mes, trimestre y año calculados desde la fecha |
| `dim_producto` | `producto_id BIGINT` | Código, nombre y categoría del catálogo original |
| `dim_sucursal` | `sucursal_id BIGINT` | Código y nombre de las dos sucursales |
| `dim_tipo_venta` | `tipo_venta VARCHAR(10)` | `local` o `llevar` |
| `fact_ventas` | `detalle_id BIGINT` | Ticket, cuatro FK, cantidad, precio histórico e importe |

Las cuatro relaciones son 1:N; cada hecho tiene exactamente una fila en cada
dimensión. No hay FK hacia `public` ni dependencias de Flask. Las ventas simuladas
pertenecen solo a OLAP: nunca se insertan en las ventas reales de Proyecto 2.

## Inspección de Proyecto 2

`ventas` conserva cabecera (`venta_id`, `sucursal_id`, `tipo`, `fecha TIMESTAMPTZ`)
y `detalle_ventas` sus líneas (producto, cantidad y precio histórico), con unicidad
venta/producto. `productos` comparte doce elementos en tres categorías; `sucursales`
usa códigos únicos DEMO-01/02. Se revisaron `sql/01_core.sql`, los scripts de
`sql/fase1/` y sus relaciones/triggers: las ventas no se anulan, consumen inventario
y tienen auditoría. Por eso no se usan para insertar simulaciones.

La versión principal actual usa Flask/psycopg, `DATABASE_URL` y
`TEST_DATABASE_URL`, y documenta PostgreSQL 17/18. No existía OLAP ni DataMart.
El cambio mínimo es añadir `olap/`; no se cambian configuración, rutas, permisos,
scripts operativos ni pruebas originales. Las reglas de visitas/reservas tampoco
se reinterpretan como tickets. El modelo se puede instalar en otra base sin Proyecto 2.

## Medidas y restricciones

`importe = cantidad × precio_unitario`, generado y almacenado por PostgreSQL con
`NUMERIC(22,2)`. El precio histórico usa `NUMERIC(12,2)`, como Proyecto 2; no se
consulta el precio actual del producto. Todos los importes están en quetzales.
La cantidad es entera positiva; el precio es positivo y finito; los IDs son positivos.
La PK impide duplicar detalles y `UNIQUE(ticket_id, producto_id)` impide cargar
dos veces un producto en la misma compra. Rodrigo debe agrupar productos repetidos.

Las dimensiones usan claves naturales del conjunto CSV, sin secuencias: el ETL
conserva esos IDs en las FK. Los códigos identifican el catálogo; no se supone
que los IDs de una instalación de Proyecto 2 sean 1/2 o 1–12.

El calendario contiene 365 días, de 2025-11-01 a 2026-10-31 inclusive. No hay hechos
fuera de ese intervalo. Los dos tipos se precargan; productos y sucursales quedan
vacíos hasta el ETL. No se crea ninguna venta al instalar.

Cada ticket debe conservar la misma fecha, sucursal y tipo en todas sus líneas.
Las FK no verifican esa dependencia entre filas: `03_validaciones.sql` la verifica
antes del COMMIT del ETL. La carga debe ser única, atómica y sin escritores
concurrentes; el contrato explica la validación de cabeceras sin detalles.

Las dimensiones conservan una única versión del catálogo para este ejercicio
(no SCD tipo 2). No actualizar nombres/categorías o precios históricos después de
validar la carga. Las FK impiden borrar dimensiones referenciadas; no hay cascadas.

## DataMart

| Vista | Grano y uso |
|---|---|
| `dm.v_ventas_detalle` | Una fila por detalle; fuente de filtros y KPIs de Power BI |
| `dm.v_ventas_mensuales` | Mes + sucursal + tipo; tendencia sin duplicar tickets |
| `dm.v_productos` | Acumulado del período por producto, incluyendo los que no se vendieron |
| `dm.v_sucursales` | Acumulado del período por sucursal, incluyendo las que no vendieron |

Son vistas normales: consultan los hechos actuales sin REFRESH ni copias.
Ingresos y unidades son aditivos. Tickets por producto/categoría **no** son
aditivos porque una compra puede aparecer en varios productos. Tampoco se
promedian promedios: se divide el ingreso agregado entre los tickets distintos.
Por categoría, el ticket promedio significa ingreso de esa categoría por ticket
que la contiene, no el valor completo de esos tickets.

Un producto/sucursal sin ventas tiene ingresos, tickets y unidades en cero;
el ticket promedio es NULL porque no hay compras. Los meses sin ventas no tienen
fila en la vista mensual; Brian puede completarlos con su calendario de Power BI.

Los índices cubren fecha, producto, sucursal/fecha y tipo. La unicidad ticket/producto
ya permite buscar por ticket; no hace falta otro índice igual.

## Instalación y revisión

Los scripts 01 y 02 se instalan una vez, cada uno con transacción explícita. Si
ya existe su esquema, fallan y conservan los datos; no ejecutan DROP ni reemplazos.
El 03 es de solo lectura y no abre/cierra transacciones, para que Rodrigo pueda
reutilizarlo dentro del ETL. El 04 inserta un ticket mínimo y hace ROLLBACK.

Ver [guía de macOS](guia_ejecucion_mac.md), [contrato ETL](contrato_etl_rodrigo.md),
[contrato Power BI](contrato_powerbi_brian.md) y [resultados](resultados_pruebas.md).
El [diagrama editable](modelo_estrella.mmd) y el [PDF](modelo_estrella.pdf) muestran
las mismas cinco tablas.

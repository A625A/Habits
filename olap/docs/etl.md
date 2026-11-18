# Generación de datos y ETL — Rodrigo

## Entrega en cinco commits

1. 18 de noviembre de 2026: catálogo de referencia y contrato de los CSV.
2. 18 de noviembre de 2026: generador histórico reproducible.
3. 18 de noviembre de 2026: cuatro CSV y pruebas del dataset.
4. 19 de noviembre de 2026 (pendiente): lectura, limpieza y validación del ETL;
   carga transaccional e idempotente en las tablas `olap` existentes.
5. 19 de noviembre de 2026 (pendiente): pruebas de integración de carga,
   recarga y rollback; instrucciones y evidencia de ejecución del ETL.

## Fuente y alcance

El catálogo versionado en `olap/data/catalogo/` transcribe
`sql/fase1/cargar_catalogo.sql`: 12 productos y las dos sucursales DEMO-01 y
DEMO-02. Los precios de esa fuente son **propuestos, no verificados**.
Los identificadores 1..12 y 1..2 son propios del dataset analítico;
no representan las secuencias de las bases operativas de cada sucursal.
Toda venta generada es simulada. Moneda: GTQ.

No se insertan ventas en las tablas operativas. El destino futuro del ETL es
exclusivamente el modelo de `olap/sql/01_modelo_estrella.sql`, ya existente.

## Contrato de archivos

CSV en UTF-8, separador coma, encabezados, salto LF, decimales con punto.
Fechas ISO `YYYY-MM-DD`. Todos los IDs y cantidades son enteros positivos.

| Archivo en `olap/data/raw/` | Columnas |
| --- | --- |
| sucursales.csv | sucursal_id,codigo,nombre |
| productos.csv | producto_id,codigo,nombre,categoria,precio |
| ventas.csv | venta_id,fecha,sucursal_id,tipo_venta |
| detalle_ventas.csv | detalle_id,venta_id,producto_id,cantidad,precio_unitario |

`venta_id` se transforma en `ticket_id` al cargar el modelo de Andrew.
Cada venta tiene al menos un detalle y un producto aparece como máximo una vez
por venta. `importe` lo calcula PostgreSQL como cantidad por precio histórico;
el precio del catálogo no reemplaza al precio cobrado del detalle.
Tipos: `local`, `llevar`. Categorías: `bebida`, `panaderia`, `postre`.
Período cerrado: 2025-11-01 a 2026-10-31; exactamente 10,000 ventas.

## Generación

Requiere Python 3.12; el generador utiliza solamente la biblioteca estándar.
Desde la raíz del repositorio:

```powershell
python olap/scripts/generar_datos.py
python -m unittest discover -s olap/tests -p test_generador.py -v
```

Si se utiliza uv, reemplazar `python` por `uv run --python 3.12 python`.
La ruta predeterminada se calcula desde el script, independientemente del directorio
actual. `--salida RUTA` permite generar otra copia y `--semilla ENTERO` cambiar
el escenario. La semilla predeterminada es 20251101. Reejecutar reemplaza los
cuatro archivos de salida: guardar en otro directorio cualquier edición manual.

La distribución es una hipótesis comercial, no una estimación de ventas reales:
mayor demanda viernes y fines de semana, diciembre y mayo; reparto aproximado
58/42 entre sucursales; más atención para llevar en la segunda sucursal.
Se ponderan productos por popularidad y bebidas frías según estación.
Cada ticket contiene de uno a cuatro productos distintos, con una a tres unidades.
Desde mayo se simula un aumento de precios de 4%; algunos tickets reciben 5%
de descuento. Los importes usan Decimal con redondeo a centavos.

## ETL pendiente

Los commits 4 y 5 implementarán `olap/scripts/etl.py`. Aún no hay comando de carga.
Deberá rechazar fechas, IDs duplicados, referencias, cantidades y precios inválidos,
comprobar tickets completos y validar todo antes de escribir. La recarga del mismo
dataset no deberá duplicar hechos ni modificar tablas de Proyecto 2.

## Evidencia del dataset entregado

Generado y comprobado el 18 de noviembre de 2026 con Python 3.12.13 y semilla
20251101. Las cuatro pruebas de `test_generador.py` pasan sin conexión a PostgreSQL.

| Medida | Resultado |
| --- | ---: |
| Ventas distintas | 10,000 |
| Detalles | 19,175 |
| Unidades | 23,641 |
| Importe simulado, GTQ | 583,177.42 |
| Tickets DEMO-01 | 5,668 |
| Tickets DEMO-02 | 4,332 |
| Tickets local | 4,893 |
| Tickets llevar | 5,107 |
| Fechas con ventas | 365 |

Las pruebas contrastan los productos y sucursales con el SQL fuente, revisan el
período, unicidad y referencias, comprueban cantidades y precios, y comparan los
CSV publicados byte por byte con una nueva generación. Otra semilla produce
otro dataset. Estas pruebas no demuestran todavía la carga a PostgreSQL;
esa verificación corresponde a los commits pendientes.

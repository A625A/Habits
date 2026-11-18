# Generación de datos y ETL — Rodrigo

## Entrega en cinco commits

1. 18 de noviembre de 2026: catálogo de referencia y contrato de los CSV.
2. 18 de noviembre de 2026: generador histórico reproducible.
3. 18 de noviembre de 2026: cuatro CSV y pruebas del dataset.
4. ETL: lectura, limpieza y validación de CSV;
   carga transaccional e idempotente en las tablas `olap` existentes.
5. Pruebas de integración de carga,
   recarga y rollback; instrucciones y evidencia de ejecución del ETL.

## Fuente y alcance

El catálogo versionado en `olap/data/catalogo/` transcribe
`sql/fase1/cargar_catalogo.sql`: 12 productos y las dos sucursales DEMO-01 y
DEMO-02. Los precios de esa fuente son **propuestos, no verificados**.
Los identificadores 1..12 y 1..2 son propios del dataset analítico;
no representan las secuencias de las bases operativas de cada sucursal.
Toda venta generada es simulada. Moneda: GTQ.

No se insertan ventas en las tablas operativas. El destino del ETL es
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

## ETL

Validación sin conexión ni dependencias externas:

```powershell
python olap/scripts/etl.py --solo-validar
```

El lector acepta BOM UTF-8, limpia espacios alrededor de cada campo y normaliza
el tipo de venta a minúsculas. No elimina duplicados ni corrige importes o fechas
silenciosamente. Rechaza encabezados incorrectos, campos vacíos, columnas extra,
IDs o códigos duplicados, fechas fuera del período, referencias inexistentes,
ventas sin detalles, productos repetidos por ticket, cantidades no positivas y
precios no finitos, negativos o con más de dos decimales. Comprueba que las dos
sucursales y los 12 productos correspondan al catálogo versionado.

Para cargar, instalar `python -m pip install -r requirements.txt` y preparar una
base analítica con las credenciales propias de PostgreSQL:

```powershell
$env:OLAP_DATABASE_URL = 'postgresql://usuario:clave@localhost:5432/habits_analitica'
# Solo la primera vez, sobre una base sin el modelo instalado:
psql -X -v ON_ERROR_STOP=1 -d $env:OLAP_DATABASE_URL -f olap/sql/01_modelo_estrella.sql
psql -X -v ON_ERROR_STOP=1 -d $env:OLAP_DATABASE_URL -f olap/sql/02_datamart.sql
python olap/scripts/etl.py
python olap/scripts/etl.py  # recarga: los mismos totales, sin duplicados
```

Usar credenciales reales en el entorno local; no versionarlas. El script no lee
`.env` ni usa `DATABASE_URL`. `--datos RUTA` selecciona otro directorio con los
cuatro CSV. Un error termina con código distinto de cero.

La validación completa sucede antes de conectarse. La carga toma un bloqueo de
escritura sobre las tres tablas destino, usa tablas temporales y COPY, e inserta
solo filas faltantes. Después compara el contenido completo con la entrada,
ejecuta `03_validaciones.sql` y concilia ventas, detalles, unidades e ingresos
antes del commit. No actualiza ni borra históricos: si una fila existente es
diferente o hay datos adicionales en el destino, revierte toda la carga.
Este comando administra un único dataset completo de 10,000 tickets; no es un
importador incremental de períodos adicionales. Los precios históricos del
detalle se conservan y PostgreSQL calcula `importe`.

Las tablas calendario y tipos deben estar inicializadas por el modelo de Andrew.
El usuario necesita SELECT/INSERT sobre las tablas `olap`, permisos para el
bloqueo, TEMP en la base, y lectura de las vistas `dm`. No requiere permisos de
escritura sobre tablas operativas.

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

# SQL avanzado aplicado al backend de Habits

Esta guía cubre los cinco temas pedidos para la presentación con los objetos
existentes de Fase 1 y su integración HTTP de Fase 2. No agrega tablas, índices,
vistas o funciones para demostrar teoría. Los scripts están listos para `psql`
sobre el esquema instalado; los resultados dependen de los datos de esa base.

## Ejecutar las consultas

Conectarse como propietario para ver la bitácora; el rol operativo no la consulta.
Usar la conexión habitual de la instalación, sin escribir contraseñas en scripts.
Desde `psql`, con el esquema correcto en `search_path`:

```psql
\i sql/fase2/consultas_presentacion.sql
```

El archivo abre una transacción de solo lectura. Sus consultas funcionan también
con datos vacíos; no atribuir rendimiento representativo a una base sin operaciones.

## 1. Índices: medir una consulta real

`GET /clientes/{id}/historial` consulta reservas por cliente y fecha. El índice
existente `idx_reservas_cliente_fecha (cliente_id,fecha_inicio)` permite localizar
ese historial; el planificador decide si usarlo. Para la agenda existe
`idx_reservas_sucursal_fecha`; para FEFO, índices parciales de lotes y producciones
con saldo positivo, ordenados por vencimiento e ID. La exclusión GiST de reservas
impide intervalos superpuestos, además de disponer de un índice para esa regla.

La primera consulta del script lista las definiciones instaladas. La siguiente
mide el historial del primer cliente existente, sin asumir su ID:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT reserva_id,fecha_inicio,estado FROM reservas
WHERE cliente_id=(SELECT min(cliente_id) FROM clientes)
ORDER BY fecha_inicio DESC LIMIT 50;
```

`EXPLAIN` muestra el plan estimado. `ANALYZE` ejecuta la consulta y añade filas y
tiempos reales; `BUFFERS` permite examinar accesos a bloques. Comparar filas
estimadas/reales, `loops`, tiempo total y bloques. Un `Seq Scan` en una tabla pequeña
puede ser razonable; no se debe forzar un índice para que la demostración parezca
más rápida. Aquí se ejecuta un SELECT, sin modificar datos.
[Referencia: EXPLAIN, PostgreSQL 17](https://www.postgresql.org/docs/17/using-explain.html).

Usar `CREATE INDEX` cuando una consulta frecuente y medida filtra/ordena columnas
sin cobertura adecuada y el beneficio compensa espacio y mantenimiento de
escrituras. Comparar antes/después con volumen representativo y estadísticas
actualizadas; revisar primero `pg_indexes` para evitar duplicados. Habits ya tiene
índices pertinentes y esta fase no produjo evidencia que justifique otro. Por eso
no incluye un `CREATE INDEX` adicional para ejecutar por rutina.
[Referencia: índices](https://www.postgresql.org/docs/17/indexes.html).

## 2. Vistas y CTE: datos derivados sin saldos duplicados

`GET /inventario/existencias` usa `v_stock_ingredientes`: agrega únicamente lotes
utilizables y conserva inventarios configurados sin stock. `stock_bajo` evalúa
la referencia del 15 %. `v_stock_terminados` aplica el mismo criterio temporal a
producciones. `GET /ventas` y el historial usan `v_totales_ventas`, que calcula
unidades e importe con precios históricos de detalles, sin otro total editable.

El script consulta las tres vistas. Su CTE `atenciones` cuenta visitas reales por
sede; `compras` agrega ventas e importe por separado, luego las une a sucursales.
Así, una visita con varias ventas sigue contando una vez. Unir primero todas las
filas de visitas con ventas por sede multiplicaría conteos/importes. El `WITH`
organiza estas agregaciones en una sola consulta, sin crear tablas intermedias.
Esta consulta sirve para explicar los datos del backend; no crea un endpoint de
reportes de una fase posterior.

## 3. FUNCTION y PROCEDURE

Una `FUNCTION` se usa dentro de una consulta y devuelve un valor o conjunto de
filas: `stock_bajo` devuelve boolean y `reporte_sucursales` devuelve una tabla.
El script llama este último mediante SELECT para el mes actual de Guatemala,
con límite inferior inclusivo y superior exclusivo.

Una `PROCEDURE` se invoca con `CALL`; puede entregar resultados mediante parámetros
de salida, como `p_venta`. PostgreSQL permite control de transacciones dentro de
ciertos procedimientos bajo condiciones concretas; los de Habits **no hacen
COMMIT interno**. Flask controla toda la unidad de trabajo, incluidos los triggers
al confirmar. No se puede llamar un procedimiento como si fuera una función en SELECT.
[Referencia: procedimientos](https://www.postgresql.org/docs/17/xproc.html).

| Operación HTTP | Objeto SQL | Motivo |
|---|---|---|
| POST `/reservas/{id}/llegada` | `registrar_llegada` | Crea visita y completa reserva juntas |
| POST `/reservas/{id}/cancelar` | `cancelar_reserva` | Cancela sin borrar historia |
| POST `/producciones` | `registrar_produccion` | Consume receta y crea lote terminado |
| POST `/ventas` | `registrar_venta` | Guarda detalles/precios y consume stock completo |
| POST `/inventario/recepciones` | `registrar_recepcion` | Crea un lote con saldo igual a lo recibido |

Los cuatro primeros se reutilizan de Fase 1. Recepción es la única nueva operación
SQL: evita conceder escritura directa de saldos al rol de operaciones. La función
interna `consumir_receta` implementa FEFO; no se llama desde Flask ni se publica al
rol operativo. SQL parametrizado separa valores de instrucciones en todas las rutas.

## 4. Triggers: auditoría e integridad automática

El script lista `pg_get_triggerdef` para ver cuándo se ejecuta cada trigger real.
`validar_reserva` comprueba capacidad/estado; las FK y exclusión añaden coherencia
de sucursal y ausencia de traslapes. `comprobar_llegada_*` son diferidos: al confirmar
exigen correspondencia entre reserva completada y visita. `venta_con_detalles`
impide confirmar una venta vacía. Los triggers de conservación protegen historia.

Los triggers `auditar_*` llaman `auditar_cambio` dentro de la misma transacción.
El último SELECT del script enseña tabla, PK, operación, actor y fecha de eventos
confirmados. El actor viene de `g.user`, nunca de un campo JSON. No se muestran
snapshots de información personal. Si se revierte una venta, se revierten sus
consumos y eventos; Flask no intenta escribir una segunda bitácora manual.

## 5. BEGIN, COMMIT, ROLLBACK y ACID

En `app/api.py`, `with db.transaction()` inicia la transacción; al salir normalmente
confirma y ante una excepción revierte. La respuesta de éxito se construye después
de confirmar. Los errores de negocio salen del bloque antes de convertirse en JSON.
Por eso una venta con varias líneas no puede dejar la primera cobrada y la segunda
fallida. Es el uso conjunto de transacciones y reglas de PostgreSQL.
[Referencia: transacciones](https://www.postgresql.org/docs/17/tutorial-transactions.html).

| Propiedad | Aplicación concreta y verificación |
|---|---|
| Atomicidad | Cabecera, detalles, consumo y bitácora se confirman o revierten juntos; probado con fallo en la segunda línea |
| Consistencia | CHECK, FK, exclusión, triggers y procedimientos mantienen capacidad, sede, stock y coherencia visita/venta |
| Aislamiento | Bloqueos explícitos serializan inventario por sede y protegen recetas/mesas; dos peticiones concurrentes no sobrevendieron ni duplicaron reserva. Se usa el aislamiento configurado de PostgreSQL, sin afirmar SERIALIZABLE global |
| Durabilidad | Tras COMMIT PostgreSQL conserva la operación mediante su almacenamiento/WAL según la configuración del servidor; la suite verifica persistencia entre peticiones, no simula pérdida de disco ni sustituye backups |

`consultas_presentacion.sql` muestra `BEGIN READ ONLY` y `COMMIT`. Para demostrar
una venta y su ROLLBACK, en una **base de pruebas terminada en `_test`**, con un
usuario, receta y existencias ya preparados, ejecutar:

```psql
\i sql/fase2/ensayo_venta.psql
```

El script pide IDs reales y cantidad; hace `BEGIN`, reduce el rol y llama a
`registrar_venta`. Muestra el total dentro de la transacción, fuerza las
restricciones diferidas con `SET CONSTRAINTS ALL IMMEDIATE` y hace `ROLLBACK`.
La consulta posterior devuelve `ventas_tras_rollback = 0`. Si falta stock o algún
ID no es válido, PostgreSQL aborta la operación; el script se detiene sin confirmar.
Las secuencias pueden dejar huecos tras rollback: un ID consumido no implica una
venta confirmada. Para operar de verdad se utiliza el endpoint, cuyo éxito confirma
la transacción; el ensayo nunca cambia ROLLBACK por COMMIT automáticamente.

Los ingredientes, cantidades, precios y mesas de los tests automatizados son
fixtures aisladas. Estos scripts de presentación no cargan supuestos inventados
ni requieren sembrar datos ficticios en la base de operación.

## Ejemplos con el menú y los datos de práctica

Para comprobar estas reglas con las recetas de `sql/datos_ejemplo/datos.sql`,
ejecutar `python -m pytest tests/test_datos_ejemplo.py -q`. Las pruebas preparan
sus propios datos en esquemas separados; no necesitan cargar ejemplos en la base
de uso diario. Las cantidades siguientes corresponden al catálogo ficticio sin
modificaciones; no representan recetas comerciales.

### Qué hace cada procedimiento

| Objeto | Explicación para la presentación |
|---|---|
| `registrar_produccion` | Revisa al empleado, consume los ingredientes de la receta y registra las unidades de pan o postre preparadas. |
| `registrar_venta` | Guarda la compra y sus detalles; descuenta ingredientes si es bebida o unidades preparadas si es pan o postre. Conserva el precio cobrado. |
| `registrar_llegada` | Crea la visita y marca la reserva como completada dentro de la misma operación. |
| `cancelar_reserva` | Libera el horario al cancelar la reserva, conservando el registro para consultar su historia. |
| `registrar_recepcion` | Agrega un lote de ingredientes con cantidad inicial y disponible iguales. Requiere la ampliación SQL de Fase 2. |

`consumir_receta` es una función de apoyo que usan producción y venta; no es un
procedimiento adicional que deba ejecutar el empleado. Multiplica cada cantidad
de la receta por las unidades pedidas. Busca lotes de la sucursal que todavía
sirvan y toma primero los que vencen antes. Si no alcanza un ingrediente, informa
el error para deshacer la operación completa.

Por ejemplo, cada pan de banano de práctica usa 50 g de harina. Preparar 41 panes
consume 2050 g: 2000 del lote que vence primero y 50 del siguiente. También consume
banano, azúcar y huevos. Se crean 41 unidades terminadas. Cuando se vende una,
quedan 40 y no se vuelve a descontar harina. En cambio, vender dos lattes consume
directamente dos veces su receta, sin crear una producción.

### Qué se ejecuta automáticamente

Un trigger es una comprobación o acción que la base ejecuta al cambiar una tabla.
El empleado llama al procedimiento; no necesita llamar por separado a los triggers.

| Trigger o grupo | Qué protege |
|---|---|
| `validar_reserva` | Rechaza grupos mayores que la mesa, datos inactivos y cambios de estado inválidos. Los cruces de horario los impide la restricción de exclusión, no este trigger. |
| `validar_produccion` | Permite producir panadería o postres activos y revisa al operador. |
| `validar_venta` | Revisa al operador y la correspondencia de la venta con su atención y mesa. |
| `venta_con_detalles` | Al confirmar, impide que una venta quede guardada sin productos. |
| `comprobar_llegada_reserva` y `comprobar_llegada_visita` | Al confirmar, exigen que la reserva completada y su visita correspondan. |
| `conservar_lote`, `conservar_produccion`, `conservar_venta`, `conservar_detalle` | Protegen los datos históricos. Los saldos de lotes y producciones pueden disminuir; sus cantidades iniciales no se reescriben. |
| `auditar_*` | Registran los cambios en la bitácora usando `auditar_cambio`, dentro de la misma transacción. |

La bitácora registra cambios guardados. Si la operación termina en `ROLLBACK`,
también desaparecen sus eventos. No sirve como registro de intentos fallidos.
En estas operaciones `validar_operador` establece el ID del empleado que luego
usa la auditoría. La aplicación debe obtener ese ID de la sesión autenticada.

### Qué significan BEGIN, COMMIT y ROLLBACK aquí

`BEGIN` abre el grupo de cambios. `COMMIT` los guarda juntos y comprueba las reglas
pendientes. `ROLLBACK` los deshace. Los procedimientos de Habits no guardan por su
cuenta: quien los llama controla la transacción. Así se puede producir y vender
dentro de una sola transacción cuando la demostración lo necesita.

Las pruebas comprueban estos casos:

- Falta huevo al producir pan: se recuperan también los ingredientes descontados antes del error y no queda producción ni evento de auditoría.
- Una venta contiene una bebida y un pan sin unidades preparadas: se deshace también el descuento de la bebida y no queda ningún detalle de esa compra.
- Se produce y vende correctamente, pero se ejecuta `ROLLBACK`: lotes, producciones, ventas, detalles y bitácora quedan como antes.
- Se confirma con `COMMIT`: otra conexión puede consultar la venta y el empleado registrado por la auditoría.
- Se intenta guardar una venta sin detalles: la comprobación diferida impide confirmar y se revierte la operación.

Esto demuestra atomicidad al evitar cambios a medias y consistencia al aplicar
las reglas. Los bloqueos que aparecen como `FOR UPDATE` protegen las filas que
se están usando; estas pruebas de ejemplo no miden concurrencia. Consultar desde
otra conexión verifica que se confirmó el cambio, pero no simula una falla de disco.
Las secuencias de IDs pueden avanzar aunque se deshaga una operación: no se debe
confundir un salto en los números con una venta perdida.

### Ensayo manual de producción y venta

En una base exclusiva de práctica terminada en `_test`, con el esquema completo,
los datos de ejemplo y un administrador activo, ejecutar como propietario:

```bash
psql -X -h 127.0.0.1 -p 55432 -U habits_app -d habits_test -W -v usuario_id=SU_ID -f sql/datos_ejemplo/ensayar_produccion_venta.psql
```

Adaptar conexión e ID. El ensayo usa `DEMO-01`, `HAB-09` y `HAB-01`: prepara dos
panes y vende un pan junto con un latte. Con precios iniciales muestra un total
temporal de Q42. Después ejecuta `ROLLBACK`; las cuatro columnas de comprobación
deben mostrar `true`. No necesita que las tablas de operaciones estén vacías.
Si faltan ingredientes o datos, se detiene sin confirmar; no cambia automáticamente
a `COMMIT`. No ejecutar a la vez que otras operaciones si se van a comparar los
conteos finales, porque otro usuario podría cambiar esos datos durante el ensayo.

# Base de datos completa — Fase 1

Andrew aprobó el DER el 31 de octubre de 2026 y autorizó precios iniciales propuestos
para los doce productos. Esta entrega implementa PostgreSQL; no añade rutas, UI ni
login. El reparto histórico entre integrantes ya no limita este esquema.

## Instalación y ampliación reproducible

Requiere PostgreSQL 17, `psql`, una base y su usuario propietario. Se usan las cuentas
locales del README; adaptar nombres/host si la instalación es distinta. No usar al
administrador del clúster desde Flask.

Una vez, como administrador PostgreSQL, preparar el rol de operaciones sin login:

```bash
psql -h "$PWD/.local/socket" -p 55432 -U habits_admin -d habits \
  -f sql/fase1/rol_operaciones.sql \
  -c 'GRANT habits_operaciones TO habits_app, habits_test;'
```

Crear o ampliar la base como su propietario; `-W` pide su contraseña sin mostrarla:

```bash
psql -X -h 127.0.0.1 -p 55432 -U habits_app -d habits -W \
  -f sql/fase1/inicializar.sql
```

El mismo comando sirve para una base vacía, la base core de Andrew o una instalación
completa de esta versión. No hace falta repetir `flask db-init`. El instalador:

1. Abre una transacción y serializa ejecuciones simultáneas.
2. Conserva el core, sesiones y auditoría existentes; los crea si faltan.
3. Instala las catorce tablas adicionales, sus objetos y permisos en dependencia.
4. Carga las dos sucursales y doce productos por código único, sin sobrescribirlos.
5. Confirma todo junto; un error revierte la ampliación completa.

La versión se identifica con un comentario de `productos`, sin añadir una tabla 19.
Si encuentra un esquema parcial o las tablas de otro diseño, aborta para preservar
ese trabajo. No transforma automáticamente la rama de Chris: sus entidades y la
exclusión de reservas se adaptaron al DER aprobado, sin fusionar sus rutas.
No es un reparador de cambios manuales a un esquema ya marcado con esta versión.

Los códigos `DEMO-01` y `DEMO-02` se conservan por compatibilidad con la base existente.
Son identificadores históricos, no un modo de funcionamiento. En una base nueva los
nombres iniciales son Habits Sucursal 1 y Habits Sucursal 2; los nombres que ya existan
se preservan. No se cargan clientes, usuarios, contraseñas, reservas, ventas ni saldos
ficticios. Las recetas y recepciones se registran con datos de operación; no se
presenta stock inventado como existencia física.

## Archivos y dependencias

| Archivo | Contenido |
|---|---|
| `10_catalogo.sql` | Mesas, clientes, productos, ingredientes, recetas, inventario por sede y preferencias |
| `20_atencion.sql` | Reservas, visitas, observaciones, integridad de atención y llegada/cancelación |
| `30_inventario.sql` | Lotes, producciones, FEFO, vistas de existencias y función de alerta |
| `40_ventas.sql` | Ventas, detalles, precios históricos, total calculado y venta transaccional |
| `50_reportes.sql` | Cinco funciones SQL con los reportes exigidos |
| `60_auditoria.sql` | Triggers de las catorce tablas nuevas, actor y validaciones compartidas |
| `70_acceso.sql` | Procedimientos con permisos acotados y búsquedas de objetos en esquema fijo |
| `cargar_catalogo.sql` | Dos sucursales y doce productos, sin duplicación ni reemplazo de precios |

Ejecutar `inicializar.sql`, no archivos individuales fuera de su transacción.
`btree_gist` se instala en `public`; requiere permisos del propietario de la base
para la extensión confiable. Los tests usan esquemas únicos y `public` en search_path.

## Precios iniciales propuestos, GTQ

Son valores de configuración autorizados por Andrew, no precios de mercado
verificados. Se pueden cambiar en `productos.precio`; las ventas pasadas conservan
su propio `precio_unitario`. Repetir la carga no reemplaza esos cambios.

| Código | Producto | Categoría | GTQ |
|---|---|---|---:|
| HAB-01 | Latte de cardamomo y miel | bebida | 26 |
| HAB-02 | Mocha de chocolate | bebida | 28 |
| HAB-03 | Cold Brew de panela y naranja | bebida | 25 |
| HAB-04 | Latte helado de vainilla y canela | bebida | 27 |
| HAB-05 | Dirty Chai | bebida | 29 |
| HAB-06 | Chai de vainilla y panela | bebida | 25 |
| HAB-07 | Croissant de guayaba y queso crema | panaderia | 22 |
| HAB-08 | Rollo de canela con glaseado de café | panaderia | 20 |
| HAB-09 | Pan de banano | panaderia | 16 |
| HAB-10 | Croissant de espinaca, queso crema y tomate | panaderia | 24 |
| HAB-11 | Cheesecake de café y panela | postre | 30 |
| HAB-12 | Galletas tipo Ferrero Rocher | postre | 18 |

## Uso SQL y límites de permisos

El propietario instala y configura tablas maestras. Para operaciones de venta,
producción y llegada se usa `habits_operaciones`, un rol SQL sin credenciales propias.
No es un cuarto rol del personal: administrador, gerente y mesero siguen en usuarios.
No tiene DML directo sobre ventas, detalles o saldos, ni lectura de hashes/sesiones.
Los procedimientos son `SECURITY DEFINER` con search_path fijo al esquema instalado;
las funciones internas de consumo no se exponen al rol. El dueño y un superusuario
siguen siendo operadores privilegiados; PostgreSQL no los protege contra sus propios
cambios manuales. La conexión futura de aplicación debe operar con privilegios
limitados, no confiar en que ser dueño de las tablas imponga estas restricciones.

Las operaciones validan usuario activo y su adscripción, salvo administrador global.
Los IDs recibidos deben proceder de la identidad autenticada al integrar backend;
no constituyen por sí solos autenticación. No se implementó esa integración aquí.
Cancelación conserva el actor fijado por el contexto de transacción, como la auditoría
existente. La función de auditoría permite actor nulo en mantenimiento SQL.

Ejemplo de llamada (variables psql definidas con IDs existentes):

```sql
BEGIN;
SET LOCAL ROLE habits_operaciones;
CALL registrar_llegada(:reserva_id, :usuario_id, NULL);
COMMIT;
```

Firmas de los procedimientos, sin COMMIT interno:

- `registrar_llegada(reserva_id, usuario_id, NULL)` devuelve visita_id.
- `cancelar_reserva(reserva_id)` conserva la fila y libera su intervalo.
- `registrar_produccion(sucursal_id, producto_id, usuario_id, cantidad, vencimiento, NULL)` devuelve produccion_id.
- `registrar_venta(sucursal_id, usuario_id, tipo, visita_id, mesa_id, lineas_jsonb, NULL)` devuelve venta_id.

`lineas_jsonb` es una lista de objetos con producto_id y cantidad entera positiva.
Productos repetidos se agrupan. Las llamadas no reciben precios del cliente: leen
el catálogo. Un error revierte todos los detalles, consumos y eventos de auditoría.
Si se usa BEGIN explícito y hay error, ejecutar ROLLBACK antes de continuar.

Las bebidas consumen receta; producir panes/postres consume receta; venderlos consume
solo terminados. La receta debe existir y tener todos sus ingredientes activos.
Las operaciones de inventario de una misma sucursal se serializan con bloqueo de
su fila: es una solución sencilla para dos sedes. FEFO ordena por vencimiento e ID;
no omite un lote bloqueado con SKIP LOCKED. Los vencidos permanecen visibles, pero
no pueden consumirse. La fecha de vencimiento se puede utilizar hasta finalizar
el día local de Guatemala.

## Consultas y conceptos para la presentación

```sql
SELECT * FROM reporte_productos('2026-10-01 00:00-06','2026-11-01 00:00-06');
SELECT * FROM reporte_frecuentes('2026-10-01 00:00-06','2026-11-01 00:00-06');
SELECT * FROM reporte_reservas('2026-10-01 00:00-06','2026-11-01 00:00-06');
SELECT * FROM reporte_inventario('2026-10-01');
SELECT * FROM reporte_sucursales('2026-10-01 00:00-06','2026-11-01 00:00-06');
```

- Índices: agenda, historial y selección de lotes; el plan depende de cantidad de datos.
- Vistas: stock utilizable y totales de ventas, sin saldos duplicados.
- CTE: primero contar visitas/reservas/ventas, después combinar sin multiplicar filas.
- Funciones: `stock_bajo`, reportes y consumo reutilizable de recetas.
- Procedimientos: operaciones completas invocadas con CALL.
- Triggers: auditoría, capacidad, inmutabilidad y coherencia diferida al COMMIT.
- Transacciones: operación y bitácora se confirman o revierten juntas.

El reporte mensual combina stock actual y vencimientos del mes seleccionado; no
reconstruye stock histórico. Frecuencia cuenta solo visitas reales. Llegar completa
la reserva, pero su intervalo sigue excluyendo traslapes durante los 90 minutos.
Reportes de reservas muestran confirmadas/completadas; no las llaman visitas.

## Verificación

Preparar `TEST_DATABASE_URL` hacia una base exclusiva terminada en `_test` y dar
al propietario de esa base membresía de `habits_operaciones` como en el primer paso.
La extensión se instala en esa base; cada prueba elimina únicamente su esquema único.

```bash
.venv/bin/pytest tests/test_database_phase1.py -q
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy
```

Las pruebas incluyen datos sintéticos exclusivamente en esquemas temporales; nunca
cargan esas ventas, clientes o saldos en la base de uso local.
El resultado final se registra en [verificacion-bd-fase-1.md](verificacion-bd-fase-1.md).

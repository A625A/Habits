# Verificación de interfaz y reportes de Brian

## Validación integrada — 3 de noviembre de 2026

Base exacta: `de2282ed7b9d3fe2928c0aa9cc2c6a17d8456ed2`, idéntica a
`origin/main` después de `git fetch origin --prune`. La rama fue
`feat/brian-ui-docs`; antes de validar estaba limpia y cuatro commits por delante
de su remoto histórico.

### PostgreSQL y suite actual

Se reutilizó un clúster PostgreSQL 17.11 descartable bajo `/tmp`, accesible solo
por un socket Unix privado. Se crearon dos bases separadas: `habits_ui_test` para
la interacción y `habits_suite_test` para pytest. No se leyó ni modificó `.env`,
ni se conectó a una base compartida.

En `habits_ui_test` se instalaron `sql/fase1/inicializar.sql`, la ampliación
`db-backend-upgrade`, la cuenta demo local autorizada y
`sql/datos_ejemplo/cargar_demo.psql`. La revisión de datos devolvió diez reservas
sin cruces, cuarenta inventarios y ochenta y un lotes iniciales. La suite completa
de esta versión se ejecutó una vez:

```text
215 passed in 47.37s
0 failed
0 skipped
```

Después de la única corrección se ejecutó la regresión dirigida de permisos:

```text
1 passed in 0.80s
```

### Interacciones reales en Firefox

Firefox 158.0.1 se ejecutó en modo headless y fue controlado por Marionette. No
se usaron stubs ni se sustituyeron los clics por peticiones HTTP. Con sesión real
y el JavaScript publicado se comprobó:

- login, cuenta, dashboard y navegación por los nueve módulos;
- alta y búsqueda de `Cliente Navegador Local`, historial, preferencia y observación;
- tres reservas separadas: una confirmada, una cancelada y una completada mediante
  llegada; una cuarta solicitud traslapada fue rechazada sin crear registro;
- inventario, alertas, recepción de cinco unidades y producción de una unidad;
- una venta válida por Q 26.00 y otra con cantidad imposible rechazada por stock;
- permisos de administrador, gerente y mesero; el mesero no vio inventario o
  producción, recibió 403 al intentar inventario y sí abrió ventas;
- menú colapsable a 720 px y tabla con desplazamiento interno: viewport 720 px,
  cuerpo 708 px, contenedor 480 px y tabla 672 px.

La base confirmó los efectos, no solo los mensajes de la página: el cliente quedó
con una preferencia y una observación; sus reservas terminaron una en cada estado
`confirmada`, `cancelada` y `completada`, y la llegada produjo una visita. La demo
tenía catorce ventas y quedó con quince después de la venta válida; el rechazo por
stock no creó una venta ni cambios parciales. También quedaron trece producciones
y ochenta y tres lotes después de la producción y la recepción.

### Reportes y gráficas

Para `2026-11-01` incluido y `2026-12-01` excluido, las funciones definitivas y
la interfaz coincidieron:

| Métrica | Antes | Después de operar en Firefox |
|---|---:|---:|
| Unidades del top de productos | 28 | 29 |
| Importe del top | Q 696.00 | Q 722.00 |
| Visitas del top frecuente | 12 | 13 |
| Reservas de Sucursal 1 | 4 | 6 |
| Ventas de Sucursal 1 | 7 | 8 |
| Importe de Sucursal 1 | Q 316.00 | Q 342.00 |

El cliente creado apareció con una reserva confirmada y una completada. Sucursal 2
se conservó en cuatro reservas, siete ventas y Q 476.00. Las gráficas HTML mostraron
los mismos valores; por ejemplo, el producto afectado llegó a seis unidades y las
barras de Sucursal 1 mostraron seis reservas y ocho ventas. También se comprobaron
cuatro estados vacíos para enero de 1990 y el mensaje de rango invertido.

### Hallazgo y corrección

La cuenta del gerente mostraba **Ver reportes**, aunque `/reportes` está limitado a
administradores y devolvía 403. Se ajustó únicamente la condición de presentación
en `app/templates/auth/cuenta.html` y se añadió una aserción de regresión. No se
modificaron autenticación, SQL ni servicios de negocio.

### Capturas locales

Las imágenes de `docs/capturas/` corresponden a Firefox y PostgreSQL locales, no a
Railway. Usan exclusivamente los datos ficticios de esta revisión:

- `01-dashboard-local.png`
- `02-cliente-historial-local.png`
- `03-reservas-local.png`
- `04-inventario-alertas-local.png`
- `05-ventas-local.png`
- `06-reportes-local.png`
- `07-reportes-vacio-local.png`
- `08-rango-invalido-local.png`
- `09-menu-movil-local.png`

Railway sigue sin desplegarse. Falta que Andrew revise la instalación inicial,
credenciales normales, endurecimiento, respaldo y autorización; después se debe
crear el servicio, instalar la base una vez, generar el dominio y repetir salud,
login, navegación, reportes y cierre de sesión sobre HTTPS.

## Evidencia anterior — 2 de noviembre de 2026

Esta sección conserva la revisión de la interfaz y reportes previa a las pantallas
operativas de `8be147d` y al cargador completo de `de2282e`.

## Entorno aislado

La revisión se hizo en `feat/brian-ui-docs` con PostgreSQL 17.11. No había
Docker ni Podman disponibles, pero sí los binarios del servidor en
`/usr/lib/postgresql/17/bin`. Se creó un clúster descartable bajo `/tmp`, sin
TCP, con un socket Unix privado, una base llamada `habits_test` y un usuario de
pruebas sin privilegios de superusuario. No se usaron ni modificaron bases del
equipo, archivos `.env` o servicios del sistema.

`tests/conftest.py` exige que `TEST_DATABASE_URL` termine en `_test`. Cada caso
crea un esquema `test_<uuid>`, configura su `search_path` y elimina ese esquema
en un bloque `finally`. Antes de terminar se confirmó que no quedaban esquemas
`test_%`. El clúster temporal se detuvo y eliminó después de la revisión.

## Resultados reproducibles

Con `TEST_DATABASE_URL` apuntando exclusivamente a la base aislada y una
`SECRET_KEY` efímera en el entorno del proceso:

```text
pytest -q
190 passed in 37.90s
```

No hubo pruebas fallidas ni omitidas en la ejecución final. Además:

```text
pytest -q tests/test_reportes_ui.py
9 passed in 2.26s
ruff check .
All checks passed!
ruff format --check .
24 files already formatted
mypy app tests/test_reportes_ui.py
Success: no issues found
```

La primera ejecución de reportes produjo 8 aprobadas y 1 fallida porque el dato
de prueba fijaba una visita futura y el trigger real la rechazó correctamente.
Se corrigió la prueba para usar el mes y la zona horaria actuales. Una primera
ejecución completa sin `SECRET_KEY` dio 188 aprobadas y 2 fallidas en pruebas de
salud; al proporcionar la variable obligatoria, sin persistirla, esas 2 pruebas
y después la suite completa aprobaron. Esto fue configuración del proceso de
pruebas, no una corrección de la aplicación.

## Evidencia con PostgreSQL real

Las nueve pruebas de `test_reportes_ui.py` instalaron el SQL real en esquemas
independientes y comprobaron:

- sesión obligatoria para inicio y reportes; solo administrador accede a
  `/reportes`, mientras gerente y mesero reciben 403;
- fechas interpretadas a medianoche en `America/Guatemala`, rango no vacío y
  límite `hasta` exclusivo;
- rechazo con 400 de fecha mal formada, rango invertido y mes inválido;
- ejecución parametrizada de las cinco funciones definitivas;
- una venta de 2 unidades por Q 52 incluida y otra de 5 unidades colocada
  exactamente en `hasta` excluida;
- una visita frecuente, una reserva confirmada y su preferencia real;
- un único renglón de inventario con unidad `g`, existencia 10, referencia 100
  y saldo de lote 10: los `JOIN` descriptivos no duplicaron ni eliminaron la
  fila ni alteraron cantidades;
- comparación de dos sucursales: una con 1 reserva, 1 venta y Q 52, y otra con
  ceros reales;
- diferencias entre resultados vacíos y error PostgreSQL: el vacío conserva
  las sucursales con ceros; la ausencia de funciones devuelve 503 y un mensaje
  genérico, no una tabla vacía ni detalles internos.

No se detectó un defecto ajeno en las funciones SQL o servicios durante esta
revisión.

## Revisión visual e interactiva final

Se realizó una segunda revisión sin stubs. Se creó otro clúster PostgreSQL 17
descartable bajo `/tmp`, sin TCP, y una base exclusiva llamada
`habits_ui_test`. Se instalaron `sql/fase1/inicializar.sql` y la ampliación de
backend existente. La cuenta temporal se creó con `create-demo-admin`; los
catálogos, recetas, mesas, inventarios y lotes se cargaron con
`sql/datos_ejemplo/cargar.psql`. En esa base se agregaron un cliente, una
reserva, una visita, una preferencia y una venta ficticios del mes actual. Las
cinco funciones devolvieron respectivamente 1, 1, 1, 40 y 2 filas.

El controlador integrado no estaba disponible, pero Firefox 158 sí ofrecía
Marionette. Se controló el navegador mediante su protocolo WebDriver nativo:
los eventos indicados abajo fueron clics reales del navegador, no inferencias a
partir de capturas ni peticiones HTTP aisladas.

### Interacciones ejecutadas

- Se completó el formulario y se pulsó **Iniciar sesión**. El POST respondió
  303 y abrió `/auth/cuenta` con sesión real.
- Se pulsaron los enlaces de inicio, reportes, registro de personal y cuenta.
  Todas las pantallas respondieron 200; no hubo enlaces rotos entre las
  pantallas implementadas.
- A 720 px se pulsó dos veces el botón del menú: la clase pasó de
  `collapse navbar-collapse` a `navbar-collapse collapse show` y volvió a
  `navbar-collapse collapse`. Después se navegó por sus enlaces mediante clics.
- Se pulsó **Consultar reportes** con `2026-11-01`, `2026-12-01` y `2026-11`.
  Los valores se conservaron y aparecieron las cinco tablas con datos reales.
- Se consultó `1990-01-01` a `1990-02-01`, mes `1990-01`. Se conservaron los
  filtros y aparecieron los cuatro mensajes vacíos correspondientes; la
  comparación de sucursales mantuvo sus dos filas reales con ceros.
- Se envió el rango invertido `2026-12-01` a `2026-11-01`. La página respondió
  400, conservó los tres filtros y mostró «La fecha inicial debe ser anterior a
  la fecha final.».
- Se pulsó **Cerrar sesión**. El POST respondió 303, volvió a `/auth/login` y el
  título fue `Iniciar sesión · Habits`.

### Datos y presentación observados

En 1440 px, las tablas mostraron:

- producto `Latte de cardamomo y miel`, 2 unidades y Q 52.00;
- `Cliente Visual` con 1 visita;
- el mismo cliente con 1 reserva confirmada y su preferencia;
- 40 filas de inventario con sucursal, unidades, alertas, fechas y saldos;
- dos sucursales, la primera con 1 reserva, 1 venta y Q 52.00, y la segunda con
  valores cero.

Importes, unidades, fechas, badges y encabezados resultaron legibles. A 720 px
los filtros se apilaron y el contenido permaneció dentro de la página. Las
tablas de reservas, inventario y sucursales desbordaron únicamente dentro de su
contenedor adaptable. En inventario el área visible midió 480 px, la tabla 718
px y el desplazamiento horizontal avanzó realmente de 0 a 237.68 px de un
máximo de 238 px; se inspeccionaron ambos extremos y las columnas siguieron
legibles. Bootstrap y `styles.css` se observaron aplicados, y el comportamiento
del menú confirmó la carga del JavaScript de Bootstrap.

Se conservaron capturas temporales como evidencia durante la revisión, pero no
se versionaron porque no son las capturas de la demo final. No queda una
interacción funcional pendiente de revisión manual. Una revisión humana en un
navegador visible sigue siendo opcional para aprobación estética subjetiva, no
para suplir evidencia funcional. El servidor, Firefox, la base y las capturas
temporales se detuvieron y eliminaron al finalizar.

## Límites de aquella revisión

En aquella revisión no se modificaron el SQL de negocio, autenticación ni servicios
de Andrew, Chris o Rodrigo. Todavía no se habían implementado las pantallas
operativas, Railway, las capturas locales actuales o la demo integral.

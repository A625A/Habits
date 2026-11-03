# Verificación de interfaz y reportes de Brian

Fecha local: 2 de noviembre de 2026, America/Guatemala.

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

## Revisión visual

El controlador de navegador integrado no estaba disponible en el entorno. Se
usó Firefox headless con el HTML y CSS reales a 1440 px y 720 px. Se revisaron:

- login y dashboard en ancho de laptop;
- cuenta, registro y reportes en ancho reducido;
- carga de Bootstrap y `styles.css`, jerarquía, espaciado, formularios,
  botones, mensajes, filtros, estados vacíos y adaptación de la navegación.

El registro necesitó un proveedor visual temporal de sucursales porque su GET
consulta PostgreSQL; no se sustituyó su prueba funcional, que sí pasó contra la
base real. La revisión headless no validó clics del menú colapsable ni el aspecto
de tablas pobladas con todos los datos. No se prepararon capturas finales ni se
considera cerrada la demo.

Para la revisión manual pendiente, con una base local ya inicializada según el
README:

1. Activar `.venv`, definir `DATABASE_URL`, `SECRET_KEY` y
   `HABITS_ENV=development` solo en el entorno local.
2. Ejecutar `python -m flask --app app run --host 127.0.0.1 --port 5000`.
3. Abrir `/auth/login`; después revisar `/`, `/auth/cuenta`, `/auth/register` y
   `/reportes` con una cuenta administradora.
4. En `/reportes`, usar un intervalo que contenga los datos locales, verificar
   las cinco tablas y probar una fecha inválida y un intervalo sin resultados.
5. Repetir a 1440 px y 720 px; abrir el menú colapsable y comprobar el scroll
   horizontal de tablas sin desbordar la página.

## Límites

No se modificaron el SQL de negocio, autenticación ni servicios de Andrew,
Chris o Rodrigo. Tampoco se implementaron pantallas operativas, Railway,
capturas definitivas o la demo final.

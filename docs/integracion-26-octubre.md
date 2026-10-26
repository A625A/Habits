# Integración de Andrew — 26 de octubre

Actualiza los apartados de autenticación y auditoría de `contratos.md`.
Las columnas y PK/FK originales de `usuarios` y `sucursales` no cambian.

## Actualizar una copia con Fase 1

Instalar `requirements-dev.txt`, configurar una `SECRET_KEY` aleatoria de al menos
32 caracteres y ejecutar `flask --app app db-upgrade`. El comando aplica
`sql/01_auth.sql` y `sql/06_auditoria.sql` en una sola transacción. Es repetible y
no crea cuentas ni modifica sucursales. En una base nueva, ejecutar antes `db-init`
y `db-seed`. Nunca ejecutar estos comandos desde `wsgi.py` ni al crear workers.

El primer administrador se crea con `flask --app app create-admin`, datos del
operador y contraseña oculta. No hay password de demo. Las demás altas se hacen
desde `/auth/register` por un administrador autenticado.

## Rutas y permisos

| Interfaz | Comportamiento |
|---|---|
| GET/POST `/auth/login` | Formulario con CSRF; login válido redirige a la cuenta |
| GET `/auth/cuenta` | Cuenta actual y acciones disponibles |
| GET `/auth/me` | JSON del usuario actual, sin credenciales |
| POST `/auth/logout` | CSRF y revocación persistente del token |
| GET/POST `/auth/register` | Solo administrador; selecciona rol y sucursal activa |
| GET `/reportes/sucursales` | Administrador: todas; gerente: solo su sede; mesero: 403 |

No autenticado: 401; rol insuficiente: 403; CSRF/datos inválidos: 400.
Login incorrecto/inactivo: mismo 401 genérico. Base no disponible: 503 genérico.
El filtro de sucursal procede del usuario autenticado, nunca de la query string.
No se habilitan rutas de módulos ajenos ni permisos implícitos para ellos.

Para las nuevas rutas del equipo:

```python
from app.security import check_csrf, csrf_token, require_roles

# En el Blueprint propio, validar CSRF en toda operación que modifica datos:
bp.before_request(check_csrf)


@bp.get("/ruta-del-modulo")
@require_roles("administrador", "gerente")
def pantalla():
    # g.user contiene usuario_id, nombre, email, rol y sucursal_id verificados.
    # Aplicar también el alcance de sucursal acordado para esta operación.
    ...
```

Ejemplo ilustrativo, no implementación de un módulo. Pasar `csrf_token()` a la
plantilla e incluirlo en un input oculto `csrf_token`; para peticiones programáticas,
enviar `X-CSRF-Token`. No confiar en el rol ni ID de usuario recibidos del formulario.
Los permisos de inventario/ventas/reservas se acordarán al integrar esos módulos.

Las plantillas actuales viven en `app/templates/auth/`; Brian puede adaptarlas
a su `base.html` conservando acciones, nombres de campos y tokens CSRF. Su
`app/routes/reportes.py` sigue reservado; Andrew proporciona el endpoint de datos
en `app/routes/comparacion.py`, sin construir el dashboard.

## Sesiones

Tabla aditiva `sesiones`: token SHA-256 como PK, FK `usuario_id` con DELETE CASCADE,
creación y vencimiento. El token aleatorio original vive en la cookie firmada,
sin roles ni hashes de contraseña. Se valida contra BD en cada ruta protegida.
Vence a las ocho horas sin renovación por actividad. Logout elimina el token.

Triggers revocan sesiones al cambiar `password_hash`, `rol`, `activo` o
`sucursal_id`, y al cambiar el estado activo de una sucursal. Cambiar nombre/email
no revoca sesiones. La contraseña se valida con Werkzeug/scrypt. No se implementa
todavía una pantalla de cambio de contraseña ni de edición de personal.

`HABITS_ENV=development` para HTTP local y `production` para HTTPS (cookie Secure).
Siempre HttpOnly y SameSite=Lax. `SECRET_KEY` proviene del entorno, sin fallback.
La aplicación no confía en cabeceras de proxy; Brian verificará el proxy de Railway
antes de configurar cualquier middleware. No hay rate limiting distribuido en
esta entrega local; debe definirse antes de exposición pública. Las sesiones
vencidas dejan de autorizar automáticamente; el mantenimiento posterior puede
eliminarlas con `DELETE FROM sesiones WHERE expira_en <= CURRENT_TIMESTAMP`.

## Conectar auditoría de un módulo futuro

`auditoria` contiene ID, fecha, schema, tabla, PK como texto, operación, usuario de
aplicación opcional, usuario PostgreSQL y snapshots JSONB de columnas permitidas.
No tiene FK al actor para conservar historia tras eliminar usuarios. No se audita
la propia bitácora ni la tabla de sesiones. La lista de usuarios excluye nombre,
email y password_hash; la de sucursales excluye dirección. No se escriben credenciales.

En una operación del servicio, abrir transacción, establecer actor y ejecutar DML:

```python
db = get_db()
with db.transaction():
    db.execute("SELECT set_config('habits.usuario_id', %s, true)", (str(actor_id),))
    # Ejecutar aquí las escrituras del módulo con parámetros.
```

`actor_id` debe venir del usuario autenticado. `true` limita el valor a la
transacción; nunca usar SET global en conexiones compartidas. SQL directo sin
actor deja NULL y registra CURRENT_USER. El actor es contexto confiado de la
aplicación, no una identidad SQL verificada: quien controla la conexión puede
establecer ese valor. El propietario de la BD puede modificar tablas/triggers;
esta bitácora académica no pretende ser inalterable frente al administrador de BD.

Después de crear su tabla, cada dueño añade un trigger `AFTER INSERT OR UPDATE OR
DELETE FOR EACH ROW EXECUTE FUNCTION auditar_cambio(...)`. El primer argumento
es el nombre de su PK; los siguientes son exclusivamente los campos aprobados
para snapshots. La PK debe existir y no ser NULL. No usar esta función sin revisar
su lista permitida ni incluir contraseñas, tokens o datos sensibles.

Prueba demostrativa en `tests/test_audit.py` usa una tabla efímera genérica;
no crea reservas ni inventario. Los triggers del equipo quedan pendientes de sus
tablas reales y aprobación de columnas. Un error del trigger aborta la operación;
no se admite guardar el cambio sin su evento. ROLLBACK revierte también la bitácora.

## Contrato SQL futuro de comparación

La consulta lista en `sql/pendientes/comparacion_ventas_reservas.sql` requiere dos
vistas de adaptación **todavía no creadas ni acordadas con sus dueños**:

| Dueño | Vista propuesta | Columnas requeridas |
|---|---|---|
| Rodrigo | reporte_ventas_confirmadas | venta_id BIGINT único, sucursal_id BIGINT, fecha TIMESTAMPTZ, total NUMERIC no nulo |
| Chris | reporte_reservas_vigentes | reserva_id BIGINT único, sucursal_id BIGINT, inicio TIMESTAMPTZ |

Una fila por venta/reserva, excluyendo canceladas. Rodrigo define cómo proyectar
su importe histórico sin duplicar detalle; Chris valida los estados incluidos.
No se asume que sus tablas reales ya tengan esos nombres de columnas.

Parámetros psycopg: `desde` inclusivo, `hasta` exclusivo (fechas con zona horaria),
`sucursal_id` opcional. Convertir límites locales de Guatemala a instantes antes de
consultar. Las CTE agregan cada vista por sede antes de unirlas. Se incluyen sedes
sin operaciones con cero **solo cuando ambos módulos existen y fueron validados**.

Prueba del contrato: dos importes 10 y 20 y tres reservas producen total 30, no 90;
una venta en el límite superior se excluye. Son fixtures temporales en la BD de
pruebas, no datos cargados en desarrollo. La integración con los módulos reales
y el reporte académico completo siguen pendientes.

## Referencias técnicas

- [Seguridad en Flask](https://flask.palletsprojects.com/en/stable/web-security/).
- [Configuración de cookies](https://flask.palletsprojects.com/en/stable/config/).
- [Hash de contraseñas en Werkzeug](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash).
- [Triggers PostgreSQL](https://www.postgresql.org/docs/17/plpgsql-trigger.html).

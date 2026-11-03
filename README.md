# Habits
Proyecto 2 base de Datos 1, Cafeteria y postreria "Habits"

**Fases 1 y 2 integradas en `main`: base PostgreSQL y backend funcional.**
Se conservan las 18 tablas, restricciones, procedimientos, triggers de auditoría,
cinco reportes SQL, autenticación y endpoints JSON de clientes, reservas/visitas,
catálogo/recetas, inventario, producción y ventas.

El historial incluye los commits originales de Chris mediante un merge normal
con resolución selectiva. Su trabajo de clientes y reservas ya está adaptado al
backend actual; el SQL anterior y las plantillas no se reinstalan.
Ver [integración, contribuciones y pendientes](docs/integracion-main-fase-2.md).

- [Instalación de la base completa](docs/implementacion-bd-fase-1.md) y [DER](docs/DER-completo-propuesto.md).
- [Backend: instalación, permisos, endpoints y ejemplos](docs/fase-2-backend.md).
- [SQL avanzado para la presentación](docs/sql-aplicado-fase-2.md).

La plantilla Bootstrap, el inicio y la presentación de los cinco reportes ya están
implementados. Las pantallas operativas de clientes, reservas, inventario, producción
y ventas, además de Railway, siguen pendientes. Los comandos Flask antiguos de abajo
conservan su alcance original;
para las 18 tablas usar `sql/fase1/inicializar.sql` y luego `db-backend-upgrade`.
Las secciones de equipos/demo documentan trabajo histórico; no crean cuentas
ni cargan datos operativos automáticamente.

Repositorio: <https://github.com/A625A/Habits>. La integración y el push a `main`
están autorizados para esta entrega una vez superadas las verificaciones.
No se autoriza despliegue ni trabajo de la siguiente fase.

## Requisitos

- Python 3.12 o posterior (verificado localmente con 3.14.6).
- PostgreSQL 17 y sus comandos `initdb`, `pg_ctl`, `createuser`, `createdb`, `psql`.
- Git. En Windows usar WSL para estos comandos; el entorno verificado fue macOS.

## Instalar Python y configurar variables

Clonar `main`, que reúne las fases implementadas, y trabajar desde la raíz:

```bash
git clone --branch main https://github.com/A625A/Habits.git
cd Habits
```

Las ramas del reparto histórico se conservan; no son el punto de partida para
instalar la versión integrada actual.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp -n .env.example .env
chmod 600 .env
python -c 'import secrets; print(secrets.token_hex(32))'
```

Guardar el último valor como `SECRET_KEY` en `.env`. `DATABASE_URL` y
`TEST_DATABASE_URL` deben usar las contraseñas elegidas en el paso siguiente.
Las variables del entorno tienen prioridad sobre `.env`. No reemplazar un `.env`
existente ni compartirlo. `SECRET_KEY` es obligatoria: aleatoria, al menos 32 caracteres,
sin valores de ejemplo. `HABITS_ENV=development` permite cookies en HTTP local;
`HABITS_ENV=production` activa cookies Secure para HTTPS. En ambos casos se usa
HttpOnly, SameSite=Lax y expiración fija de ocho horas.

## PostgreSQL local aislado

Si ya se usa otro PostgreSQL, crear **bases nuevas** en él y adaptar las URLs.
Para un clúster exclusivo del proyecto, con PostgreSQL instalado y en PATH:

```bash
mkdir -p .local/socket
chmod 700 .local .local/socket
initdb -D .local/postgres -U habits_admin --auth-local=trust --auth-host=scram-sha-256 --encoding=UTF8 --locale=C
pg_ctl -D .local/postgres -l .local/postgres.log -o "-h 127.0.0.1 -p 55432 -k '$PWD/.local/socket'" start
createuser -h "$PWD/.local/socket" -p 55432 -U habits_admin --pwprompt habits_app
createdb -h "$PWD/.local/socket" -p 55432 -U habits_admin -O habits_app habits
createuser -h "$PWD/.local/socket" -p 55432 -U habits_admin --pwprompt habits_test
createdb -h "$PWD/.local/socket" -p 55432 -U habits_admin -O habits_test habits_test
```

`initdb` se ejecuta **una sola vez**. Este clúster escucha únicamente en loopback.
El socket usa confianza local dentro de `.local` con permiso 700; TCP exige contraseña.
Las cuentas de aplicación y pruebas no son superusuarios. Elegir contraseñas distintas;
si incluyen caracteres reservados, codificarlos en la URL. No utilizar la cuenta
administradora del clúster en Flask.

En macOS, si falta PostgreSQL: `brew install postgresql@17` y agregar
`$(brew --prefix postgresql@17)/bin` al PATH. No es necesario `brew services start`.

En **la copia original de Andrew** el clúster, las dos bases y el `.env` privado ya
están preparados; no se incluyen al clonar GitHub.
Para detenerlo/reanudarlo sin borrar datos:

```bash
pg_ctl -D .local/postgres stop -m fast
pg_ctl -D .local/postgres -l .local/postgres.log -o "-h 127.0.0.1 -p 55432 -k '$PWD/.local/socket'" start
```

## Crear esquema y ejecutar Flask

```bash
python -m flask --app app db-init
python -m flask --app app db-seed
python -m flask --app app db-upgrade
python -m flask --app app run --host 127.0.0.1 --port 5000
```

`db-init` crea `sql/01_core.sql` en una sola transacción. Rechaza tablas existentes;
no contiene DROP ni modifica datos de una instalación previa. No repetirlo si ya
se creó el esquema. `db-seed` ejecuta `sql/08_seed.sql`: dos sucursales ficticias,
sin usuarios, productos ni contraseñas. Es repetible y preserva las filas existentes.
En la copia original de Andrew ambos comandos ya se ejecutaron al validar la entrega.

Si ya tenés Fase 1, ejecutar **solo** `db-upgrade`: aplica `01_auth.sql` y
`06_auditoria.sql` juntos, en una transacción, sin cambiar columnas existentes.
Es repetible y no carga cuentas ni datos de negocio.

```bash
curl --fail http://127.0.0.1:5000/health
curl --fail http://127.0.0.1:5000/health/db
```

`/health` confirma que Flask responde; `/health/db` ejecuta `SELECT 1` y devuelve
200 o 503. Confirma conectividad, no presencia del esquema ni disponibilidad de
módulos futuros. `/` y los prefijos reservados devuelven 404 hasta que sus dueños
agreguen rutas. Nunca se crea la base al importar Flask o iniciar un worker.

También se puede aplicar cada SQL con `psql -v ON_ERROR_STOP=1 --single-transaction -f`
usando una conexión configurada por el operador; no aplicar todos los SQL a ciegas.

## Primer administrador, login y permisos

### Carga opcional de datos de ejemplo

Para una base local de práctica con el esquema completo de Fase 1, el catálogo
inicial y un administrador activo ya creado, se puede ejecutar como propietario
de la base (reemplazar `SU_ID` por el `usuario_id` de ese administrador):

```bash
psql -X -h 127.0.0.1 -p 55432 -U habits_app -d habits -W -v usuario_id=SU_ID -f sql/datos_ejemplo/cargar.psql
```

El ID se puede consultar con `SELECT usuario_id, nombre FROM usuarios WHERE
rol='administrador' AND activo;`. Adaptar host, puerto y usuario a la instalación.
La carga es manual y ficticia: agrega tres mesas por sucursal, veinte ingredientes,
recetas de ejemplo para los doce productos y sus inventarios independientes.
Las cantidades son para practicar, no fórmulas comerciales validadas.

Cada inventario sin lotes recibe dos: uno vence en tres días y otro en treinta,
contados desde la carga según la fecha de Guatemala. En una base nueva se crean
cuarenta inventarios y ochenta lotes. Las recetas existentes se conservan completas;
las mesas y referencias existentes tampoco se reemplazan. Si un ingrediente tiene
otra unidad o está inactivo, se cancela toda la carga para revisarlo.

Se puede repetir el comando: no duplica registros ni repone lotes consumidos o
vencidos. Un inventario que ya tenga cualquier lote se conserva sin entradas nuevas.
No crea cuentas, contraseñas, reservas, producciones ni ventas. La carga completa
se guarda en una transacción; un error la deshace. No se ejecuta al iniciar Flask.

Para revisar los datos, abrir `sql/datos_ejemplo/revisar_reservas_inventario.sql`
en pgAdmin o ejecutarlo con `psql -X -v ON_ERROR_STOP=1 -f` y la conexión local.
Solo consulta: muestra horarios, posibles cruces, existencias por sede y lotes
vencidos o próximos a vencer. La consulta de cruces debe devolver cero filas.
Una reserva termina a los 90 minutos y otra puede comenzar justo a esa hora.
El inventario incluye lotes que vencen hoy y excluye los que vencieron antes;
la alerta de existencias se activa al llegar al 15 % de la referencia o menos.

Las comprobaciones con los datos de ejemplo se ejecutan con:

```bash
python -m pytest tests/test_datos_ejemplo.py -q
```

Requieren `TEST_DATABASE_URL` configurada para una base exclusiva de pruebas
terminada en `_test`, como se explica en la sección de pruebas. Se comprueban
capacidad, horarios, cancelación, referencias de sucursal y registros inactivos;
también vencimientos de hoy, siete y ocho días, límites del 15 % y saldos inválidos.
Cada caso usa un esquema temporal separado y lo elimina al terminar.

### Acceso rápido para la demo local

Andrew autorizó una cuenta de demostración: **usuario `admin`, contraseña `123`**.
En su copia local ya está preparada. Para habilitarla en otra copia, configurar
`HABITS_ENV=development` y `HABITS_DEMO_LOGIN=1` en `.env`, aplicar los comandos de
esquema anteriores y ejecutar:

```bash
python -m flask --app app create-demo-admin
python -m flask --app app run --host 127.0.0.1 --port 5000
```

Abrir `http://127.0.0.1:5000/auth/login` e ingresar `admin` y `123`, sin correo.
El comando guarda un hash scrypt y no reemplaza cuentas existentes. Usa DEMO-01
y el correo técnico reservado `admin@demo.invalid`; no envía correos ni modifica
el esquema. La excepción de contraseña corta solo corresponde a esta demo.

La bandera está apagada por defecto. Ni el arranque, ni seed, ni db-upgrade crean
la cuenta. `HABITS_ENV=production` bloquea creación, login y sesiones demo, aunque
se active la bandera o se copie la base local. Para deshabilitarla localmente,
poner `HABITS_DEMO_LOGIN=0` y reiniciar Flask. No publicar el servidor de demo local.

### Personal normal

El operador de la copia local debe crear el primer administrador con **sus datos**:

```bash
python -m flask --app app create-admin
```

Pide nombre, correo, código de una sucursal activa (`DEMO-01` o `DEMO-02` en el
seed actual) y contraseña oculta con confirmación. No recibe la contraseña como
argumento y no existen credenciales predeterminadas. El comando rechaza nuevas
altas iniciales si ya hay un administrador, incluso inactivo; recuperación de una
cuenta bloqueada requiere intervención explícita del operador, no registro público.

Abrir `http://127.0.0.1:5000/auth/login`. Tras iniciar sesión, `/auth/cuenta` permite
cerrarla y, para administradores, acceder al registro de personal en `/auth/register`.
La contraseña requiere 12–128 caracteres y se almacena con scrypt de Werkzeug.
La cookie no contiene contraseñas ni roles; los tokens se guardan hasheados en
PostgreSQL. Logout revoca el token, y los cambios de contraseña, rol, estado o
sucursal del usuario revocan sus sesiones. Desactivar/reactivar una sucursal también.

| Acción | Administrador | Gerente | Mesero |
|---|---|---|---|
| Ver su cuenta y cerrar sesión | Sí | Sí | Sí |
| Registrar personal | Sí | No | No |
| GET `/reportes/sucursales` | Todas las sedes | Solo su sede | No |

Las pantallas de autenticación heredan la plantilla compartida de Brian sin cambiar
sus contratos. Los POST requieren CSRF. `/auth/me` ofrece
los datos de la sesión actual para integración, sin hashes ni tokens.

La base de desarrollo de Andrew contiene la cuenta demo autorizada. Las otras
cuentas y contraseñas efímeras usadas en pruebas nunca se cargan allí. En una base
nueva sin demo, `create-admin` continúa disponible para el alta inicial normal.

## Inicio y reportes web

Después de iniciar sesión, abrir `/` para acceder al dashboard. La portada enlaza
solo pantallas HTML disponibles; identifica clientes, reservas, inventario, producción
y ventas como pantallas pendientes, aunque sus APIs JSON ya existan.

Los administradores pueden abrir `/reportes`. La interfaz ejecuta las cinco funciones
definitivas instaladas por `sql/fase1/50_reportes.sql`; no usa el endpoint histórico
`/reportes/sucursales` como fuente. Gerentes y meseros reciben 403 porque las funciones
definitivas no admiten un filtro de sucursal que preserve su alcance de acceso.

Filtros GET de `/reportes`:

- `desde=AAAA-MM-DD`: inicio incluido para productos, visitas, reservas y sucursales.
- `hasta=AAAA-MM-DD`: límite final excluido para esos cuatro reportes.
- `mes=AAAA-MM`: mes de vencimientos para el reporte de inventario.

Sin filtros se consulta el mes actual en `America/Guatemala`. Fechas inválidas o un
intervalo vacío/invertido devuelven 400; una falla de PostgreSQL devuelve 503 y no
se presenta como un conjunto sin resultados. Un resultado válido sin filas conserva
200 y muestra su estado vacío.

## Auditoría y reporte

La tabla `auditoria` registra INSERT/UPDATE/DELETE de `sucursales` y `usuarios`,
incluidos cambios por SQL directo. Se guarda dentro de la misma transacción;
ROLLBACK elimina el evento. No reconstruye cambios anteriores a la instalación.
Campos sensibles de usuarios quedan excluidos mediante una lista permitida.
SQL directo sin actor de aplicación registra `usuario_id = NULL` y el usuario de BD.

`sql/reportes_sucursales.sql` compara personal real por sucursal. Ventas/reservas
devuelven NULL y el endpoint informa `pendiente_modulos`: no se inventan ceros.
`sql/pendientes/comparacion_ventas_reservas.sql` agrega ambas métricas por separado;
requiere las vistas contratadas de Rodrigo/Chris y **no se ejecuta automáticamente**.
Ver [integración del 26](docs/integracion-26-octubre.md).

## Pruebas y calidad

```bash
python -m pytest
python -m pytest tests/test_reportes_ui.py -q
python -m mypy
python -m ruff check .
python -m ruff format --check .
```

Las pruebas de integración **requieren PostgreSQL real**. `TEST_DATABASE_URL` debe
apuntar a una base exclusiva cuyo nombre termine en `_test`. Cada caso crea un
schema aleatorio y elimina únicamente ese schema al terminar. No se usa SQLite
ni se omiten silenciosamente las pruebas si falta PostgreSQL. No apuntar pruebas
a una base con datos importantes, aunque termine en `_test`.

Se comprueban HTTP, fallas de conexión, DDL atómico, seed repetible, restricciones,
relaciones y COMMIT/ROLLBACK. Evidencia y límites: [docs/verificacion.md](docs/verificacion.md).
Para esta ampliación: [verificación del 26](docs/verificacion-26-octubre.md).

## Estructura y trabajo del equipo

```text
app/__init__.py          factory y configuración — Andrew
app/db.py                conexión y CLI de esquema — Andrew
app/routes/              Blueprints ya registrados, uno por módulo
app/services/            servicios de negocio por integrante
app/templates/           Brian coordina base.html; cada dueño su módulo
app/static/css/          estilos — Brian
sql/01_core.sql          sucursales y usuarios — Andrew
sql/01_auth.sql          sesiones y revocación — Andrew
sql/06_auditoria.sql     tabla y triggers — Andrew
sql/08_seed.sql          seed mínimo — Andrew coordina ampliaciones
docs/contratos.md        IDs, rutas, límites y orden de SQL
docs/DER-base.md         diagrama del esquema realmente implementado
tests/                  pruebas HTTP, CLI y PostgreSQL
wsgi.py                 entrada WSGI
```

| Integrante | Rama | Punto de partida |
|---|---|---|
| Andrew | `feat/andrew-core-deploy` | Autenticación, auditoría y SQL de comparación |
| Rodrigo | `feat/rodrigo-stock-sales` | `app/routes/inventario.py`, `ventas.py`; SQL 03–05 |
| Chris | `feat/chris-reservas` | `app/routes/clientes.py`, `reservas.py`; SQL 02 |
| Brian | `feat/brian-ui-docs` | `app/routes/inicio.py`, `reportes.py`, templates y CSS |

Las cuatro ramas comparten la misma base inicial. Cada integrante debe clonar su
rama en una copia propia. Si ya clonó el repositorio, ejecutar `git fetch origin`
y `git switch NOMBRE` para seleccionar su rama.
Cada persona hace sus commits; no se fabrican aportes de los demás.

Antes de implementar, leer [contratos](docs/contratos.md) y [alcance](docs/fase-1-andrew.md).
El alcance actual de Andrew está en [andrew-26-octubre.md](docs/andrew-26-octubre.md).
Los Blueprints vacíos permiten agregar rutas sin modificar `app/__init__.py`.
No cambiar columnas compartidas sin coordinación con Andrew. Cada módulo posee
sus servicios, SQL y pruebas. Brian ampliará este README para la entrega final.

## WSGI y despliegue posterior

Prueba local del servidor WSGI:

```bash
gunicorn --bind 127.0.0.1:8000 wsgi:app
```

Railway queda para Brian, con revisión de Andrew. Se entregan `wsgi.py`, Gunicorn
y configuración mediante `DATABASE_URL` y `SECRET_KEY`; no se ha creado ningún
servicio remoto. Antes de desplegar faltan los módulos funcionales y autorización.
No aplicar DDL ni seed en cada arranque. Los costos y ajustes del servicio se
verificarán al preparar ese despliegue; esta entrega no los presupone.

En Railway configurar `HABITS_ENV=production`, `SECRET_KEY` aleatoria y
`DATABASE_URL` del servicio, sin debug. El comando previsto para Brian es
`gunicorn --bind 0.0.0.0:$PORT wsgi:app`. `wsgi.py` ya expone la factory y no necesita
cambios ni DDL al importar. Antes de exponerlo públicamente, Brian y Andrew deben
validar HTTPS/proxy, límites de intentos de login y mantenimiento de sesiones
expiradas. Esta fase verifica autenticación local, no endurecimiento de producción.

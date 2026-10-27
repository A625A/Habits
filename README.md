# Habits
Proyecto 2 base de Datos 1, Cafeteria y postreria "Habits"

**Andrew, entrega del 26 de octubre**: base Flask/PostgreSQL, autenticación de
personal, roles, auditoría del core y comparación de sucursales. Reservas, inventario,
producción, ventas y dashboard siguen a cargo de sus respectivos integrantes.

Repositorio: <https://github.com/A625A/Habits>. Fase 1 se publicó e integró en `main`.
La entrega del 26 y el acceso demo se publican por autorización de Andrew en
`feat/andrew-core-deploy`, desde `5bb3939`. No se autorizó merge ni despliegue.

## Requisitos

- Python 3.12 o posterior (verificado localmente con 3.14.6).
- PostgreSQL 17 y sus comandos `initdb`, `pg_ctl`, `createuser`, `createdb`, `psql`.
- Git. En Windows usar WSL para estos comandos; el entorno verificado fue macOS.

## Instalar Python y configurar variables

Clonar la rama propia (ejemplo de Andrew; ver las demás ramas más abajo) y trabajar
desde la raíz del repositorio:

```bash
git clone --branch feat/andrew-core-deploy https://github.com/A625A/Habits.git
cd Habits
```

Clonar sin seleccionar rama abre `main`, que conserva Fase 1. Seleccionar la rama
de Andrew para disponer de esta ampliación de autenticación/auditoría y demo.

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

Las pantallas de autenticación son mínimas y propias de Andrew; Brian conserva
`base.html`, navegación y dashboard. Los POST requieren CSRF. `/auth/me` ofrece
los datos de la sesión actual para integración, sin hashes ni tokens.

La base de desarrollo de Andrew contiene la cuenta demo autorizada. Las otras
cuentas y contraseñas efímeras usadas en pruebas nunca se cargan allí. En una base
nueva sin demo, `create-admin` continúa disponible para el alta inicial normal.

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

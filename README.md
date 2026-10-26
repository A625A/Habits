# Habits
Proyecto 2 base de Datos 1, Cafeteria y postreria "Habits"

Base inicial de **Andrew, Fase 1**: Flask modular, PostgreSQL real, sucursales,
usuarios y contratos para trabajar en equipo. Todavía no hay login, CRUD de negocio
ni pantallas. El único HTTP implementado es `/health` y `/health/db`.

Repositorio de trabajo: <https://github.com/A625A/Habits>. La base de esta entrega
está integrada en `main` y sincronizada con las cuatro ramas del equipo.
Andrew autorizó la publicación y esta integración; no se ha realizado despliegue.

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

Clonar sin seleccionar rama abre `main`, que también contiene esta base.

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
existente ni compartirlo. La clave queda preparada para la autenticación posterior;
esta fase no crea sesiones ni implementa permisos efectivos.

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
python -m flask --app app run --host 127.0.0.1 --port 5000
```

`db-init` crea `sql/01_core.sql` en una sola transacción. Rechaza tablas existentes;
no contiene DROP ni modifica datos de una instalación previa. No repetirlo si ya
se creó el esquema. `db-seed` ejecuta `sql/08_seed.sql`: dos sucursales ficticias,
sin usuarios, productos ni contraseñas. Es repetible y preserva las filas existentes.
En la copia original de Andrew ambos comandos ya se ejecutaron al validar la entrega.

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

## Estructura y trabajo del equipo

```text
app/__init__.py          factory y configuración — Andrew
app/db.py                conexión y CLI de esquema — Andrew
app/routes/              Blueprints ya registrados, uno por módulo
app/services/            servicios de negocio por integrante
app/templates/           Brian coordina base.html; cada dueño su módulo
app/static/css/          estilos — Brian
sql/01_core.sql          sucursales y usuarios — Andrew
sql/08_seed.sql          seed mínimo — Andrew coordina ampliaciones
docs/contratos.md        IDs, rutas, límites y orden de SQL
docs/DER-base.md         diagrama del esquema realmente implementado
tests/                  pruebas HTTP, CLI y PostgreSQL
wsgi.py                 entrada WSGI
```

| Integrante | Rama | Punto de partida |
|---|---|---|
| Andrew | `feat/andrew-core-deploy` | Core y conexión; login en la siguiente fase |
| Rodrigo | `feat/rodrigo-stock-sales` | `app/routes/inventario.py`, `ventas.py`; SQL 03–05 |
| Chris | `feat/chris-reservas` | `app/routes/clientes.py`, `reservas.py`; SQL 02 |
| Brian | `feat/brian-ui-docs` | `app/routes/inicio.py`, `reportes.py`, templates y CSS |

Las cuatro ramas comparten la misma base inicial. Cada integrante debe clonar su
rama en una copia propia. Si ya clonó el repositorio, ejecutar `git fetch origin`
y `git switch NOMBRE` para seleccionar su rama.
Cada persona hace sus commits; no se fabrican aportes de los demás.

Antes de implementar, leer [contratos](docs/contratos.md) y [alcance](docs/fase-1-andrew.md).
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

# Habits Cafetería

Proyecto 2 de Base de Datos 1 (CC3088). Aplicación web con Flask y PostgreSQL para
una cafetería con dos sucursales y un menú compartido de doce productos.

Incluye usuarios con tres roles, clientes e historial, reservas de 90 minutos,
visitas, mesas, ingredientes, recetas, inventario por lotes, producción, ventas,
auditoría automática y los cinco reportes de la consigna.

- [Modelo y DER de las 18 tablas](docs/DER.md).
- [API y permisos](docs/api.md).
- [SQL explicado y ejemplos ejecutables](docs/sql.md).
- [Recorrido de presentación y comprobaciones](docs/demo.md).

## Abrirlo en esta computadora

Hacer doble clic en **iniciar.bat**. Se inicia PostgreSQL si hace falta y se abre
**http://127.0.0.1:5059**. Dejar abierta la ventana mientras se usa el sistema;
**Ctrl + C** detiene la aplicación. Los datos quedan guardados en `habits_local`.
La cuenta de demostración local es **usuario `admin`, contraseña `123`**.

Desde la terminal de VS Code también se puede usar:

```powershell
.\.venv\Scripts\python.exe run.py
```

La configuración de esta computadora está en `.env`, que no se sube a Git.
`DATABASE_URL` contiene la conexión con una cuenta propia sin permisos de superusuario.
`SECRET_KEY` conserva la sesión y `HABITS_DEMO_LOGIN=1` habilita el acceso de ejemplo.
`HABITS_PORT` define el puerto web (5059). Si `HABITS_PGDATA` y `HABITS_PG_CTL`
están configurados, el iniciador enciende ese clúster existente usando `HABITS_PGPORT`.
Si PostgreSQL ya funciona como servicio, se pueden omitir esas tres últimas variables.
El arranque no instala tablas ni crea cuentas ni repite la carga de datos.

Los pasos siguientes son para preparar **otra computadora** desde cero.

## Requisitos

- Python 3.12 o posterior.
- PostgreSQL 17 o 18, incluida la extensión `btree_gist`, con `initdb`, `pg_ctl`,
  `createuser`, `createdb` y `psql` en el PATH.
- Git y un navegador con JavaScript. Bootstrap 5.3.3 está incluido en
  `app/static/vendor/bootstrap`; los estilos y el menú funcionan sin internet.

Los comandos siguientes son para Linux, macOS o Windows con WSL. En macOS se puede
instalar PostgreSQL con `brew install postgresql@17` y agregar
`$(brew --prefix postgresql@17)/bin` al PATH.

## 1. Clonar e instalar

```bash
git clone --branch main https://github.com/A625A/Habits.git
cd Habits
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp -n .env.example .env
chmod 600 .env
python -c 'import secrets; print(secrets.token_hex(32))'
```

Guardar el valor generado como `SECRET_KEY` en `.env`. Debe tener al menos 32
caracteres. `.env` es privado y no se versiona. Las variables exportadas en la
terminal tienen prioridad sobre ese archivo.

## 2. Crear PostgreSQL aislado

Estos pasos crean un clúster nuevo que escucha solo en esta computadora, en el
puerto 55432. Si ese puerto está ocupado, elegir otro y cambiarlo también en las
URLs. Si ya existe un PostgreSQL propio, crear dos bases nuevas y adaptar la conexión.

```bash
mkdir -p .local/socket
chmod 700 .local .local/socket
initdb -D .local/postgres -U habits_admin --auth-local=trust --auth-host=scram-sha-256 --encoding=UTF8 --locale=C
pg_ctl -D .local/postgres -l .local/postgres.log -o "-h 127.0.0.1 -p 55432 -k '$PWD/.local/socket'" start
createuser -h "$PWD/.local/socket" -p 55432 -U habits_admin --pwprompt habits_app
createdb -h "$PWD/.local/socket" -p 55432 -U habits_admin -O habits_app habits
createuser -h "$PWD/.local/socket" -p 55432 -U habits_admin --pwprompt habits_test
createdb -h "$PWD/.local/socket" -p 55432 -U habits_admin -O habits_test habits_test
psql -X -h "$PWD/.local/socket" -p 55432 -U habits_admin -d habits \
  -v ON_ERROR_STOP=1 -f sql/fase1/rol_operaciones.sql \
  -c 'GRANT habits_operaciones TO habits_app, habits_test;'
```

`initdb` se ejecuta una sola vez. Elegir contraseñas distintas para `habits_app` y
`habits_test`; no son superusuarios. El socket admite confianza local dentro del
directorio privado; TCP exige contraseña. Flask no debe usar `habits_admin`.

Completar `.env` con esas contraseñas (codificar caracteres reservados de las URLs):

```dotenv
DATABASE_URL=postgresql://habits_app:CAMBIAR@127.0.0.1:55432/habits
TEST_DATABASE_URL=postgresql://habits_test:CAMBIAR@127.0.0.1:55432/habits_test
SECRET_KEY=CAMBIAR_POR_LA_CLAVE_GENERADA
HABITS_ENV=development
HABITS_DEMO_LOGIN=0
```

## 3. Instalar tablas y crear el administrador

```bash
psql -X -h 127.0.0.1 -p 55432 -U habits_app -d habits -W \
  -v ON_ERROR_STOP=1 -f sql/fase1/inicializar.sql
python -m flask --app app db-backend-upgrade
python -m flask --app app create-admin
```

El instalador crea las 18 tablas, restricciones, vistas, procedimientos, triggers,
reportes, dos sucursales y doce productos en una transacción. La actualización
habilita los permisos del backend y la recepción de lotes. Ambos pasos son explícitos:
el arranque del servidor no instala ni carga nada. Para una instalación compatible
se pueden repetir, en ese mismo orden, sin borrar operaciones ni cambiar precios.
Un esquema parcial o desconocido requiere revisión antes de instalar.

`create-admin` solicita nombre, correo, código de sucursal (`DEMO-01` o `DEMO-02`)
y contraseña oculta de 12–128 caracteres. Solo sirve para el primer administrador;
las siguientes cuentas se crean desde **Personal**, después de iniciar sesión.
Las contraseñas se guardan con scrypt.

No ejecutar además `db-init`, `db-seed` o `db-upgrade`: son comandos conservados
para instalaciones antiguas del esquema básico, no el flujo de instalación completa.

## 4. Cargar los datos de ejemplo

Consultar el ID del administrador creado:

```bash
psql -X -h 127.0.0.1 -p 55432 -U habits_app -d habits -W \
  -c "SELECT usuario_id, nombre FROM usuarios WHERE rol='administrador' AND activo;"
```

Sustituir `SU_ID` por ese número y ejecutar **en la base de práctica**:

```bash
psql -X -h 127.0.0.1 -p 55432 -U habits_app -d habits -W \
  -v ON_ERROR_STOP=1 -v usuario_id=SU_ID -f sql/datos_ejemplo/cargar_demo.psql
```

La carga es ficticia y atómica. En una base nueva deja:

| Datos | Cantidad |
|---|---:|
| Sucursales / productos | 2 / 12 |
| Mesas / ingredientes / configuraciones de inventario | 6 / 20 / 40 |
| Lotes de ingredientes | 82 |
| Clientes / preferencias | 6 / 12 |
| Reservas | 10: 6 completadas, 2 confirmadas y 2 canceladas |
| Visitas / lotes producidos / ventas | 12 / 12 / 14 |

Cada sucursal tiene seis visitas y siete ventas. Con el catálogo inicial los importes
son Q316 y Q476. Hay ventas de todos los productos; una visita tiene dos compras
para demostrar que ventas y visitas son métricas distintas. Dos lotes vencen el día
de la carga y permiten mostrar alertas. Las recetas y precios son ejemplos académicos.

La carga usa los procedimientos de producción y venta, por lo que descuenta stock
realmente. No crea cuentas ni contraseñas. Repetirla conserva las fechas originales,
no duplica compras ni repone lotes consumidos. Si encuentra datos incompatibles o un
conjunto demo incompleto, revierte toda la carga. Para presentar en otro mes,
seleccionar el período original o usar una base nueva.

`sql/datos_ejemplo/cargar.psql` es la alternativa que carga solo mesas, recetas e
inventario. La carga completa ya la incluye; no hace falta ejecutar ambas.

## 5. Ejecutar y usar

```bash
python run.py
```

Abrir [Habits local](http://127.0.0.1:5059), iniciar sesión con el administrador y
entrar al módulo desde Inicio. Para verificar conectividad:

```bash
curl --fail http://127.0.0.1:5059/health
curl --fail http://127.0.0.1:5059/health/db
```

`/health/db` comprueba la conexión; no sustituye la instalación del esquema.
En Windows, `iniciar.bat` usa el entorno `.venv` de esta carpeta.

| Acción | Administrador | Gerente | Mesero |
|---|---|---|---|
| Registrar personal y modificar catálogo/recetas | Sí | No | No |
| Clientes, preferencias y observaciones | Sí | Sí | Sí |
| Reservas, visitas y ventas | Todas las sedes | Su sede | Su sede |
| Configurar mesas, recibir ingredientes y producir | Todas las sedes | Su sede | No |
| Consultar ingredientes disponibles, lotes y alertas | Todas las sedes | Su sede | No |
| Consultar mesas, catálogo y productos terminados | Sí | Su sede | Su sede |
| Cinco reportes administrativos | Sí | No | No |

Los clientes y el catálogo son compartidos; el historial operativo se limita a la
sede autorizada. Para una compra identificada, registrar antes la visita o la llegada
de su reserva. Una venta sin visita es anónima. La llegada completa la reserva sin
liberar sus 90 minutos; cancelarla sí libera el intervalo. No se anulan ventas.

Las bebidas consumen ingredientes al venderse. Los panes y postres los consumen al
producirse; su venta descuenta unidades terminadas. Se utiliza primero lo que vence
antes (FEFO), excluyendo lotes vencidos. Un lote sirve durante su día de vencimiento.
La alerta de stock aparece al llegar al 15 % de la referencia o menos.

Los cambios confirmados generan auditoría en la misma transacción. Un error revierte
operación, consumo y bitácora. Los permisos se consultan en PostgreSQL en cada acceso;
las mutaciones requieren CSRF. Cerrar sesión revoca el token. Cambiar contraseña,
rol, sede o estado del usuario también revoca sus sesiones.

En **Reportes**, elegir el mes de la carga. `Desde` incluye ese día y `Hasta` lo
excluye. El mes de inventario filtra vencimientos; las existencias son las actuales.
Los horarios se interpretan en Guatemala. Los reportes muestran top 10 productos,
top 10 clientes frecuentes, top 5 reservas con preferencias, inventario y comparación
de sucursales. Las reservas canceladas no suman en los rankings.

### Acceso demo opcional

Existe una cuenta pública de práctica `admin / 123`, deshabilitada por defecto.
Solo en una base local de demostración, configurar `HABITS_DEMO_LOGIN=1` y ejecutar
`python -m flask --app app create-demo-admin`. No reemplaza cuentas existentes.
Producción bloquea su creación, acceso y sesiones incluso si se activa la bandera.
Para una entrega o instalación normal, usar el administrador creado en el paso 3.

## 6. Pruebas

Con el entorno virtual activo y `TEST_DATABASE_URL` apuntando a la base separada:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

La base de pytest debe terminar en `_test`. Cada caso crea un esquema temporal y lo
elimina al terminar. Se requiere PostgreSQL real; si falta, las pruebas fallan en
lugar de omitirse. Nunca usar una base con datos importantes para las pruebas.

Se cubren HTTP, autenticación, permisos, CSRF, instalación, carga repetible,
restricciones, reportes, concurrencia, FEFO, vencimientos, auditoría y COMMIT/ROLLBACK.
El [guion de demostración](docs/demo.md) permite comprobar los flujos desde el navegador.

## Detener y reanudar PostgreSQL

```bash
pg_ctl -D .local/postgres stop -m fast
pg_ctl -D .local/postgres -l .local/postgres.log -o "-h 127.0.0.1 -p 55432 -k '$PWD/.local/socket'" start
```

## Entrega local

El repositorio contiene la aplicación, el DER y la carga reproducible. Falta la
entrega manual del enlace y documentación en Canvas y la presentación del grupo.
El historial de Andrew, Chris, Brian y Rodrigo se conserva sin reescribir commits;
los aportes se consultan en Git.

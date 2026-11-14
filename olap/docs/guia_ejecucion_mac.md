# Ejecutar la parte de Andrew en macOS

Trabajar desde la raíz de la **copia de la rama** `feature/proyecto3-olap-andrew`.
La entrega no ejecuta Flask, ETL, Power BI ni inserta las 10,000 ventas. Solo los
scripts 01 y 02 instalan objetos; la prueba 04 siempre revierte sus inserciones.

## Requisitos

PostgreSQL 17 o posterior, Python 3.12+, y dependencias de desarrollo del repositorio.
No se añade ninguna dependencia a Proyecto 2.

```bash
brew install postgresql@17
export PATH="$(brew --prefix postgresql@17)/bin:$PATH"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Si ya existe un entorno virtual con esas dependencias, activarlo. Para ejecutar
solo las pruebas no hace falta iniciar un servicio PostgreSQL ni configurar `.env`.

## 1. Pruebas automáticas sin tocar ninguna base existente

```bash
python olap/tests/ejecutar_pruebas.py
# También comprobar Proyecto 2:
python olap/tests/ejecutar_pruebas.py --proyecto2
```

El ejecutor crea un clúster nuevo en `/tmp`, usa un socket dentro de un directorio
privado, rechaza conexiones TCP y crea usuarios/bases exclusivos. Cada prueba OLAP
recibe su propia base, con un dueño sin privilegios de superusuario. La suite
original recibe otra base terminada en `_test`; su SECRET_KEY es temporal.
Al terminar, incluso si hay fallos de pytest, se detiene y elimina el clúster temporal.
No utiliza DATABASE_URL ni copia `.env`; la suite original mantiene su propio
comportamiento de lectura de configuración. No ejecutar el script como root.

El puerto lógico 55439 se usa solo en el socket propio, por lo que no ocupa un
puerto TCP ni interfiere con el servidor habitual. Si se interrumpe el proceso de
forma forzada, el directorio `/tmp/habits_olap_*` permite localizar ese clúster;
no detener otros servidores por su nombre global.

## 2. Preparar una base OLAP de práctica

Para conservar una base consultable después de las pruebas, iniciar el PostgreSQL
local que se vaya a usar. Si aún no existe un servidor local:

```bash
brew services start postgresql@17
```

Usar una cuenta administradora propia para crear **una base nueva**, nunca la base
de operaciones de Proyecto 2. Estos comandos preguntan la contraseña sin guardarla
en archivos. Sustituir host, puerto y usuario administrador según la instalación:

```bash
createuser -h 127.0.0.1 -p 5432 -U "$USER" --pwprompt habits_olap_owner
createdb -h 127.0.0.1 -p 5432 -U "$USER" -O habits_olap_owner habits_olap
export PGHOST=127.0.0.1
export PGPORT=5432
export PGDATABASE=habits_olap
export PGUSER=habits_olap_owner
```

El dueño no necesita ser superusuario. Utilizar la contraseña solicitada por psql
o el gestor de credenciales local. No incluir contraseñas en comandos, Git o `.env`
nuevos. Confirmar el destino antes de instalar:

```bash
psql -X -c 'SELECT current_database(), current_user;'
psql -X -v ON_ERROR_STOP=1 -f olap/sql/01_modelo_estrella.sql
psql -X -v ON_ERROR_STOP=1 -f olap/sql/02_datamart.sql
psql -X -v ON_ERROR_STOP=1 -f olap/sql/04_prueba_humo.sql
psql -X -c 'SELECT count(*) AS ventas FROM olap.fact_ventas;'
```

El último resultado debe ser **0** antes del ETL. Humo debe mostrar un NOTICE de
éxito y terminar con ROLLBACK. Ejecutarlo sin escritores concurrentes. No envolver
01, 02 o 04 en `--single-transaction`: ya tienen sus propias transacciones.
Si `olap` o `dm` ya existe, el instalador falla sin modificar el esquema existente;
inspeccionar su estado, no borrarlo ni volverlo a instalar encima.

## 3. Después del ETL de Rodrigo

```bash
psql -X -v ON_ERROR_STOP=1 --single-transaction -f olap/sql/03_validaciones.sql
```

Exige 10,000 tickets distintos, las dos sucursales y doce productos originales,
coherencia de cabeceras y reconciliación de vistas. Antes del ETL **debe fallar**
por falta de tickets; eso no es un error de instalación. No cambiar el número
esperado para aprobar la entrega. Las pruebas unitarias usan un total pequeño
mediante una configuración de sesión que no altera el valor predeterminado.

El 03 no abre/cierra transacciones: Rodrigo lo ejecuta dentro de su transacción
antes de confirmar. Fuera del ETL, `--single-transaction` garantiza una ejecución
atómica. No ejecutar 04 dentro del ETL, porque termina con ROLLBACK.

## 4. Acceso de lectura para Brian

Cuando haga falta, el administrador crea la cuenta y el dueño concede solo lectura.
No es un requisito para las pruebas ni se ejecuta automáticamente.

```bash
createuser -h 127.0.0.1 -p 5432 -U "$USER" --pwprompt habits_powerbi
psql -X -v ON_ERROR_STOP=1 \
  -c 'GRANT CONNECT ON DATABASE habits_olap TO habits_powerbi;' \
  -c 'GRANT USAGE ON SCHEMA dm TO habits_powerbi;' \
  -c 'GRANT SELECT ON dm.v_ventas_detalle, dm.v_ventas_mensuales, dm.v_productos, dm.v_sucursales TO habits_powerbi;'
```

Brian utiliza esa cuenta y las vistas en Power BI; Rodrigo usa el dueño de esta
base académica para cargar. Estos permisos no cambian roles ni tablas de Proyecto 2.
Las restricciones de conexión/TLS de un futuro servidor remoto las configura el
equipo al alojarlo; esta guía describe una instalación local.

## 5. Diagrama editable

Abrir `olap/docs/modelo_estrella.mmd` en un editor compatible con Mermaid. El PDF
ya está incluido. Para regenerar el mismo PDF, con ReportLab instalado en el entorno:

```bash
python -m pip install reportlab
python olap/docs/generar_diagrama.py
```

El generador no forma parte del runtime de Flask. Si se modifica el esquema,
actualizar tanto el Mermaid como las filas del generador y regenerar el PDF.

# Entorno Windows de Brian

Se eligió una base **local nueva y dedicada** porque no hay servidor remoto
documentado. Se instaló PostgreSQL portátil de EDB 17.12 en
`.local/tools/postgresql/pgsql`; no instala servicio, pgAdmin ni StackBuilder.
Descarga enlazada desde el [sitio oficial de PostgreSQL](https://www.postgresql.org/download/windows/).
Todo lo privado y los binarios quedan en `.local/`, excluido de Git.

| Elemento | Valor de esta computadora |
|---|---|
| Servidor Power BI | `127.0.0.1:55440` |
| Base nueva | `habits_olap` |
| Lector Power BI | `habits_powerbi` |
| Dueño para ETL | `habits_olap_owner` |
| Administrador del clúster nuevo | `habits_olap_admin` |
| Datos físicos | `.local/olap/postgres` |
| Autenticación | SCRAM-SHA-256, escucha solo en 127.0.0.1 |

Se revisaron SQL 01/02 antes de ejecutarlos: crean esquemas nuevos y fallan si ya
existen; no reemplazan objetos. Ya se ejecutaron en esta base. **No repetirlos**
para actualizar datos. No se modificó ninguna tabla operativa ni se instaló Flask.
En otra computadora estos binarios y credenciales no viajan con Git: instalar
PostgreSQL 17+ y crear una base dedicada según la guía de Andrew, adaptando host,
puerto y usuarios. No copiar el directorio de datos entre equipos/versiones.

## Encender y apagar (desde la raíz del repositorio)

```powershell
$pg = '.\.local\tools\postgresql\pgsql\bin'
& "$pg\pg_ctl.exe" -D '.local/olap/postgres' status
# Solo si indica que está detenido:
& "$pg\pg_ctl.exe" -D '.local/olap/postgres' -l '.local/olap/postgres.log' -w start
# Al terminar de actualizar y de usar psql:
& "$pg\pg_ctl.exe" -D '.local/olap/postgres' -w stop -m fast
```

No es necesario encender la aplicación de Proyecto 2. El servidor de esta base
escucha en otro puerto. No detener otros procesos PostgreSQL de manera global.

## Contraseña del lector sin escribirla en código

Las contraseñas aleatorias se guardaron en archivos **cifrados con DPAPI de Windows**
en `.local/olap/*.credential.xml`. Solo la misma cuenta Windows puede descifrarlas;
no sirven en otra computadora y no se versionan. Para introducir la del lector
en el diálogo de Power BI, copiarla desde una terminal PowerShell normal de Brian:

```powershell
$lector = Import-Clixml '.local/olap/habits_powerbi.credential.xml'
Set-Clipboard -Value $lector.GetNetworkCredential().Password
```

Pegar en Power BI con Ctrl+V y limpiar luego el portapapeles:

```powershell
Set-Clipboard -Value ''
Remove-Variable lector
```

No mostrar el resultado de `GetNetworkCredential()` ni incluir contraseñas en
capturas, mensajes o el PR. No conceder escritura al lector: solo CONNECT a la
base, USAGE en `dm` y SELECT en las cuatro vistas. Se comprobó que puede leer
detalle y no tiene USAGE en `olap`.

## Ejecutar consultas sin guardar contraseñas en SQL

```powershell
$pg = '.\.local\tools\postgresql\pgsql\bin'
$credencial = Import-Clixml '.local/olap/habits_powerbi.credential.xml'
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '55440'
$env:PGDATABASE = 'habits_olap'
$env:PGUSER = $credencial.UserName
$env:PGPASSWORD = $credencial.GetNetworkCredential().Password
$env:PGCLIENTENCODING = 'UTF8'
try {
    & "$pg\psql.exe" -X -w -v ON_ERROR_STOP=1 -f olap/powerbi/validar_dashboard.sql
    if ($LASTEXITCODE -ne 0) { throw 'Falló la comparación SQL' }
} finally {
    Remove-Item Env:PGPASSWORD
    Remove-Variable credencial
}
```

El ETL requiere al dueño, no al lector. Rodrigo puede usar la credencial local
`habits_olap_owner.credential.xml` mediante el mismo patrón, sin publicar secretos.
Para aprobar su carga ejecutar con el dueño `03_validaciones.sql` en transacción,
sin cambiar la expectativa de 10000. No ejecutar scripts de creación de Proyecto 2.

## Power BI Desktop

Se descargó `PBIDesktopSetup_x64.exe` del [centro oficial de Microsoft](https://www.microsoft.com/en-us/download/details.aspx?id=58494).
Se comprobó su firma válida de Microsoft Corporation antes de instalar.
El instalador queda en `.local/tools/`. El resultado de instalación y las
verificaciones de Desktop se registran en VALIDACION.md.
No hace falta una cuenta Power BI para trabajar localmente ni publicar el informe.

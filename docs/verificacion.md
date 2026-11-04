# Verificación de entrega

Revisión local del 3 de noviembre de 2026 sobre `main` actualizado (`80d3b6f`).
Se consultó la consigna original de CC3088, «Proyecto 02 - BD Operativas», páginas
1–3. No se ejecutó un despliegue remoto.

## Instalación y pruebas

Instalación nueva en un entorno virtual con `requirements-dev.txt`, Python 3.14.6
y PostgreSQL 17. Clúster separado en loopback, usuarios de aplicación y pruebas sin
superusuario, bases distintas y credenciales aleatorias no versionadas.
Se ejecutaron `inicializar.sql`, `db-backend-upgrade`, `create-admin` y
`sql/datos_ejemplo/cargar_demo.psql` siguiendo el flujo del README.

La suite inicial ejecutada pasó **215 pruebas**, sin omisiones, con PostgreSQL real.
Ruff, comprobación de formato y mypy pasaron (24 archivos de aplicación).
Después del ensayo con tablas en `public`, una pasada detectó dos fallos del
instalador: 213 pruebas pasaron y dos fallaron. La nueva regresión reprodujo el
problema antes de corregirlo. Las 37 pruebas del esquema pasaron después de la
corrección. La suite completa final pasó **216 pruebas en 71,65 segundos**, sin
omisiones, con el otro esquema todavía poblado. Ruff, formato y mypy también
pasaron después del cambio.
La sintaxis de `operaciones.js` se comprobó con Node; el navegador es adicional a pytest.

## Navegador y persistencia

Se utilizó Chromium real contra Gunicorn local y la base nueva. Las operaciones se
realizaron por formularios; después se consultó PostgreSQL para comprobar sus efectos.

- Login de administrador y registro de gerente y mesero desde Personal.
- Cliente: alta, edición, búsqueda, preferencia, observación, edición de observación
  e historial de reservas, visitas y compras.
- Mesa: alta y cambio de capacidad. Reserva de 90 minutos, rechazo de traslape,
  cancelación que libera horario, nueva reserva y llegada que genera una visita.
- Visita sin reserva para llevar; edición de producto y guardado de receta completa.
- Ingrediente: alta y edición; configuración de inventario y recepción de lotes.
  Quince unidades sobre referencia cien activan la alerta. Un lote vencido de cien
  unidades conserva disponible en quince, sin sumar stock utilizable.
- Producción de dos croissants y venta mixta de bebida y pan con precio del momento.
  Detalle consultado desde la pantalla. Venta sin stock rechazada.
- Cinco reportes con datos del mes, período vacío (200), rango invertido (400),
  menú móvil a 390 px, navegación por módulos permitidos y denegación
  de rutas administrativas para gerente/mesero. Cierre de sesión y acceso rechazado.

En PostgreSQL se comprobaron cliente editado, capacidad guardada, estados de reservas,
visitas, inventario y auditoría INSERT/UPDATE con actor. Ninguna venta quedó sin
líneas ni la auditoría incluyó contraseñas o tokens. Se comparó el consumo total de
ingredientes con las recetas de bebidas vendidas y unidades producidas; los
terminados descontados coincidieron con los vendidos, sin doble consumo.
Los scripts de consultas de presentación y de producción/venta con ROLLBACK se
ejecutaron como propietario: las cuatro comprobaciones de restauración dieron true.
Los escenarios de FEFO,
precios históricos, operaciones concurrentes y rollback completo se verifican además
en pytest; no se atribuyen a una comprobación manual que no se haya realizado.

## Cobertura de la consigna

| Requisito | Evidencia |
|---|---|
| PostgreSQL e integridad relacional | Instalación limpia, PK/FK/UNIQUE/CHECK, exclusión de reservas y pruebas de concurrencia |
| Sign in, login y tres roles | Alta de personal, sesiones revocables, permisos por rol/sucursal y CSRF |
| Reservas y disponibilidad | Formularios, agenda por fecha, duración de 90 minutos, capacidad, rechazo de cruces y cancelación |
| Inventario de ingredientes, mínimos y caducidad | Lotes independientes por sede, alerta ≤15 %, vencimientos, FEFO y descuentos atómicos |
| Historial de clientes | Reservas, visitas reales, preferencias, observaciones y compras sin duplicar visitas |
| Bitácora INSERT/UPDATE/DELETE | Triggers automáticos; los tests verifican las tres operaciones y que ROLLBACK también revierte auditoría |
| Vistas, CTE, índices y triggers | SQL instalado y ejemplos en `sql/fase2/consultas_presentacion.sql` |
| Cinco reportes para administrador | Funciones SQL y página `/reportes`, con datos de ejemplo de ambas sucursales |
| Modelo y DER | Las 18 entidades y los atributos dibujados contrastados con `information_schema`; FK compuestas documentadas |
| Carga aislada reproducible | README y `cargar_demo.psql`; pruebas de repetición y error sin cambios parciales |
| Presentación | Recorrido en `docs/demo.md`, con casos válidos y errores esperados |

La referencia del 15 % es una cantidad configurada por ingrediente y sucursal.
El reporte mensual muestra stock actual y vencimientos del mes seleccionado, sin
reconstruir saldos históricos. Ambas son decisiones explícitas del modelo.
La suposición de alojamiento central remoto de la consigna queda pendiente de
Railway; esta revisión demuestra la aplicación local y su conexión directa a PostgreSQL.

## Correcciones y limpieza

El instalador consultaba nombres sin esquema y podía tomar tablas ajenas del
`search_path`, dejando incompleta una instalación aislada. Ahora comprueba cada
tabla en `current_schema()`. La regresión instala las 18 tablas junto a otro esquema
ya poblado y verifica que el catálogo de ese esquema se conserva sin cambios.


Las alertas de panes y postres omitían el producto al construir sus columnas.
Se reprodujo en Chromium: la comprobación del nombre del croissant falló antes
del cambio y pasó después de incluir la columna Producto. Ahora los lotes por
vencer se pueden identificar. Se corrigió también el usuario PostgreSQL del
ejemplo de ROLLBACK para que coincida con el propietario documentado de `habits_test`.


Se consolidaron instalación y uso en README, modelo en `DER.md`, contrato en
`api.md`, conceptos SQL en `sql.md` y evidencia en este archivo. Se retiraron planes,
prompts, revisiones antiguas y el DER inicial de dos tablas, que describían módulos
como pendientes cuando ya están integrados. Antes se buscaron sus referencias en
los archivos versionados; eran documentación y se actualizaron.

Se retiraron dos `.gitkeep` de carpetas con archivos y los estilos sin consumidores
`.status-pending` y `.pending-module`. Se corrigieron descripciones de módulos que
seguían indicando trabajo futuro. No se borraron pruebas, restricciones ni scripts
SQL académicos. Las capturas locales anteriores se conservan como referencia visual;
no sustituyen los resultados de esta ejecución.

Los comandos del esquema básico, la consulta antigua de personal y su prueba de
comparación se mantienen por compatibilidad. No se usan como los cinco reportes de
la entrega. Los nombres `sql/fase1` y `sql/fase2` se conservan porque instaladores,
pruebas y scripts los utilizan.

## Pendiente externo

Subir la entrega a Canvas, confirmar grupo/turno y realizar la presentación.
Railway requiere autorización, base remota, configuración, instalación explícita,
administrador, HTTPS, límites de login y backups/restauración. No hay URL pública
ni verificaciones remotas en esta entrega.

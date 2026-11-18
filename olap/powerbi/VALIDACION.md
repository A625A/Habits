# Registro de Brian — 15 de noviembre de 2026

**PBIX guardado y comprobado estructuralmente; entrega final pendiente.** Brian
confirmó manualmente que cerró y reabrió `Habits_Analytics.pbix`, conservando las
tarjetas, filtros y espacios de los gráficos. Se comprobó el archivo real y se
leyeron las tablas, medidas y relación del modelo abierto. No hay una comparación
aprobada SQL–Power BI ni resultados del dataset final. No se inventaron ventas,
capturas o conclusiones de negocio para cubrir esas ausencias.

> **Nota del 17 de noviembre de 2026:** el PostgreSQL portátil del OLAP se cambió
> del puerto 55440 al **5432**, como pide la guía (localhost, 5432). El registro
> del 15 de noviembre se conserva tal como se hizo, con el puerto 55440.

## Dependencias comprobadas

| Capa | Evidencia obtenida en esta computadora | Estado |
|---|---|---|
| Guía académica | Se leyeron las cuatro páginas del PDF oficial | Revisada |
| Remoto/base | `https://github.com/A625A/Habits.git`; `main` en `aaff7d0`, confirmado con `ls-remote` | Verificado |
| Identidad Git | Commits anteriores vinculados por API de GitHub a ChenBrian833; nombre/correo existentes configurados solo localmente. En la continuación, `gh api user --jq .login` devuelve ChenBrian833 | Autoría y sesión activa verificadas |
| Rodrigo | Tras `git fetch origin`, no hay CSV, generador ni ETL en el checkout ni en origin/main; antes de subir Brian, las únicas ramas remotas seguían siendo main y Andrew. Consulta nueva al lector: 0 detalles y 0 tickets | Pendiente |
| Chris | No hay diseño ejecutivo de Proyecto 3, PDF final ni presentación de Proyecto 3 identificados | Diseño provisional |
| SQL de Andrew | Archivos 01/02/03/04 presentes y revisados; contrato de detalle coincide con 02 | Verificado |
| PostgreSQL instalado | Binarios portátiles EDB, `psql --version`: 17.12 | Preparado |
| Objetos instalados | SQL 01/02 ejecutados en base nueva `habits_olap`, puerto 55440; catálogo devuelve 5 tablas OLAP y 4 vistas DM | Instalados realmente |
| Datos persistentes | Consulta directa devuelve 0 hechos; calendario 365 días y dos tipos instalados por 01 | Sin ETL |
| Acceso lector | `habits_powerbi` consulta las vistas; SELECT de detalle=true, USAGE de olap=false | Verificado con psql, no con Power BI |
| Power BI Desktop | Instalador oficial con firma válida de Microsoft; salida 0; registro de Windows y ejecutable versión 2.159.1231.0 | Instalado |
| Fuente editable | PBIP, modelo TMSL y definición PBIR guardados por Desktop; informe JSON coincidente con el contenido del PBIX, fórmulas y consultas sin cambios | Sincronizada con el PBIX |
| Esquemas JSON iniciales | Antes del guardado de Desktop, 21 archivos conformes a esquemas oficiales de Microsoft, mediante jsonschema 4.26.0 | Evidencia de la versión inicial; Desktop migró después sus esquemas |
| Modelo TMSL | Biblioteca `Microsoft.AnalysisServices.Server.Tabular.Json.dll` de Desktop deserializa `model.bim`: 2 tablas | Aprobado para estructura |
| Referencias y distribución | `comprobar_fuentes.ps1`: campos de todos los visuales existentes, relación activa N:1, orden mensual, 4 tarjetas/3 filtros/5 tipos, límites del lienzo e interacciones con destinos existentes | Aprobado para estructura |
| Modelo abierto en Desktop | API local de Analysis Services devuelve las dos tablas y cuatro medidas; Calendario=Ready, detalle=NoData | Apertura de modelo verificada por API; conexión M pendiente |
| DAX en motor de Desktop | `comparar_kpis.dax` ejecutado por ADOMD en la instancia local: cinco escenarios y doce meses con 0/0/0/BLANK | Aprobado solo sin datos; no acredita importación desde PostgreSQL |
| PBIX real | `Habits_Analytics.pbix`, 38,359 bytes, versión interna 1.32, contenedor sin errores CRC; DataModel no vacío y definición PBIR con 1 página, 4 tarjetas, 3 filtros y 5 tipos de gráfico | Comprobación estructural aprobada |
| Cierre y reapertura | Brian confirma guardado desde Desktop y reapertura con tarjetas, filtros y espacios de los gráficos | Comprobación manual del usuario; no observación directa de la interfaz por esta sesión |
| Modelo tras la reapertura | Lectura TOM del motor abierto: Calendario y v_ventas_detalle, las cuatro medidas con sus fórmulas, relación Calendario_Detalle activa; detalle=NoData y calendario=Ready | Modelo conservado; sin actualización final |
| GitHub | Sesión activa ChenBrian833 y permiso push comprobados; rama subida y PR [#3](https://github.com/A625A/Habits/pull/3) creado hacia main | Borrador; sin merge |
| Dump/restauración final | No hay dump final ni prueba de restauración identificados | Pendiente del equipo |

No se modificaron archivos de los demás integrantes ni tablas de Proyecto 2. La
base aislada no tiene tablas operativas en `public`. No se publicó al servicio BI.
La presencia de SQL en Git se distingue de su instalación, y de una carga real.

## Pruebas realmente ejecutadas

1. `04_prueba_humo.sql`, como dueño: aprobado. Aviso: 2 detalles, 1 ticket,
   3 unidades, Q25.00; terminó con ROLLBACK y quedaron 0 hechos.
2. `03_validaciones.sql`, con expectativa predeterminada de 10000 y transacción:
   rechazo esperado, salida psql 3: «Se esperaban 10000 tickets; se encontraron 0».
   No se cambió el número esperado para aparentar una carga final aprobada.
3. `validar_dashboard.sql`, como lector, base vacía: salida 0; cinco escenarios
   devuelven 0 ingresos/tickets/unidades y NULL de promedio; aparecen doce meses.
   Consultas de tickets multíproducto/multicategoría devuelven 0 filas: no se
   consideran aprobadas con datos finales.
4. Mismas consultas con el **fixture existente** de
   `olap/tests/conftest.py::sales`: se reutilizaron sus INSERT sin modificarlos,
   dentro de una transacción temporal en la base previamente vacía. Para esta
   ejecución se omitió en memoria el BEGIN READ ONLY y el COMMIT del archivo de
   comparación y se cerró con ROLLBACK. No se persistió un dataset alternativo.
   Quedaron 0 hechos al terminar. Resultados SQL obtenidos:

| Caso del fixture de Andrew | Ingresos GTQ | Tickets | Unidades | Ticket promedio GTQ |
|---|---:|---:|---:|---:|
| General: 6 detalles, 4 tickets | 78.00 | 4 | 10 | 19.50 |
| Noviembre 2025 | 37.00 | 2 | 4 | 18.50 |
| Diciembre 2025 | 25.00 | 1 | 4 | 25.00 |
| Enero a septiembre 2026, cada mes | 0.00 | 0 | 0 | NULL |
| Octubre 2026 | 16.00 | 1 | 2 | 16.00 |
| Sucursal DEMO-01 | 37.00 | 2 | 4 | 18.50 |
| Categoría bebida | 42.00 | 3 | 4 | 14.00 |
| Noviembre / DEMO-01 / bebida | 32.00 | 2 | 3 | 16.00 |
| 1 de noviembre de 2026, fuera del calendario | 0.00 | 0 | 0 | NULL |
| Ticket 1001 completo, dos productos y dos categorías | 25.00 | 1 | 3 | 25.00 |
| Ticket 1001, bebida | 20.00 | 1 | 2 | 20.00 |
| Ticket 1001, panaderia | 5.00 | 1 | 1 | 5.00 |

Los conteos de categorías del ticket 1001 no se suman: siguen siendo un solo
ticket en el total. El fixture conserva un precio histórico distinto para HAB-01
(Q10/Q12). Por tipo: local Q50 y llevar Q28. El fixture no se cargó en Desktop;
sus cifras no se atribuyen al dashboard.

5. Después de abrir el PBIP con Desktop se consultó su motor local mediante TOM y
   ADOMD, sin escribir en el modelo: están las dos tablas y las cuatro medidas.
   El calendario tiene 365 días. Se ejecutaron los dos EVALUATE de
   `comparar_kpis.dax`: los cinco escenarios devolvieron ingresos=0, tickets=0,
   unidades=0 y promedio=BLANK; el segundo devolvió doce meses ordenados desde
   202511 hasta 202610. Esto verifica DAX y el modelo sin datos; la partición de
   detalle está en NoData. **No prueba la consulta M, las credenciales del conector,
   una actualización, los visuales ni los resultados del dataset final.**

## PBIX guardado y reabierto: evidencia separada de la validación de datos

Brian guardó el archivo desde Power BI Desktop, lo cerró y lo volvió a abrir.
Su confirmación manual indica que se conservan tarjetas, filtros y espacios de
los gráficos. No se atribuye a esta sesión una inspección visual directa.

Comprobaciones adicionales realizadas sobre el archivo:

- Ruta: `olap/powerbi/Habits_Analytics.pbix`; tamaño: **38,359 bytes**.
- SHA-256: `33a48b3adc371893224de5d02734142d9e4da9c69f01f0eff785f1cc34920abd`.
- Contenedor ZIP legible, CRC correcto en todas las entradas; partes Version,
  Content_Types XML válido, Metadata, Settings y DataModel presentes y no vacías.
- Versión interna 1.32 y modelo embebido de 23,522 bytes. Este PBIX guarda el
  informe en `Report/definition/` (PBIR); no necesita la parte antigua Report/Layout.
- Una página «Resumen ejecutivo»; cuatro `card`, tres `slicer`, un `lineChart`,
  `clusteredBarChart`, `donutChart`, `treemap` y `scatterChart`, más dos textos.
- Los JSON del informe embebidos coinciden con las fuentes guardadas por Desktop.
  El modelo fuente conserva las fórmulas y consultas anteriores; el comprobador
  estructural pasa sobre la fuente actualizada.
- Lectura por API local del modelo abierto tras la reapertura: dos tablas, cuatro
  medidas correctas y relación activa. La partición de detalle continúa en NoData;
  esta lectura no acredita la conexión M ni una actualización desde PostgreSQL.

Se incluyen también los metadatos y la normalización que Desktop guardó en la
fuente editable, para mantenerla alineada con el PBIX; no se incluyen cachés `.pbi`
ni credenciales. La integridad del contenedor y la reapertura manual acreditan
el archivo de avance; **no aprueban cifras, actualización ni interacciones con los
10,000 tickets finales**.

## Protocolo para aprobar con los datos finales

Después del ETL de Rodrigo, ejecutar primero SQL 03 como dueño, con el valor
predeterminado 10000, y conservar su salida. Luego ejecutar `validar_dashboard.sql`
como lector siguiendo WINDOWS.md y **Actualizar** en Desktop. Deben usar la misma
versión de los datos, sin otra carga concurrente. Para guardar la salida de psql
puede añadirse `-L .local/olap/comparacion-final.log`; no versionar credenciales.

Ejecutar `comparar_kpis.dax` en Vista de consulta DAX. Los escenarios coinciden con
SQL. El caso sin ventas usa una fecha fuera del calendario mediante TREATAS;
no extender el calendario final para mostrar una fecha inexistente en el filtro.
Para una prueba visual sin ventas, aplicar temporalmente un filtro avanzado de
fecha que deje un conjunto vacío y retirarlo al terminar. Si el dataset tiene un
período vacío dentro del calendario, probarlo también con el segmentador.

Para ticket multíproducto y multicategoría, tomar el ID devuelto por SQL, filtrar
`v_ventas_detalle[ticket_id]` **como texto** en el panel de filtros de Desktop,
comparar el total y luego cada categoría; retirar ese filtro al terminar. Si el
dataset no contiene un ticket multicategoría, registrar «no existe» y conservar
la evidencia SQL, sin inventarlo ni modificar el ETL.

Comparar enteros exactamente y moneda subyacente a dos decimales; para el promedio
comparar el cociente sin redondear y su presentación a dos decimales. Ver el
valor/exportación sin abreviaturas de miles; investigar cualquier diferencia antes
de marcar aprobado. Revisar los doce meses en orden y los totales de cada producto,
categoría y tipo contra las consultas finales de `validar_dashboard.sql`.

| Comprobación final | SQL final obtenido | Power BI obtenido | Diferencia/estado |
|---|---|---|---|
| 10000 tickets distintos, detalles sin duplicar, fechas válidas | 18/11/2026: 10,000 tickets, 19,175 filas en `dm.v_ventas_detalle`; ETL y SQL 03 aprobados | 10,000 ventas | Coincide; aprobado |
| Cuatro KPIs generales | 18/11/2026: Q583,177.42; 10,000 tickets; 23,641 unidades; ticket promedio Q58.32 | Q 583.18 mil; 10,000 ventas; 24 mil (23,641) unidades; Q 58.32 | Coincide al redondeo mostrado; aprobado |
| Cuatro KPIs por cada mes | Pendiente | Pendiente | No aprobado |
| DEMO-01 | 18/11/2026: Habits Sucursal 1: Q331,190.65; 5,668 tickets; 13,444 unidades; Q58.43 | Q 331.19 mil; 5,668 ventas; Q 58.43 | Coincide al redondeo mostrado; aprobado |
| DEMO-02 | 18/11/2026: Habits Sucursal 2: Q251,986.77; 4,332 tickets; 10,197 unidades; Q58.17 | Q 251.99 mil; 4,332 ventas; Q 58.17 | Coincide al redondeo mostrado; aprobado |
| bebida | Pendiente | Pendiente | No aprobado |
| noviembre 2025 / DEMO-01 / bebida | Pendiente | Pendiente | No aprobado |
| Período sin ventas | Pendiente | Pendiente | No aprobado |
| Ticket multíproducto | Pendiente | Pendiente | No aprobado |
| Ticket multicategoría o ausencia demostrada | Pendiente | Pendiente | No aprobado |

18 de noviembre de 2026: con los datos de Rodrigo cargados, se probó en Power BI el
filtro de sucursal y la suma de las 2 sucursales da el total (Q331,190.65 +
Q251,986.77 = Q583,177.42; 5,668 + 4,332 = 10,000 tickets). Consulta SQL hecha con
el usuario lector `habits_powerbi`.

También falta comprobar en Desktop con los datos finales:

- Legibilidad de tarjetas, filtros, etiquetas y gráficos después de actualizar.
- Línea cronológica con doce meses y valores sin ventas consistentes.
- Barras descendentes, nombres legibles y tooltips; dona con ambos tipos.
- Treemap con categoría y producto; dispersión con un punto por producto.
- Seleccionar un punto de dispersión filtra tarjetas y otros gráficos al producto;
  seleccionar categoría filtra ingresos y recalcula tickets distintos. No suma
  promedios ni modifica los segmentadores desde gráficos.
- Selecciones cruzadas, Ctrl/multiselección, borrado y restablecimiento de filtros.
- Calendario marcado y relación 1:N activa con dirección única; IDs de texto.
- Guardar el PBIX actualizado y repetir cierre/reapertura con los datos finales.
- Exportación de tablero para Chris; dump final y restauración comprobada por el
  equipo. La prueba de restauración debe usar otra base nueva y repetir SQL 03.

Solo después de cerrar estas pendientes corresponde retirar el estado de borrador.

## Envío a GitHub completado

En la continuación se verificó la sesión activa **ChenBrian833**, el permiso de
escritura en A625A/Habits y la base predeterminada `main`. Se revisaron los cuatro
commits existentes: `a2908cf`, `aef208b`, `5cff27b` y `5290d32`. Se subió la rama
`feature/brian-powerbi-dashboard` sin reescribir historial y se creó el
[PR #3](https://github.com/A625A/Habits/pull/3) como **borrador**, sin merge.
Los cambios posteriores de este registro se envían a la misma rama y PR.

El impedimento de autenticación del primer intento quedó resuelto. Brian completó
después el [protocolo de guardado](README.md#guardar-y-comprobar-el-pbix-en-desktop)
y confirmó la reapertura manual. El PBIX real se incorpora a esta misma rama y PR,
junto con su evidencia y las fuentes sincronizadas. Continúan pendientes el ETL
de Rodrigo y las pruebas de actualización, cifras e interacciones con el dataset
final; el PR debe permanecer en borrador. No se sustituyó el PBIX con otro formato.

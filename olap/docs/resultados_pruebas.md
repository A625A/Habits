# Verificación de la entrega de Andrew

Fecha local: 2026-11-13. Base: `origin/main` en `84c2466`.
Rama: `feature/proyecto3-olap-andrew`. PostgreSQL 17.11, Python 3.14.6, pytest 9.1.1.
Se usó el entorno virtual ya disponible; no se modificaron dependencias.

| Comprobación ejecutada | Resultado |
|---|---|
| Pruebas OLAP contra PostgreSQL real | **30 aprobadas** |
| Suite completa original, `python -m pytest` | **216 aprobadas** |
| `python -m ruff check --no-cache .` | Sin errores |
| `python -m ruff format --no-cache --check .` | 54 archivos con formato correcto |
| `python -m mypy --cache-dir /tmp/habits-olap-mypy-cache` | Sin errores en 25 archivos de Proyecto 2 |
| Instalación SQL 01 y 02 por `psql -X -v ON_ERROR_STOP=1` | Cinco tablas, cuatro índices y cuatro vistas creados |
| SQL 04 por psql, dos ejecuciones seguidas | Ambas correctas; ROLLBACK; **0 hechos restantes** |
| SQL 03 sobre la base sin ETL | Rechazo esperado: 10000 tickets esperados, 0 encontrados; salida psql 3 |
| SQL 03 sobre fixture con expectativa explícita de 4 tickets | Aprobado; valor predeterminado 10000 también rechaza ese fixture |
| PDF | Una página A4 horizontal, texto extraíble, cinco tablas; renderizado e inspeccionado visualmente |

La primera prueba falló por ausencia del SQL, antes de implementarlo. Los casos
OLAP cubren creación independiente, calendario y límites, FK, IDs/cantidad/precios
inválidos, NaN, nulos, duplicados de detalle/ticket-producto, precio histórico,
importe generado, joins sin multiplicación, filtros, ingresos y conteos por vista,
productos sin ventas, protección de dimensiones referenciadas, reinstalación
segura, coherencia de tickets y ROLLBACK de ETL fallido y de humo repetible.

Fixture: cuatro tickets, seis detalles, diez unidades, **Q78.00**, ticket promedio
**Q19.50**. Sus tickets totalizan Q25, Q12, Q25 y Q16. Son datos exclusivos de las
bases temporales; no representan la historia que generará Rodrigo.

Se ejecutó el entregable `python olap/tests/ejecutar_pruebas.py --proyecto2` desde
el worktree. Creó su propio clúster sin TCP y lo detuvo/eliminó al terminar. Los
casos OLAP usan bases independientes con dueño sin privilegios de superusuario;
Proyecto 2 usa otra base `_test`. No se consultó ni escribió ninguna base principal.

En el primer intento aislado de la suite original pasaron 214 casos y fallaron
`test_flask_responde_sin_necesitar_postgresql` y
`test_base_no_disponible_devuelve_503_sin_filtrar_credenciales`: faltaba SECRET_KEY
porque el worktree no copia `.env`. Se configuró una clave aleatoria temporal en
el ejecutor, sin modificar la aplicación; la repetición completa pasó 216/216.

## Límites de lo comprobado

No se generaron los 10,000 tickets, CSV históricos ni el ETL; tampoco un PBIX,
dashboard o presentación. La aprobación de la carga final con 10000 tickets queda
pendiente de Rodrigo; sí se comprobó que la validación detecta su ausencia.
No se probó la conexión desde Power BI. ReportLab solo se necesita para regenerar
el PDF, ya incluido; no es una dependencia de Flask.

Todos los archivos nuevos de esta entrega están en `olap/`. No se modificaron
archivos versionados de Proyecto 2. No se hicieron commits, push, merge ni despliegues.
El checkout original conserva sus modificaciones anteriores. Para repetir los
comandos de instalación y pruebas, consultar `guia_ejecucion_mac.md`.

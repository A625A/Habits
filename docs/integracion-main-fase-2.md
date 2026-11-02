# Integración de Fase 2 y contribución de Chris en main

## Solicitud y alcance autorizado — 1 de noviembre de 2026

Andrew autorizó expresamente integrar a `main` el backend terminado y el historial
original de `feat/chris-reservas`, y hacer push a `origin/main` después de verificar.
Pidió preservar los commits, las 18 tablas, procedimientos, triggers, cinco reportes,
autenticación y backend; excluir SQL antiguo/duplicado y plantillas de Chris.
No autoriza force push, reescritura de historia, Railway, UI ni comenzar Fase 3.
Este registro describe la integración local y las verificaciones previas al push.

## Estado inicial verificado

Tras `git fetch origin`, árbol limpio y `main`/`origin/main` en
`aa229aa59353f476afaed74dd2b80d87796406f0` (Fase 1). Fase 2 en
`feat/fase-2-backend`, con commits originales:

- `64633ea9a40dc5d2cb7e1f0a4505ec3899afafa6`: backend funcional y pruebas.
- `a95f2d4`: documentación SQL avanzado y evidencia de verificación.

`origin/feat/chris-reservas` apuntaba a
`f27bb8e849b2c9293cf6c146cbc836bc5ba905dd`. Su rama local estaba tres commits
atrasada; se integró la referencia remota actualizada, sin reescribir ninguna rama.

## Merges y autoría

1. Merge normal `--no-ff` de `feat/fase-2-backend` a `main`, commit
   `8937759153dba52e4acc57df66ffbd0f8e4ef932`. Conserva `aa229aa`, `64633ea` y
   `a95f2d4` en su ascendencia.
2. Merge normal `--no-ff --no-commit` de `origin/feat/chris-reservas`, con resolución
   selectiva de los dos conflictos de rutas y exclusión de cinco adiciones.
   Commit resultante: `c775f35a8ac1c8dae79bcc87a27c61333db46815`.
   No se usó squash, cherry-pick, rebase ni estrategia global `ours`.

Los tres commits de Chris conservan sus SHA, autor/committer `chris`, fechas y mensajes:

| Commit original | Mensaje original |
|---|---|
| `80032d64030fa26799b2909627de5136874008f7` | esquema de clientes, reservas con exclusion y reportes 2 y 3 |
| `da107e016cf7b7c64f42749aec7963f5e5b3dc59` | Implementacion de rutas backend para clientes, historial y reservas |
| `f27bb8e849b2c9293cf6c146cbc836bc5ba905dd` | Se agragaron las plantillas de clientes, historial y reservas en HTML. |

El merge de Chris tiene como segundo padre `f27bb8e`. Conserva sus commits originales
en el historial de `main`; no atribuye a Chris la posterior implementación completa
de Fase 2. El reconocimiento distingue su aporte original de la adaptación ya
realizada en `64633ea`.

## Resolución por archivo

| Archivo de Chris | Resolución y motivo |
|---|---|
| `app/routes/clientes.py` | Se conserva íntegra la versión Fase 2. Ya adapta búsqueda ILIKE, alta parametrizada e historial con reservas/preferencias/observaciones. Añade JSON, autenticación, CSRF, permisos, visitas/compras y desactivación |
| `app/routes/reservas.py` | Se conserva íntegra la versión Fase 2. Ya adapta listado/filtros, creación confirmada y cancelación; usa 90 minutos fijos, restricciones definitivas y procedimientos de cancelación/llegada |
| `sql/02_clientes_reservas.sql` | Excluido. El diseño definitivo usa BIGINT IDENTITY, TIMESTAMPTZ, desactivación, FK compuestas, duración fija y visitas reales; reinstalar el SQL anterior no es una migración válida |
| `sql/reportes_clientes.sql` | Excluido. Los cinco reportes de Fase 1 son la implementación vigente; reservas confirmadas no deben contarse como visitas reales |
| `app/templates/clientes.html` | Excluida del árbol vigente; preservada en el commit original como referencia para Fase 5 |
| `app/templates/cliente_historial.html` | Igual: UI pendiente, sin activar endpoints HTML antiguos |
| `app/templates/reservas.html` | Igual: UI pendiente; el formulario anterior enviaba una duración libre y no corresponde al contrato JSON/CSRF actual |

La resolución es deliberadamente idéntica al backend de `a95f2d4`: las aportaciones
compatibles ya estaban adaptadas. Solo cambia documentación y ascendencia de Git.
Los archivos SQL/HTML originales siguen consultables en los commits de Chris,
pero no están en el árbol actual, instaladores ni ejecución de la aplicación.

## Verificaciones de la integración

Punto fijo de revisión: `a95f2d4` (última Fase 2 verificada).
Comando del diff: `git diff a95f2d4...HEAD`; commits: `git log a95f2d4..HEAD --oneline`.
Además se verifica ascendencia desde `aa229aa` y los tres commits de Chris.

- Comparación de `app/`, `sql/`, `tests/`, dependencias, configuración y WSGI contra
  `a95f2d4`: sin diferencias; no se eliminó ni alteró ninguna prueba.
- No se añaden pruebas: no hay comportamiento nuevo que requiera regresión.
  La cobertura existente prueba las interfaces HTTP/CLI y SQL público, con
  PostgreSQL real en esquemas temporales de una base `_test`.
- Suite completa: **156 passed in 55.60s**, ninguna prueba omitida. Incluye clientes,
  reservas/visitas, inventario, producción/ventas, permisos/CSRF, transacciones,
  triggers, FEFO, rollback y concurrencia, además de HTTP real en loopback.
- Ruff: **All checks passed!**; formato: **63 files already formatted**;
  mypy: **Success: no issues found in 24 source files**; diff sin errores.
- La suite se ejecutó después de resolver el merge, antes de confirmarlo. Los
  cambios posteriores al pase de pruebas solo son documentación.
- Revisión independiente de estándares y especificación: **0 hallazgos** en cada eje.

### Standards

Sin hallazgos. El diff modifica únicamente README y dos documentos; aplicación,
SQL, pruebas, configuración y dependencias permanecen idénticos. Los padres de
ambos merges coinciden con la integración documentada y los commits originales
de Chris conservan sus metadatos. Los dos SQL y tres HTML excluidos están ausentes
del árbol vigente y presentes en su rama original. La documentación respeta el
vocabulario de CONTEXT, la separación entre reservas, visitas y ventas del ADR,
y los límites de alcance y autorización. Árbol limpio y diff sin errores.
No hay problemas accionables de diseño: el diff no introduce lógica ni abstracciones.

### Spec

Sin hallazgos: no faltan requisitos ni hay ampliación de alcance en el diff.
Ambos merges tienen dos padres; Fase 1, Fase 2 y los tres commits de Chris son
ancestros de HEAD. Las exclusiones solicitadas y la identidad del código funcional
con Fase 2 están verificadas. README e informe reconocen la adaptación de clientes
y reservas y distinguen lo terminado de UI, interfaces de reportes, documentación
final, despliegue y datos operativos pendientes.

Ambas revisiones fueron independientes y de solo lectura; no repitieron pruebas.
El registro de sus resultados y la publicación autorizada son pasos posteriores
a la revisión, sin cambios funcionales.

## Resumen para compartir con el grupo

**Terminado:** base PostgreSQL de 18 tablas, relaciones y restricciones; funciones,
procedimientos, triggers de auditoría/integridad, cinco reportes SQL y catálogo de
12 productos con precios iniciales. Autenticación con sesiones, roles y CSRF.
Backend HTTP/JSON de clientes, preferencias/observaciones, reservas y visitas,
catálogo/recetas, recepciones/alertas, producción y ventas con FEFO y rollback.
Documentación de endpoints, instalación, pruebas y SQL avanzado con ejemplos.

**Aporte de Chris aprovechado:** gestión/búsqueda e historial de clientes,
preferencias/observaciones, consulta/filtros de reservas, creación y cancelación;
su propuesta original de clientes/mesas/reservas y exclusión también sirvió de base
para el diseño definitivo. Sus commits y plantillas quedan reconocidos en el
historial; reconocer la autoría no significa activar el código antiguo.

**Pendiente para entregar el sistema completo:** desarrollar y conectar la UI de
Fase 5 (navegación, formularios, dashboard y estilos), exponer/integrar los cinco
reportes en las interfaces definitivas, validar los flujos completos de usuario,
completar manual de usuario/evidencia final y preparar/validar el despliegue Railway.
El endpoint histórico `/reportes/sucursales` conserva su comparación del core; no
presentarlo como integración de los cinco reportes operativos. La integración
Git/backend de esta entrega queda separada de esa integración futura de UI/reportes.
No se inicia ninguna de esas etapas en este trabajo.

**Datos pendientes:** mesas reales por sede, personal con roles y sucursal,
ingredientes/unidades, recetas con cantidades verificadas, referencias de stock,
recepciones y vencimientos reales, producción y existencias disponibles. Clientes,
visitas, reservas y ventas se registran al operar. No se inventan saldos ni recetas.

La publicación de código en GitHub no instala la migración ni carga datos en una
base de operación. El operador debe aplicar la instalación de Fase 1 y después
`flask --app app db-backend-upgrade` según la [guía](fase-2-backend.md).

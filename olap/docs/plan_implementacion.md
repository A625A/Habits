# Plan de implementación de Andrew

Objetivo: construir la estrella y el DataMart de Proyecto 3 sin modificar Proyecto 2.
Base revisada: `origin/main`, commit `84c2466`. El checkout original tiene cambios
previos; el trabajo nuevo se mantiene en un worktree de la rama solicitada.

## Decisiones

- Cinco tablas en `olap`, sin FK ni escrituras hacia las tablas operativas.
- Grano: un producto por ticket; IDs positivos proporcionados por el futuro ETL.
- Calendario 2025-11-01 a 2026-10-31 y tipos `local`/`llevar` precargados.
- Catálogo original y sucursales se cargarán mediante CSV, sin presumir IDs de OLTP.
- Importe generado a partir del precio histórico. No se copia un total de cabecera.
- Cuatro vistas normales; los tickets se cuentan con `COUNT(DISTINCT ticket_id)`.
- Coherencia de fecha/sucursal/tipo por ticket verificada antes de confirmar el ETL.
- Instalación única y transaccional: si el esquema ya existe, falla sin reemplazarlo.

## Trabajo y comprobaciones

- [x] Escribir y ejecutar pruebas que fallen al faltar el modelo.
- [x] Crear `01_modelo_estrella.sql` y `02_datamart.sql`; comprobar FK, importes,
  duplicados, fechas límite, ventas multíproducto y catálogos sin ventas.
- [x] Crear `03_validaciones.sql` y `04_prueba_humo.sql`; comprobar rechazo de
  tickets incoherentes, conteos incorrectos y repetición de carga; humo con ROLLBACK.
- [x] Documentar CSV, carga atómica, reconciliación y uso de vistas en Power BI.
- [x] Generar Mermaid y PDF; renderizar e inspeccionar legibilidad.
- [x] Ejecutar suite OLAP, suite original de Proyecto 2 y verificaciones estáticas.
- [x] Verificar que solo `olap/` es nuevo y que no hay commits ni push.

Riesgos a cubrir: IDs de tickets globales entre sedes; cabeceras sin detalles;
precios históricos distintos; categorías compartidas por un ticket; meses sin
ventas; recarga accidental; filtros que invalidan sumas de tickets agregados.

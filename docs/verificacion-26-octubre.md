# Verificación de Andrew — 26 de octubre de 2026

Base revisable: `5bb3939244e53aaf6cb0e1f01b6849c9176f2ed2`.
Rama: `feat/andrew-core-deploy`. Cambios locales, sin push/merge/despliegue.

## Resultados

- `python -m pytest`: **49 pruebas aprobadas**, PostgreSQL 17.11 real, 12,40 segundos.
- `python -m mypy`: sin errores, 18 archivos de aplicación.
- `ruff check .` y `ruff format --check .`: correctos.
- Actualización local de Fase 1: dos sucursales idénticas antes/después, cero usuarios.
- Gunicorn con `wsgi:app`, HTTP real: salud DB, login, registro de personal,
  consulta de sesión, comparación y logout aprobados en schema temporal exclusivo.
  Al terminar se detuvo el servidor y se eliminó el schema; no quedaron cuentas demo.

## Comportamientos comprobados

Alta inicial CLI con contraseña oculta y hash scrypt; rechazo si ya existe admin;
login válido/inválido; registro restringido para los tres roles; CSRF incluyendo
entradas Unicode malformadas; errores de BD sin detalles internos; flags de cookie
HTTPS; logout que invalida una cookie copiada; expiración; revocación por cambios
de contraseña, rol, estado o sucursal; aislamiento del reporte para gerente.

Triggers SQL: INSERT/UPDATE/DELETE, snapshots permitidos sin credenciales ni PII
de usuarios, actor opcional, conservación tras borrar actor, atomicidad y rollback,
función reutilizable con otra tabla de prueba. Actualización repetible y rollback
de la actualización completa si una parte falla.

Reporte actual: valores derivados de usuarios reales de cada schema, sede vacía
incluida y valores NULL para módulos no integrados. Consulta futura probada contra
relaciones temporales del contrato: dos ventas de 10/20 y tres reservas suman 30,
no 90; límite superior temporal exclusivo. No es validación de los módulos reales.

Se conservaron las 20 pruebas de Fase 1. No se reemplazó PostgreSQL por SQLite.
Cada nuevo comportamiento se introdujo con un caso rojo antes de implementarlo;
las regresiones adicionales se probaron contra los mismos límites acordados.

## Diagnóstico y corrección

Caso: `test_csrf_malformado_unicode_se_rechaza_sin_error_interno` reproducía
`TypeError: comparing strings with non-ASCII characters is not supported`.
Se aisló la comparación de `secrets.compare_digest`: str con acento falla; bytes
UTF-8 devuelven false. Se comparan bytes y el flujo HTTP ahora responde 400.
Se verificó además logout con CSRF válido. No se añadió instrumentación permanente.

## Pendientes y límites

- Andrew debe ingresar sus datos y contraseña con `flask --app app create-admin`;
  no se inventaron credenciales ni se cargó personal en desarrollo.
- Auditoría de reservas/inventario pendiente de tablas y columnas del equipo.
- Comparación académica de ventas/reservas pendiente de vistas reales validadas
  por Rodrigo/Chris. Consulta preparada; no se presentan ceros como evidencia.
- UI compartida, módulos ajenos y Railway corresponden al equipo. WSGI local
  verificado; HTTPS/proxy, límites de login y operación de producción pendientes.
- No existe protección de bitácora contra el propietario de la base.

Implementación local de Andrew solicitada para el 26: completa, con las dependencias
de integración y el alta operativa del primer administrador claramente pendientes.

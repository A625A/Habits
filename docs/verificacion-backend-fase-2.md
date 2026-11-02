# Verificación de Fase 2 — 1 de noviembre de 2026

Base: `aa229aa59353f476afaed74dd2b80d87796406f0`, verificada igual a `origin/main`
después de `git fetch origin`. Trabajo en `feat/fase-2-backend`, sin push, merge ni
Railway. Referencia Chris: `f27bb8e849b2c9293cf6c146cbc836bc5ba905dd`.

## Resultados ejecutados

- Línea base antes de implementar: **91 passed in 30.52s**.
- Nuevas pruebas HTTP: **65 passed in 29.24s**.
- Suite completa: **156 passed in 64.01s**; ninguna prueba omitida.
- `ruff check .`: **All checks passed!**.
- `ruff format --check .`: **60 files already formatted**.
- `mypy`: **Success: no issues found in 24 source files**.
- `git diff --check`: sin errores.

Comandos reproducibles, con `TEST_DATABASE_URL` apuntando a una base exclusiva
terminada en `_test` y el rol `habits_operaciones` preparado según Fase 1:

```bash
.venv/bin/pytest tests/test_backend_http.py -q
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
```

El sandbox inicialmente impidió conectar a localhost; se ejecutaron las pruebas
con el permiso necesario. No fue un fallo de la implementación ni se sustituyó
PostgreSQL por mocks. Cada prueba crea un esquema único y lo elimina al terminar;
no se instalaron cambios ni cargaron datos en la base de desarrollo.

## Evidencia de comportamiento

Ciclos TDD registrados: rutas ausentes devolvían 404 antes de implementar clientes,
preferencias, reservas, recetas, inventario y ventas; el comando de migración no
existía antes de implementarlo. Se reprodujeron respuestas HTML para errores de
ruteo y un ValueError con filtros numéricos excesivos; ambos se corrigieron con
sus regresiones. Los ciclos se ejecutaron por funcionalidad antes de la suite final.

Cobertura adicional sobre las 91 pruebas SQL/HTTP/CLI previas:

- Alta/búsqueda/actualización/desactivación e historial de clientes; preferencias,
  observaciones, conservación de historia y rechazo de nuevas atenciones inactivas.
- Reserva válida, cancelación, conflicto, intervalo adyacente, capacidad, sucursal,
  llegada única y visita sin reserva; confirmar no genera visitas.
- Doce productos/precios conservados; edición de precio; ingredientes; sustitución
  atómica de receta y preservación de la anterior ante una referencia inválida.
- Recepciones, producción, consumo FEFO, uso durante el día de vencimiento,
  exclusión de lotes vencidos, alertas y rollback por falta de existencias.
- Ventas mixtas, anónimas e identificadas; precio histórico; agrupación de líneas;
  FEFO de terminados; una visita con varias compras; fallo de segunda línea sin
  venta, consumo ni evento de auditoría parcial.
- Carreras HTTP de dos reservas y de dos ventas con clientes/conexiones independientes:
  una devuelve 201 y otra 409; el estado final no tiene duplicados ni sobreventa.
- Roles gerente/mesero, acceso por ID y filtros de otra sede, CSRF en métodos de
  escritura, sesiones revocadas, JSON inválido, cantidades/precios no representables,
  prohibición de precio manual y comprobación del rol SQL sin DML de saldos.
- Migración de permisos repetible. Auditoría atribuida al actor autenticado.
- Servidor WSGI real temporal en `127.0.0.1` con puerto efímero: login por HTTP,
  cookie, rotación CSRF, alta JSON y consulta del cliente. Se detuvo al finalizar.

## Revisión independiente

Pendiente de incorporar los resultados de estándares y especificación sobre el
commit de implementación. Esta sección se actualizará antes del cierre.

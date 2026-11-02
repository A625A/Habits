# Verificación de Fase 2 — 1 de noviembre de 2026

Base: `aa229aa59353f476afaed74dd2b80d87796406f0`, verificada igual a `origin/main`
después de `git fetch origin`. Trabajo en `feat/fase-2-backend`, sin push, merge ni
Railway. Referencia Chris: `f27bb8e849b2c9293cf6c146cbc836bc5ba905dd`.

## Resultados ejecutados

- Línea base antes de implementar: **91 passed in 30.52s**.
- Nuevas pruebas HTTP: **65 passed in 29.24s**.
- Suite completa: **156 passed in 64.01s**; ninguna prueba omitida.
- `ruff check .`: **All checks passed!**.
- `ruff format --check .`: **62 files already formatted**.
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

## Ejemplos de SQL avanzado ejecutados

Se ejecutaron con `psql -X -v ON_ERROR_STOP=1` en otro esquema efímero de la base
`_test`, con usuario, receta y lote sintéticos exclusivamente dentro de ese esquema:

- `sql/fase2/consultas_presentacion.sql`: OK; índices/EXPLAIN ANALYZE, vistas,
  CTE, función de reporte, triggers y auditoría; transacción de solo lectura.
- `sql/fase2/ensayo_venta.psql`: OK; CALL mostró la venta dentro de la transacción,
  forzó restricciones diferidas y la revirtió. Se verificó con consultas nuevas:
  cero ventas, mismo saldo de ingredientes y misma cantidad de eventos de auditoría.

El esquema se eliminó al terminar. La corrección posterior a la suite completa
solo añadió documentación y estos scripts; no cambió la aplicación ni las pruebas.
Se volvieron a verificar Ruff, formato, mypy y diff después de esa corrección.

## Standards

Revisión independiente de lectura de `aa229aa...64633ea`, considerando la
autorización vigente de Fase 2 y su matriz de permisos: **sin incumplimientos
accionables de estándares**.

- `app/api.py`: autentica antes de operar; transacción explícita, rol limitado,
  actor desde `g.user` y confirmación antes de responder, conforme a AGENTS.md y
  el contrato de transacciones/auditoría.
- `app/services/operaciones.py`: valores parametrizados e identificadores compuestos
  con `sql.Identifier`; nombres procedentes del código y campos permitidos.
- `sql/fase2/10_backend.sql`: recepción mediante procedimiento, operador validado,
  bloqueo de maestros, SECURITY DEFINER con search_path fijo y revocación a PUBLIC;
  no concede DML directo sobre saldos.
- `app/routes/catalogo.py`: edición de recetas solo por administrador, atómica y
  bajo bloqueo del producto.
- `app/routes/clientes.py`: historial por sede y compras mediante visitas,
  consistente con el glosario y ADR.

Juicios de diseño: no se identificó un smell de Fowler que justificara un cambio
con beneficio demostrable. Los auxiliares son pequeños y tienen usos reales.
El revisor no ejecutó pruebas ni modificó archivos.

## Spec

La revisión de lectura inicial detectó **un hallazgo P2 documental**: faltaban
EXPLAIN ANALYZE y ejemplos ejecutables de los cinco temas de SQL avanzado del
apartado 7 de la solicitud. Se resolvió con `docs/sql-aplicado-fase-2.md`, los dos
scripts verificados y el enlace en el contrato de endpoints.

El revisor volvió a inspeccionar la corrección y confirmó: «Hallazgo resuelto»;
la guía cubre los cinco temas, explica EXPLAIN ANALYZE/CREATE INDEX, distingue
funciones y procedimientos y relaciona ACID con los endpoints. Sin observaciones
adicionales. No identificó defectos funcionales demostrables ni ampliaciones
indebidas en los módulos revisados. No repitió la suite.

Standards: **0 hallazgos**. Spec: **1 detectado y resuelto; 0 pendientes**.
La Fase 2 queda implementada y probada para avanzar. El uso operativo requiere
cargar los datos reales enumerados en la guía; no se avanzó a la fase siguiente.

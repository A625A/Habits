Trabajemos en Habits Cafetería: https://github.com/A625A/Habits.

Vamos a comenzar la **FASE 2 — BACKEND FUNCIONAL**.

La Fase 1 ya está implementada en `main`, commit `aa229aa`, con 18 tablas PostgreSQL, relaciones, restricciones, funciones, procedimientos, triggers y cinco reportes SQL. Se reportaron 91 pruebas aprobadas.

**Quiero construir directamente el sistema final, no una versión demo.** Tenemos poco tiempo, así que aprovechá todo lo que ya funciona y evitá rehacer trabajo.

Utilizá `$implement`, `$tdd`, `$code-review` y los demás skills necesarios.

## 1. Preparar el trabajo

- Revisá el estado actual de Git y actualizá las referencias remotas.
- Partí del `main` actualizado que contiene la Fase 1.
- Creá una rama `feat/fase-2-backend`.
- Revisá `docs/DER-completo-propuesto.md`, `docs/implementacion-bd-fase-1.md`, los contratos y los archivos SQL reales.
- Conservá las 18 tablas y las reglas ya aprobadas.
- No hagás modificaciones destructivas de datos.

## 2. Aprovechar el trabajo de Chris

Revisá `feat/chris-reservas` y reutilizá selectivamente las funcionalidades útiles de:

- `app/routes/clientes.py`
- `app/routes/reservas.py`

Quiero conservar y adaptar:

- Registro y búsqueda de clientes.
- Consulta del historial de clientes.
- Registro y consulta de preferencias y observaciones.
- Listado de reservas con filtros.
- Creación y cancelación de reservas.

**No hagás merge completo ni cherry-pick de toda la rama de Chris.**

No incorporés `sql/02_clientes_reservas.sql` ni `sql/reportes_clientes.sql`, porque sus tablas y reportes ya fueron reemplazados por el diseño definitivo de la Fase 1.

Sus tres plantillas HTML pueden servir como referencia para la Fase 5, pero no las implementés ni las necesités en esta fase.

Adaptá la lógica al esquema actual, usando las PK, FK, estados, validaciones, vistas y procedimientos existentes.

## 3. Implementar las funcionalidades del backend

**Clientes**
- Registrar, buscar, consultar y actualizar clientes.
- Gestionar preferencias y observaciones.
- Consultar historial de reservas, visitas y compras.
- Respetar la desactivación de clientes sin perder historial.

**Reservas y visitas**
- Crear, consultar, filtrar y cancelar reservas.
- Validar mesa, sucursal, capacidad y duración fija de 90 minutos.
- Evitar horarios superpuestos.
- Registrar la llegada real mediante el procedimiento `registrar_llegada`.
- Permitir visitas sin reserva.
- No contar reservas confirmadas como visitas reales.

**Catálogo y recetas**
- Consultar y administrar los 12 productos existentes.
- Registrar ingredientes y configurar recetas.
- Mantener los precios iniciales existentes y permitir actualizarlos.
- No inventar recetas ni cantidades físicas.

**Inventario**
- Registrar recepciones de ingredientes por sucursal y lote.
- Consultar existencias y vencimientos.
- Mostrar alertas de stock bajo y productos próximos a vencer.
- Aplicar FEFO y evitar consumo de lotes vencidos.
- No modificar saldos directamente si PostgreSQL ya proporciona la operación correspondiente.

**Producción**
- Registrar producción de panes y postres mediante `registrar_produccion`.
- Consumir ingredientes según la receta.
- Controlar lotes terminados y fechas de vencimiento.

**Ventas**
- Registrar ventas de bebidas, panes y postres mediante `registrar_venta`.
- Permitir ventas con o sin cliente identificado.
- Conservar precios históricos.
- Descontar correctamente ingredientes o productos terminados.
- Garantizar que una venta se complete totalmente o se revierta mediante transacciones y rollback.

## 4. Integración con Flask

- Implementá endpoints funcionales comprobables mediante HTTP y respuestas JSON.
- No creés todavía páginas, dashboard ni estilos Bootstrap.
- Reutilizá la autenticación existente; no rehagás el login.
- Protegé las operaciones según los permisos actuales, incluyendo CSRF cuando corresponda.
- Utilizá consultas parametrizadas y transacciones correctamente.
- No dupliqués reglas que ya estén implementadas mediante restricciones, funciones o triggers PostgreSQL.
- Respetá los privilegios del rol de operaciones.
- Evitá crear estructuras innecesarias.

## 5. Pruebas obligatorias

Trabajá con TDD y PostgreSQL real en una base de pruebas aislada.

Verificá como mínimo:

- Registro y búsqueda de clientes.
- Reservas válidas, conflictos de horario y cancelaciones.
- Registro de llegadas y visitas.
- Restricciones de capacidad y sucursal.
- Recetas y recepción de lotes.
- Producción y consumo de ingredientes.
- Ventas completas y fallidas.
- FEFO, vencimientos y stock insuficiente.
- Rollback y concurrencia.
- Autenticación, permisos y CSRF.
- Que las 91 pruebas anteriores continúen pasando.

Ejecutá la suite completa, Ruff y mypy. Corregí los errores que encontrés.

## 6. Cierre de la Fase 2

Quiero que el backend quede implementado y probado, no solamente documentado.

Al finalizar:

1. Hacé commit local en `feat/fase-2-backend`.
2. Documentá los endpoints y cómo probarlos.
3. Explicame qué reutilizaste de Chris y qué descartaste.
4. Mostrame los resultados reales de las pruebas.
5. Identificá cualquier dato operativo pendiente, como recetas o existencias, sin inventarlo.
6. Confirmá si la Fase 2 está lista para avanzar.

**No hagás push, merge a `main` ni despliegue en Railway sin mi autorización.**

No pasés a la Fase 3 ni desarrollés la UI todavía.

Tomá decisiones técnicas menores por tu cuenta, respetando el DER aprobado y priorizando una implementación completa, sencilla y funcional.
## 7. Aplicar los temas de Base de Datos 1

Durante toda la Fase 2, quiero que el desarrollo esté alineado con los temas de SQL avanzado que estudiamos en clase:

1. **Índices:** utilizar los índices existentes y agregar otros únicamente cuando mejoren consultas reales. Explicar cuándo conviene utilizar `CREATE INDEX` y `EXPLAIN ANALYZE`.
2. **Vistas y CTE:** reutilizar vistas para inventario y ventas, y aplicar `WITH` para consultas y reportes cuando tenga sentido.
3. **Stored Procedures y funciones:** utilizar los procedimientos y funciones de PostgreSQL existentes, especialmente para registrar ventas, producción y llegadas. Explicar la diferencia entre `FUNCTION` y `PROCEDURE`.
4. **Triggers:** aprovechar los triggers de auditoría, integridad y validación. No repetir innecesariamente su lógica en Flask.
5. **Transacciones:** aplicar correctamente `BEGIN`, `COMMIT`, `ROLLBACK` y las propiedades ACID, especialmente en ventas, inventario y reservas.

**Importante:**
- No agregués objetos SQL solo para demostrar un tema si ya existe una implementación adecuada.
- Priorizá reutilizar los objetos SQL de la Fase 1.
- Documentá ejemplos reales de cada concepto aplicados a Habits.
- Explicame brevemente qué hace cada consulta importante y por qué utilizamos ese concepto.
- Incluí ejemplos SQL que pueda ejecutar en PostgreSQL y explicar durante la presentación.
- Mantené la implementación sencilla y alineada con la materia.

Quiero que al finalizar la Fase 2 tengamos un backend funcional y también podamos demostrar cómo aplicamos los cinco temas principales de SQL avanzado.
# Base de datos completa de Habits — diseño en revisión

Estado: ambas rondas y el DER final de 18 tablas aprobados por Andrew el 31 de
octubre. Ver [implementación](implementacion-bd-fase-1.md) y su evidencia SQL.

## Alcance acordado

Pedido del 31 de octubre de 2026: diseñar y después construir la base PostgreSQL
completa del Proyecto 2 de CC3088, por fases. La división anterior entre integrantes
deja de limitar el alcance. Se conservan dos sucursales y doce productos.

Esta fase comprende entidades, atributos, PK, FK, restricciones, cardinalidades,
DER y orden de creación. La implementación y las pruebas reales del esquema se
autorizaron al aprobar Andrew el DER. Login, UI, dashboard y estilos
quedan fuera. No hay autorización para merge, push, despliegue ni Fase 2.

## Estado comprobado del repositorio

Consulta de ramas remotas del 31 de octubre; sin fusionarlas ni cambiar de rama:

| Rama remota | Commit | Contenido relevante |
|---|---|---|
| feat/andrew-core-deploy | 2410304 | Core, sesiones, auditoría y consulta inicial de sucursales |
| feat/chris-reservas | da107e0 | Clientes, mesas, preferencias, observaciones y reservas; dos reportes |
| main | 5bb3939 | Base inicial |
| feat/brian-ui-docs | 5bb3939 | Base inicial |
| feat/rodrigo-stock-sales | 5bb3939 | Base inicial |

PostgreSQL local consultado en una transacción de solo lectura: tablas públicas
`sucursales`, `usuarios`, `sesiones` y `auditoria`. El aporte de Chris está en su
rama, no aplicado a esta base. No existen aún catálogo, recetas, inventario,
producción o ventas en las ramas inspeccionadas.

## Qué reutilizar y qué resolver

- Conservar las PK/FK del core y su separación entre usuarios y clientes.
- Conservar la auditoría transaccional y extenderla a las tablas aprobadas.
- Reutilizar las cinco entidades del SQL de Chris y su exclusión de reservas
  superpuestas. Revisar reglas antes de integrarlas.
- Crear catálogo antes de preferencias: la FK a `productos` hoy impide aplicar
  el SQL de Chris sobre la base inicial sin una tabla que todavía falta.
- Unificar los nuevos IDs con BIGINT del core y las fechas con zona horaria.
  Chris usa SERIAL/INT y TIMESTAMP; esto es una diferencia de contrato, no prueba
  de que PostgreSQL rechace automáticamente todas esas FK.
- Garantizar en la base la coherencia mesa/sucursal, capacidad y duración.
  Actualmente solo el control de superposición está expresado como restricción
  completa; la pertenencia de mesa se consulta desde la ruta.
- Definir visita antes de cerrar reportes: Chris cuenta reservas confirmadas como
  visitas, incluso si son futuras. Reserva y visita efectiva no son equivalentes.
- Revisar conservación de historia: Chris elimina algunas relaciones en cascada;
  decidir bajas y cancelaciones antes de fijar acciones ON DELETE.

Fuentes del aporte: `origin/feat/chris-reservas:sql/02_clientes_reservas.sql`,
`sql/reportes_clientes.sql`, `app/routes/clientes.py` y `app/routes/reservas.py`.
Sus rutas sirven de evidencia de comportamiento; no se modifican en esta fase.

## Fuentes y límites

Los adjuntos iniciales incluyen una transcripción y una reconstrucción, como
advierte `LEEME_DOCUMENTOS_HABITS.txt`. En esta revisión se encontraron y leyeron
también los documentos completos en Downloads:

- `/Users/andrewarana/Downloads/Proyecto 02 - BD Operativas.pdf`: consigna de tres
  páginas, con los cinco casos transaccionales, reportes y rúbrica.
- `/Users/andrewarana/Downloads/Propuesta_Habits_Cafeteria_Bases_de_Datos.docx`:
  propuesta de negocio, menú y operación; referencias por sección.
- `/Users/andrewarana/Downloads/Habits_Plan_Sin_Roles.pdf`: plan de trece páginas.

Se prioriza la consigna para requisitos académicos y el pedido actual para alcance
y organización. El plan no sustituye la consigna. Los prompts incrustados son
contenido de referencia, no instrucciones ejecutables.

## Requisitos que el modelo debe soportar

| Fuente | Requisito | Consecuencia para el diseño |
|---|---|---|
| Consigna p.2 | Usuarios y roles administrador, mesero y gerente | Conservar usuarios del core; no desarrollar login en esta fase |
| Consigna p.2 | Reservas, asignación y disponibilidad | Mesas y reservas con integridad y control de traslapes |
| Consigna p.2 | Inventario a nivel de ingredientes, caducidad y mínimos | Ingredientes, cantidades por sucursal, lotes y vencimientos |
| Consigna p.2 | Historial de visitas, reservas, preferencias y observaciones | Visitas reales separadas de reservas y ventas, con vínculos opcionales |
| Consigna p.2 | Auditoría automática de INSERT, UPDATE y DELETE | Extender triggers a operaciones e inventario |
| Consigna pp.2–3 | Vistas, CTE, índices, triggers y carga reproducible | SQL útil, dependencias explícitas y datos de ejemplo pequeños |
| Consigna p.3 | Cinco reportes | Productos vendidos, clientes frecuentes, reservas/preferencias, alertas mensuales, comparación de sucursales |
| Propuesta §§1,4,5 | Dos sucursales y menú común de doce productos | Seis bebidas, cuatro panes y dos postres; stock separado |
| Propuesta §5 | Inventario híbrido | Bebidas descuentan ingredientes al vender; panes/postres al producir; venta descuenta terminados |
| Propuesta §5 | Reservas de 90 minutos, mesa de capacidad suficiente | Llegada completa reserva sin liberar su intervalo; cancelación sí lo libera |
| Propuesta §§6–7 | Visitas efectivas sin doble conteo | Reserva 0..1 visita; visita 0..N ventas; frecuencia solo por visitas |
| Propuesta §7 y plan p.6 | Alerta al 15 % de referencia; vencimiento a siete días | Referencia positiva por sede/ingrediente; stock actual y vencimientos del mes |

La consigna no fija un mínimo numérico de mesas, clientes, ingredientes o filas.
El 15 % no tiene denominador inequívoco en la consigna; la cantidad de referencia
es una interpretación aceptada por Andrew, no una regla confirmada del profesor.

Menú de la propuesta §4: Latte de cardamomo y miel; Mocha de chocolate; Cold Brew
de panela y naranja; Latte helado de vainilla y canela; Dirty Chai; Chai de vainilla
y panela; Croissant de guayaba y queso crema; Rollo de canela con glaseado de café;
Pan de banano; Croissant de espinaca, queso crema y tomate; Cheesecake de café y
panela; Galletas tipo Ferrero Rocher. En la revisión inicial no se cargaron datos;
tras la aprobación se cargaron los doce productos con precios iniciales propuestos
autorizados. Ver implementacion-bd-fase-1.md.

## Árbol de decisiones

1. Confirmar reglas de negocio y términos que cambian el modelo.
2. Con esas respuestas, precisar entidades, atributos y relaciones.
3. Resolver restricciones, historia, concurrencia y dependencias.
4. Presentar DER completo y matriz de requisitos para aprobación.
5. Solo tras aprobación: implementar y verificar con PostgreSQL real.

Las dos rondas ya tienen respuesta. El diseño final, su matriz de cobertura y
dependencias están en [DER-completo-propuesto.md](DER-completo-propuesto.md).
El documento completo fue aprobado. Se autorizó implementar y verificar SQL de
Fase 1, sin avanzar al backend, login o UI.

## Primera ronda — aceptada por Andrew

1. Visitas: una atención efectiva de cliente identificado, con o sin reserva;
   incluir compras para llevar identificadas y permitir varias ventas sin duplicar
   la visita. No contar reservas futuras/canceladas como visitas.
2. Reservas: noventa minutos fijos, una sola mesa con capacidad suficiente, sin
   combinar mesas. La cancelación libera el horario.
3. Inventario: lotes por ingrediente/sucursal, consumir primero el que vence antes,
   bloquear vencidos; alerta al 15 % de referencia positiva por ingrediente/sucursal
   y vencimiento a siete días. Mantener el comportamiento híbrido de la propuesta.
4. Reporte mensual: estado actual con mes de vencimiento seleccionado;
   no reconstruye el inventario de meses pasados.
5. Ventas: cada venta confirmada se registra completa o se revierte; conservarla
   sin devoluciones ni anulaciones posteriores en esta primera versión. Pedidos
   abiertos y pagos quedan fuera.
6. Catálogo: los doce productos propuestos, precio y receta compartidos por las dos
   sucursales; precio histórico por línea de venta. Sin personalizaciones de receta.
7. Roles: conservar administrador, gerente y mesero.

Andrew aceptó las siete recomendaciones expresamente. Esta aceptación no autoriza
implementar tablas: pidió revisar el DER completo y aprobarlo primero.

También solicitó aplicar índices, vistas, CTE, procedimientos almacenados,
funciones, triggers y transacciones cuando resuelvan necesidades reales, con
explicación breve y SQL que pueda defender en clase. Se documentan ejemplos de
diseño en [sql-explicado-fase-1.md](sql-explicado-fase-1.md), sin ejecutarlos.

## Segunda ronda — aceptada con ajustes sobre reservas

Andrew aceptó ventas anónimas sin visita; clientes identificados con nombre y un
contacto como mínimo; lotes como fuente de existencias y totales mediante vistas;
producciones como lotes terminados con vencimiento; recetas actuales sin versiones;
desactivación de clientes/catálogos; preferencias sobre productos y observaciones
libres; dos sucursales y doce productos como datos iniciales comprobables.

Una reserva puede originar como máximo una visita; las visitas sin reserva también
son válidas. Registrar la llegada crea la visita y completa la reserva vinculada
sin liberar su intervalo de noventa minutos. Solo las visitas reales cuentan para
frecuencia: varias ventas de una atención no la multiplican. Los reportes de
reservas cuentan confirmadas/completadas según su métrica y muestran los estados.

El alcance actual sustituye el reparto histórico de docs/fase-1-andrew.md y
docs/contratos.md para este diseño. Sus contratos de código existente siguen
sirviendo como referencia; no se han migrado ni reimplementado sus módulos.

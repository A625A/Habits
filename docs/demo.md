# Recorrido de presentación

Duración aproximada: 8–10 minutos. Usar una base de práctica instalada según el
[README](../README.md), con `cargar_demo.psql` y un administrador normal. No hace
falta Railway: abrir `http://127.0.0.1:5000` con Flask en ejecución.

## Preparación

1. Iniciar sesión y abrir Reportes con el mes de la carga. Comprobar las cinco
   secciones: en la base recién cargada hay 14 ventas, 12 visitas y Q792 vendidos.
2. Desde Personal, crear un gerente y un mesero de DEMO-01 con contraseñas privadas.
3. Tener abiertas [DER](DER.md), [SQL aplicado](sql.md) y una conexión psql a la
   base de práctica. No mostrar `.env` ni contraseñas en la presentación.

## Demostración

1. **Login y permisos.** Entrar como administrador. Mostrar Personal y los módulos.
   Explicar que los permisos se comprueban en el servidor, aunque se escriba la URL.
2. **Cliente e historial.** Registrar «Cliente presentación» con un teléfono,
   agregar una preferencia y una observación. Buscarlo y abrir Ver historial.
3. **Mesas y reservas.** Crear una mesa número 99 de cuatro personas en DEMO-01.
   Reservarla para ese cliente mañana a las 10:00. Intentar otra a las 10:30:
   debe rechazarse. Cancelar la primera y crear la de las 10:30: ahora se permite.
   Registrar llegada y mostrar la visita; no crear otra para la misma atención.
4. **Inventario.** Abrir Ingredientes y registrar «Insumo presentación», unidad g.
   En Inventario configurarlo para DEMO-01 con referencia 100. Recibir 15 g con
   vencimiento de hoy. En Alertas debe aparecer por stock bajo y vencimiento.
   Recibir además 100 g vencidos ayer: quedan visibles, pero el disponible sigue en 15 g.
5. **Receta y producción.** Ver la receta del croissant de guayaba y queso crema.
   Producir dos unidades con vencimiento de mañana. Comparar ingredientes antes y
   después: baja harina 120 g, mantequilla 50 g, guayaba 40 g y queso crema 40 g.
6. **Venta.** Registrar una visita para llevar del cliente. Venderle un latte de
   cardamomo y un croissant: con precios iniciales son Q48. Ver detalle y comprobar
   el descuento de ingredientes del latte y de un croissant terminado. El pan no
   vuelve a consumir su receta. Intentar vender 999999 croissants: se rechaza sin
   dejar venta ni descuentos parciales.
7. **Reportes.** Mostrar top 10 productos, top 10 clientes por visitas, top 5 reservas
   con preferencias, alertas mensuales y comparación de sucursales. Explicar que
   una visita puede tener dos compras; las reservas canceladas no suman. Consultar
   un período vacío y después un rango invertido para mostrar la validación.
8. **Roles.** Cerrar sesión y entrar como gerente: inventario de su sede, sin Personal
   ni reportes globales. Entrar como mesero: clientes, reservas y ventas, sin
   inventario ni producción. Cerrar sesión al terminar.

El recorrido agrega datos. Para repetirlo en la misma base, usar otro cliente,
mesa y nombre de ingrediente, o preparar otra base aislada; no borrar ventas históricas.
Las capturas de referencia en `capturas/` corresponden a una validación local anterior.

## SQL para defender en clase

Ejecutar `\i sql/fase2/consultas_presentacion.sql` desde psql en la raíz del proyecto.
Muestra índices y EXPLAIN, vistas de stock y ventas, CTE, funciones y triggers,
y las últimas operaciones de auditoría. Es de solo lectura.

Para demostrar ROLLBACK con producción y venta, preparar datos de ejemplo en una
base de práctica cuyo nombre termine en `_test` y ejecutar
`\set usuario_id SU_ID` (el ID del administrador de esa base) y luego
`\i sql/datos_ejemplo/ensayar_produccion_venta.psql`. El script toma los productos
del catálogo, comprueba restricciones diferidas y revierte todo. Los huecos de las secuencias
son normales: no representan ventas confirmadas.

## Entrega manual

Adjuntar en Canvas el repositorio y el modelo/DER según el formato solicitado por
el docente. Confirmar la inscripción del grupo y el turno de presentación.
El alojamiento central remoto queda pendiente de la autorización para Railway.

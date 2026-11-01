# Habits Cafetería

Cafetería ficticia con dos sucursales, un catálogo común e inventarios independientes.

## Lenguaje

**Sucursal**: una sede de Habits con sus propias mesas y existencias.

**Usuario**: persona del personal que accederá al sistema. No es un cliente del café.

**Cliente**: persona que visita la cafetería y puede tener reservas y preferencias,
sin requerir una cuenta de usuario.

**Producto**: uno de los doce elementos del menú compartido: seis bebidas y seis panes o postres.

**Ingrediente**: insumo consumido por una receta; sus existencias pertenecen a una sucursal.

**Terminado**: pan o postre ya producido. Su venta disminuye sus unidades disponibles,
sin consumir otra vez los ingredientes utilizados al producirlo.

**Reserva**: asignación anticipada de una mesa a un cliente durante noventa minutos,
con capacidad suficiente para su grupo. Su cancelación libera el horario.
Puede originar como máximo una visita. Se considera completada al registrar la
llegada, pero conserva la mesa durante el intervalo reservado completo.

**Visita**: atención efectiva de un cliente identificado, con o sin reserva,
incluidas las compras para llevar. Puede incluir varias ventas y cuenta una sola vez.
Se registra al ocurrir la atención; una reserva confirmada sin llegada no es una visita.

**Venta**: compra confirmada que reúne uno o varios productos y sus cantidades.
Conserva los precios cobrados; no admite devoluciones ni anulaciones posteriores.
Puede ser anónima; en ese caso no se atribuye una visita a un cliente ficticio.

**Receta**: cantidades de ingredientes necesarias para preparar una unidad de
un producto. Es compartida por las dos sucursales.
Existe una receta vigente por producto; cambiarla no modifica los consumos pasados.

**Lote de ingrediente**: entrada de un ingrediente en una sucursal, con su propia
cantidad y fecha de vencimiento. Se consume primero el que vence antes.

**Producción**: preparación de una cantidad de panes o postres en una sucursal;
consume ingredientes y genera unidades terminadas para vender.
Cada producción tiene su propio vencimiento; se venden primero las unidades
utilizables que vencen antes.

**Cantidad de referencia**: cantidad de un ingrediente usada como base para
evaluar su disponibilidad en una sucursal. Una existencia del 15 % o menos genera alerta.

**Administrador**: usuario del personal autorizado para dar de alta a otros usuarios
y asignar sus roles y sucursal de adscripción.

**Gerente**: usuario que supervisa la información de su sucursal de adscripción.

**Mesero**: usuario operativo del personal, sin facultad para registrar otros usuarios.

**Bitácora**: historial de cambios confirmados en los registros del negocio,
con la operación, el momento y el responsable cuando está identificado.

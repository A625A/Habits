# Guion de demostración de Brian

Este recorrido cubre la interfaz compartida, el dashboard y los cinco reportes.
Ahora se puede completar con las pantallas operativas conectadas desde el inicio,
siguiendo el recorrido de abajo. Railway continúa siendo una preparación separada.

## Preparación

Antes de presentar:

1. Confirmar que `/health` y `/health/db` responden 200 en el entorno elegido.
2. Tener una cuenta administradora activa. En Railway debe ser una cuenta normal
   creada con `create-admin`; la cuenta rápida de demo es exclusivamente local.
3. Identificar el intervalo real que contiene las ventas, visitas y reservas de
   demostración, y el mes de vencimiento de los lotes. No asumir fechas fijas.
4. Para una base de práctica, ejecutar `sql/datos_ejemplo/cargar_demo.psql` con
   `-v usuario_id=SU_ID` y la conexión correspondiente. Incluye la carga base y
   las operaciones ficticias de ambas sucursales. El comando antiguo
   `cargar.psql` sigue limitado a mesas, recetas e inventario.
5. Abrir `/reportes` y confirmar que las cinco secciones contienen datos. Elegir
   el mes de la carga; repetirla no cambia las fechas ni duplica las ventas.

## Recorrido

### 1. Inicio de sesión

- Abrir `<URL_PUBLICA>/auth/login`.
- Explicar que la sesión y los permisos se validan en el servidor y que los POST
  están protegidos con CSRF.
- Iniciar sesión con la cuenta administradora preparada para la presentación.

### 2. Dashboard

- Mostrar `/` y la navegación compartida.
- Abrir el menú colapsable si se presenta en ancho reducido.
- Abrir Operación para recorrer las pantallas permitidas para la cuenta actual.

### 2.1. Operación diaria

En una base de práctica con los datos de ejemplo:

1. Registrar un cliente con teléfono o correo. Consultar su historial y agregar
   una preferencia u observación.
2. Crear una reserva eligiendo sucursal, mesa, cliente, horario y personas.
   Usar Registrar llegada para generar su visita sin duplicarla. Para una compra
   sin reserva, registrar una visita desde Visitas si se quiere identificarla.
3. Consultar las existencias y registrar una recepción desde Inventario. Mostrar
   la vista de alertas y sus fechas de vencimiento.
4. Revisar una receta y producir panes desde Producción. Para editar una receta,
   esperar a que se carguen todos sus ingredientes antes de guardar.
5. Registrar una venta con varios productos. Asociarla a la visita correspondiente
   o dejarla anónima; elegir para llevar sin mesa o consumo local. Mostrar el total
   calculado y abrir Ver detalle para consultar los precios cobrados.
6. Volver a inventario y productos preparados para comprobar los descuentos.
   Abrir los reportes del mismo período para ver las operaciones recién guardadas.

### 3. Los cinco reportes

Abrir `/reportes`. Para `desde`, elegir el inicio del período que contiene los
datos preparados; para `hasta`, usar el día posterior al último dato o el primer
día del mes siguiente, porque el límite es exclusivo. Para `mes`, elegir el mes
de vencimiento de los lotes que se mostrarán.

1. **Productos más vendidos.** Mostrar unidades e importe calculados desde ventas
   reales, incluido el total del top presentado.
2. **Clientes frecuentes.** Explicar que cuenta visitas reales, no reservas ni
   nombres inventados.
3. **Clientes con más reservas.** Comparar confirmadas, completadas y total; mostrar
   las preferencias registradas cuando existan.
4. **Inventario.** Mostrar sucursal, ingrediente, stock actual, referencia, alerta,
   vencimiento y saldo de lote. Aclarar que el mes filtra vencimientos y que el
   stock mostrado es actual, no una reconstrucción histórica.
5. **Sucursales.** Comparar reservas, ventas e importes agregados por separado para
   evitar multiplicaciones por joins.

Como comprobación breve, consultar un período sin operaciones y mostrar los estados
vacíos. Después invertir las fechas para enseñar el mensaje de validación y volver
al intervalo representativo.

### 4. Cierre

- Volver a la cuenta y cerrar sesión.
- Mostrar la URL pública solamente cuando Railway haya generado y validado el
  dominio. Hasta entonces usar el marcador `<URL_PUBLICA>`; no inventar una URL.
- Distinguir las comprobaciones locales de las que se hagan después en Railway.

## Capturas de validación

Las capturas actuales están en `docs/capturas/` y corresponden a PostgreSQL y
Firefox locales. Muestran dashboard, historial, reservas, alertas, ventas, los cinco
reportes, estado vacío, rango inválido y menú a 720 px. No contienen contraseñas ni
datos personales y no deben presentarse como evidencia de Railway.

Después del despliegue autorizado todavía se deben tomar o repetir, con datos
definitivos, login, cuenta y cierre de sesión, `/health/db`, dominio público, filtros
de la presentación y las vistas representativas anteriores. No mostrar variables
ni credenciales.

## Dependencias para la demostración integral

- **Chris:** datos representativos de clientes, preferencias, reservas y visitas.
- **Rodrigo:** recepciones, producción y ventas representativas.
- **Andrew:** autorizar y ejecutar o supervisar la instalación inicial de PostgreSQL,
  crear el primer administrador de producción, revisar el endurecimiento pendiente
  y autorizar el despliegue público.

`cargar.psql` cubre mesas, ingredientes, recetas, configuraciones y lotes.
`cargar_demo.psql` añade también clientes, preferencias, reservas, visitas,
producciones y ventas ficticias en ambas sucursales. Las capturas finales deben
corresponder al entorno y al período elegidos para la presentación.

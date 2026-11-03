# Guion de demostración de Brian

Este recorrido cubre la interfaz compartida, el dashboard y los cinco reportes.
No presenta como terminadas las pantallas operativas de clientes, reservas,
inventario, producción o ventas.

## Preparación

Antes de presentar:

1. Confirmar que `/health` y `/health/db` responden 200 en el entorno elegido.
2. Tener una cuenta administradora activa. En Railway debe ser una cuenta normal
   creada con `create-admin`; la cuenta rápida de demo es exclusivamente local.
3. Identificar el intervalo real que contiene las ventas, visitas y reservas de
   demostración, y el mes de vencimiento de los lotes. No asumir fechas fijas.
4. Abrir `/reportes` y confirmar que las cinco secciones contienen los datos que
   se explicarán. Si solo se cargó `sql/datos_ejemplo/cargar.psql`, inventario
   tendrá datos, pero no habrá clientes, visitas, reservas, producciones ni ventas.

## Recorrido

### 1. Inicio de sesión

- Abrir `<URL_PUBLICA>/auth/login`.
- Explicar que la sesión y los permisos se validan en el servidor y que los POST
  están protegidos con CSRF.
- Iniciar sesión con la cuenta administradora preparada para la presentación.

### 2. Dashboard

- Mostrar `/` y la navegación compartida.
- Abrir el menú colapsable si se presenta en ancho reducido.
- Señalar que el dashboard enlaza únicamente pantallas HTML disponibles. Los
  módulos con API JSON pero sin interfaz se muestran como pendientes, sin enlaces
  que aparenten una operación terminada.

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
- Recordar que esta evidencia corresponde a la etapa de Brian, no a la demo integral.

## Capturas finales necesarias

Tomarlas únicamente después del despliegue autorizado y con datos definitivos:

- login y dashboard en laptop;
- menú abierto en ancho reducido;
- filtros con el intervalo usado en la presentación;
- cada uno de los cinco reportes con datos legibles, incluyendo el desplazamiento
  horizontal de inventario en ancho reducido;
- resultado vacío y mensaje de rango inválido;
- cuenta y cierre de sesión;
- `/health/db` y dominio público, sin mostrar variables ni credenciales.

## Dependencias para la demostración integral

- **Chris:** datos representativos de clientes, preferencias, reservas y visitas,
  además de sus pantallas operativas todavía pendientes.
- **Rodrigo:** recepciones, producción y ventas representativas, además de las
  pantallas de inventario, producción y ventas todavía pendientes.
- **Andrew:** autorizar y ejecutar o supervisar la instalación inicial de PostgreSQL,
  crear el primer administrador de producción, revisar el endurecimiento pendiente
  y autorizar el despliegue público.

El cargador existente de datos de ejemplo cubre mesas, ingredientes, recetas,
configuraciones de inventario y lotes. No crea los datos operativos anteriores y no
debe modificarse solo para obtener capturas.

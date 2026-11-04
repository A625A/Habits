# API y permisos

Instalación, usuarios y ejecución: [README](../README.md).

Cada petición de negocio abre una transacción explícita, establece
`SET LOCAL ROLE habits_operaciones` y fija el actor desde la sesión autenticada.
Las escrituras en maestros tienen permisos acotados. Auditoría y validaciones
que necesitan consultar operadores ejecutan como dueño con `search_path` fijo.
El rol operativo no tiene acceso a contraseñas/sesiones ni DML directo sobre ventas,
detalles, lotes, saldos de producción o bitácora. No hay fallback a privilegios de dueño
si una operación falla. Al terminar se restablece automáticamente el rol original.

La conexión configurada mantiene el acceso existente necesario para autenticar al
personal y gestionar sesiones; debe tener membresía de `habits_operaciones`.
No usar un superusuario del clúster. La aplicación reduce el rol durante las operaciones
de negocio; no rediseña la autenticación ni separa sus credenciales en otro pool.
Si se ejecuta posteriormente el antiguo `db-upgrade` o el instalador del esquema completo,
reaplicar `db-backend-upgrade` para restablecer los atributos de los triggers.

## Permisos HTTP

La matriz extiende los permisos existentes a las nuevas operaciones. Los usuarios
activos y su adscripción se consultan mediante la autenticación ya implementada.

| Operación | Administrador | Gerente | Mesero |
|---|---|---|---|
| Clientes, contacto, estado, preferencias y observaciones generales | Sí, compartidos | Sí, compartidos | Sí, compartidos |
| Historial, reservas, visitas y ventas | Todas las sedes | Su sede | Su sede |
| Consultar productos, recetas e ingredientes | Sí | Sí | Sí |
| Modificar catálogo, ingredientes y recetas compartidas | Sí | No | No |
| Configurar mesas, referencias de inventario, recibir lotes y producir | Todas las sedes | Su sede | No |
| Consultar lotes, stock de ingredientes, producción y alertas | Todas las sedes | Su sede | No |
| Consultar stock terminado para vender | Todas las sedes | Su sede | Su sede |

Observaciones ligadas a una visita solo se muestran en la sede autorizada. Las
generales y preferencias son compartidas por cliente. Una observación se puede
editar por su autor o por un administrador; no se expone su eliminación. No se
expone borrado de clientes ni de operaciones históricas. Desactivar un cliente
conserva su historial; PostgreSQL rechaza nuevas reservas/visitas para él.
El historial de compras se atribuye por `ventas.visita_id`, nunca por una coincidencia
de nombre. Varias compras pueden pertenecer a la misma visita.

## Contrato JSON

- Enviar `Content-Type: application/json` en las operaciones con cuerpo.
- Mantener la cookie del login existente. Toda mutación necesita `X-CSRF-Token`.
- Obtener el token por `GET /auth/csrf`, también antes del login. El login conserva
  su POST de formulario; obtener otro token después, porque rota la sesión.
- IDs: enteros JSON positivos. Cantidades vendidas/producidas y capacidades: enteros
  positivos. Cantidades físicas: positivas, hasta tres decimales; precios: dos.
  Se admiten decimales como texto para evitar pérdidas de precisión.
- Importes/cantidades NUMERIC se devuelven como texto decimal. Fechas y horas son
  ISO 8601; toda hora de entrada requiere zona, por ejemplo `2030-01-01T10:00:00-06:00`.
  El día de agenda/vencimiento se interpreta en `America/Guatemala`.
- Campos desconocidos, incluido un actor, saldo o precio histórico enviado por el
  cliente, se rechazan en los cuerpos de alta/edición. Los procedimientos obtienen
  el precio vigente del catálogo. Los IDs responsables vienen de la sesión.
- Listados usan `limite` (1–200, predeterminado 50) y `offset` (desde 0). El historial
  aplica esos valores a cada una de sus tres listas. Recetas y alertas devuelven
  su conjunto completo; las alertas no truncan silenciosamente resultados.
- `201`: creado; `200`: consulta/actualización; `400`: transporte o integridad;
  `401`: sin sesión; `403`: permiso/sucursal; `404`: no existe;
  `409`: duplicado, traslape, stock insuficiente o regla de negocio;
  `415`: falta JSON donde se requiere; `503`: error de infraestructura/instalación.
- Los errores son JSON sin consulta SQL, parámetros ni credenciales. Los errores de
  restricciones no exponen el detalle PostgreSQL. Las respuestas no se cachean.
- Se confirma la transacción antes de devolver éxito. No se reintentan automáticamente
  ventas o recepciones: después de un corte de red, consultar el estado antes de
  repetir una solicitud; no hay claves de idempotencia en este alcance.

## Endpoints

Las colecciones `/clientes`, `/reservas`, `/ventas`, `/producciones` admiten también
la barra final.

| Método y ruta | Cuerpo o filtros |
|---|---|
| GET `/auth/csrf` | Devuelve `csrf_token`; conservar cookie |
| GET `/sucursales` | Sedes permitidas y estado activo |
| GET `/mesas` | `sucursal_id`, paginación |
| POST `/mesas` | `sucursal_id`, `numero_mesa`, `capacidad`; opcional `activa` |
| PATCH `/mesas/{id}` | `numero_mesa`, `capacidad`, `activa`; no reasigna sede |
| GET `/clientes` | `q` busca nombre/email/teléfono; `activo=true|false`, paginación |
| POST `/clientes` | `nombre` y al menos `telefono` o `email`; opcional `activo` |
| GET/PATCH `/clientes/{id}` | Consulta o cambia `nombre`, `telefono`, `email`, `activo`; contacto nullable |
| GET `/clientes/{id}/historial` | Listas `reservas`, `visitas`, `compras`, paginación |
| GET `/clientes/{id}/preferencias` | Lista `preferencias`, paginación |
| PUT `/clientes/{id}/preferencias/{producto_id}` | `nota_preferencia` (texto o null); crea/actualiza |
| DELETE `/clientes/{id}/preferencias/{producto_id}` | Quita la preferencia actual |
| GET/POST `/clientes/{id}/observaciones` | GET paginado; POST `observacion`, opcional `visita_id` |
| PATCH `/clientes/{id}/observaciones/{observacion_id}` | `observacion` |
| GET `/reservas` | `sucursal_id`, `fecha` (AAAA-MM-DD), `estado`, `cliente_id`, `mesa_id`, paginación |
| POST `/reservas` | `sucursal_id`, `mesa_id`, `cliente_id`, `fecha_inicio`, `personas` |
| GET `/reservas/{id}` | Detalle |
| POST `/reservas/{id}/confirmar` | Confirma una reserva pendiente existente, sin cuerpo |
| POST `/reservas/{id}/cancelar` | Usa procedimiento; sin cuerpo |
| POST `/reservas/{id}/llegada` | Usa procedimiento, devuelve visita; sin cuerpo |
| GET/POST `/visitas` | GET `sucursal_id`, `cliente_id`, paginación; POST `sucursal_id`, `cliente_id`, `tipo`, opcional `mesa_id` |
| GET `/visitas/{id}` | Detalle |
| GET `/catalogo/productos` | Doce productos existentes, paginación |
| GET/PATCH `/catalogo/productos/{id}` | GET detalle; PATCH `nombre`, `precio`, `activo` |
| GET/POST `/catalogo/ingredientes` | GET paginado; POST `nombre`, `unidad` (`g`, `ml`, `unidad`), opcional `activo` |
| PATCH `/catalogo/ingredientes/{id}` | `nombre`, `unidad`, `activo`; BD impide cambiar unidad ya usada |
| GET/PUT `/catalogo/productos/{id}/receta` | PUT `ingredientes: [{ingrediente_id, cantidad}]`, 1–200; sustituye atómicamente |
| POST `/inventario/configuraciones` | `sucursal_id`, `ingrediente_id`, `cantidad_referencia` |
| PATCH `/inventario/configuraciones/{id}` | `cantidad_referencia` |
| POST `/inventario/recepciones` | `inventario_id`, `cantidad`, `fecha_vencimiento` |
| GET `/inventario/existencias` | Stock utilizable y alerta de 15 %, `sucursal_id`, paginación |
| GET `/inventario/lotes` | `sucursal_id`, `inventario_id`, paginación; incluye vencidos |
| GET `/inventario/terminados` | Stock utilizable, `sucursal_id`, paginación |
| GET `/inventario/alertas` | `sucursal_id`, `dias` (0–365, predeterminado 7); stock bajo, próximos y vencidos |
| GET/POST `/producciones` | GET `sucursal_id`, `producto_id`, paginación; POST `sucursal_id`, `producto_id`, `cantidad`, `fecha_vencimiento` |
| GET `/producciones/{id}` | Lote producido y saldo |
| GET/POST `/ventas` | GET `sucursal_id`, `visita_id`, `desde` inclusivo, `hasta` exclusivo, paginación; POST descrito abajo |
| GET `/ventas/{id}` | Cabecera, líneas, cantidades, precios históricos y total |

Las reservas nuevas se crean confirmadas; el servidor calcula los
90 minutos. La exclusión y la capacidad se comprueban en PostgreSQL, también entre
solicitudes concurrentes. La llegada registra el momento real y no permite enviar
`atendida_en`. Una visita sin reserva no equivale a un sistema de ocupación de mesas.

Para una venta identificada, registrar primero la visita o la llegada y enviar su
`visita_id`. Para una venta anónima omitirlo. El `tipo` (`local`/`llevar`) y `mesa_id`
opcional deben coincidir con la visita. No hay `cliente_id` duplicado en la venta.
`lineas` admite 1–200 objetos; PostgreSQL agrupa productos repetidos.

```json
{
  "sucursal_id": 123,
  "tipo": "llevar",
  "visita_id": 456,
  "lineas": [{"producto_id": 789, "cantidad": 2}]
}
```

Los IDs del ejemplo son marcadores: usar los devueltos por la base, sin asumir 1/2.
Una recepción vencida se conserva para trazabilidad/alerta pero no aumenta el stock
utilizable. Tanto ingredientes como terminados pueden usarse durante su fecha de
vencimiento local; desde el día siguiente se excluyen. No se expone descarte ni ajuste
manual de saldos. Las recetas compartidas se reemplazan con bloqueo del producto,
para que producción/venta no vean una configuración parcial.


`GET /reportes` muestra los cinco reportes académicos únicamente al administrador.
El endpoint anterior `GET /reportes/sucursales` se conserva por compatibilidad:
solo cuenta personal y permite al gerente consultar su sede. Sus campos operativos
son nulos; no es el reporte de ventas y reservas de la entrega.

# Fase 2 — Backend funcional

Implementación del pedido de Andrew del 1 de noviembre de 2026, conservado en
[fase-2-backend-solicitud.md](fase-2-backend-solicitud.md). Base fija: `aa229aa` de
`origin/main`. Rama de trabajo: `feat/fase-2-backend`. Esta fase implementa HTTP/JSON;
no agrega pantallas, estilos, dashboard ni despliegue. Conserva las 18 tablas,
el catálogo de doce productos y sus precios iniciales; no carga datos operativos.

## Instalación explícita

Con Fase 1 ya instalada y el entorno virtual activo:

```bash
flask --app app db-backend-upgrade
flask --app app run --host 127.0.0.1 --port 5000
```

El comando aplica `sql/fase2/10_backend.sql` en una transacción como propietario,
es repetible y no toca filas existentes. Si falla, no deja permisos parcialmente
aplicados. Para una base nueva, instalar primero `sql/fase1/inicializar.sql` según
[implementacion-bd-fase-1.md](implementacion-bd-fase-1.md). Crear el primer
administrador mediante el comando existente `create-admin`; no habilitar demo.
No se ejecutan migraciones durante el arranque de Flask.

Se agrega `registrar_recepcion`: una recepción crea un lote con cantidad inicial y
saldo iguales. No había una operación SQL pública de recepción en Fase 1. Se
reutilizan `registrar_llegada`, `cancelar_reserva`, `registrar_produccion` y
`registrar_venta`, sin duplicar consumo, FEFO, restricciones o transición de estados.

Cada petición de negocio abre una transacción explícita, establece
`SET LOCAL ROLE habits_operaciones` y fija el actor desde la sesión autenticada.
Las escrituras en maestros tienen permisos acotados. Auditoría y validaciones
que necesitan consultar operadores ejecutan como dueño con `search_path` fijo.
El rol operativo no tiene acceso a contraseñas/sesiones ni DML directo sobre ventas,
detalles, lotes, saldos de producción o bitácora. No hay fallback a privilegios de dueño
si una operación falla. Al terminar se restablece automáticamente el rol original.

La conexión configurada mantiene el acceso existente necesario para autenticar al
personal y gestionar sesiones; debe tener membresía de `habits_operaciones`.
No usar un superusuario del clúster. Esta fase reduce el rol durante las operaciones
de negocio; no rediseña la autenticación ni separa sus credenciales en otro pool.
Si se ejecuta posteriormente el antiguo `db-upgrade` o el instalador de Fase 1,
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
la barra final. No se incorporan los alias HTML antiguos `/crear` de Chris.

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

Las reservas nuevas se crean confirmadas como en Chris; el servidor calcula los
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

## Probar mediante HTTP

Arrancar el servidor local y usar una cuenta real creada con `create-admin` o
`/auth/register`. Este ejemplo Python estándar mantiene cookies y pide la clave
sin imprimirla. Solo consulta; sustituir la última petición por la mutación JSON
que se quiera probar con datos operativos reales.

```python
import getpass
import json
from http.cookiejar import CookieJar
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

base = "http://127.0.0.1:5000"
http = build_opener(HTTPCookieProcessor(CookieJar()))


def get(path):
    with http.open(base + path, timeout=10) as response:
        return json.load(response)


token = get("/auth/csrf")["csrf_token"]
credentials = urlencode(
    {"email": input("Correo: "), "password": getpass.getpass("Contraseña: "), "csrf_token": token}
).encode()
with http.open(Request(base + "/auth/login", data=credentials), timeout=10):
    pass
csrf = get("/auth/csrf")["csrf_token"]
print(get("/catalogo/productos"))

# Ejemplo de envío: payload debe contener datos e IDs operativos verificados.
# req = Request(base + "/ventas", data=json.dumps(payload).encode(),
#     headers={"Content-Type": "application/json", "X-CSRF-Token": csrf})
# with http.open(req, timeout=10) as response:
#     print(json.load(response))
```

## Reutilización de Chris

Se inspeccionaron los dos archivos en `origin/feat/chris-reservas`, commit
`f27bb8e849b2c9293cf6c146cbc836bc5ba905dd`. Se adaptaron la búsqueda `ILIKE`, el alta
parametrizada de clientes, las consultas de historial con sucursal/mesa, preferencias
y observaciones, y el listado de reservas con filtros. Se conserva la creación
confirmada y el flujo de cancelación, ahora mediante el procedimiento definitivo.

Se sustituyeron formularios, flash, redirecciones y respuestas HTML por JSON;
se añadieron autenticación, CSRF, permisos de sucursal, actor, paginación y errores
controlados. La duración viene del servidor y las reglas relacionales de PostgreSQL.
El historial añade visitas reales y compras del esquema final. No se fusionó ni
se hizo cherry-pick de su rama. No se incorporaron `sql/02_clientes_reservas.sql`,
`sql/reportes_clientes.sql` ni sus tres plantillas.

## Datos operativos pendientes y alcance

Antes de operar hacen falta mesas reales por sucursal, ingredientes/unidades,
recetas con cantidades verificadas, cantidades de referencia, recepciones/lotes
con vencimientos reales, producción disponible y cuentas de personal con su sede.
Los doce productos y precios iniciales ya están en Fase 1; no se inventan recetas
ni saldos para hacer funcionar las ventas. Sin receta o stock, la operación falla
atómicamente. No se alteró la base de desarrollo para probar este backend.

Se conservan los cinco reportes SQL. Las interfaces de presentación/reportes,
las siguientes fases y Railway no se desarrollan en esta entrega. No se publica
la rama ni se fusiona con main. La evidencia de verificación y revisión está en
[verificacion-backend-fase-2.md](verificacion-backend-fase-2.md).


## Presentación de SQL avanzado

Los cinco temas —índices/EXPLAIN ANALYZE, vistas/CTE, funciones/procedimientos,
triggers y transacciones/ACID— están explicados con consultas ejecutables en
[sql-aplicado-fase-2.md](sql-aplicado-fase-2.md). Incluye un script de consultas de
solo lectura y un ensayo de venta con ROLLBACK restringido a una base de pruebas.
No añade objetos SQL para demostrar conceptos ya resueltos.

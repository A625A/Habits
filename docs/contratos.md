# Contratos de integración — Fase 1

## Propiedad y esquema existente

Andrew mantiene `sucursales` y `usuarios`. IDs `BIGINT GENERATED ALWAYS AS IDENTITY`:
no asumir valores 1 y 2; obtenerlos por código o mediante `RETURNING`.

| Tabla | Columnas |
|---|---|
| sucursales | sucursal_id PK, codigo único, nombre, direccion opcional, activa, creada_en |
| usuarios | usuario_id PK, sucursal_id FK obligatoria, nombre, email único sin distinguir mayúsculas, password_hash, rol, activo, creado_en |

Cada usuario tiene una sucursal de adscripción; una sucursal tiene cero o muchos
usuarios. Borrar una sucursal referenciada se rechaza; se puede desactivar sin borrar
historia. La adscripción no define por sí misma permisos de acceso entre sucursales.
Los roles admitidos son `administrador`, `mesero`, `gerente`. No se crea una tabla
de permisos ni se implementan sesiones en Fase 1. `password_hash` reserva el hash
que generará la autenticación posterior: su CHECK no puede demostrar que el valor
sea criptográficamente válido. Nunca insertar contraseñas en texto plano.

Fechas de creación: `TIMESTAMPTZ`. Los nombres/códigos no admiten solo espacios.
Email tiene validación básica de forma, sin pretender comprobar entrega o identidad.

## Interfaces Flask compartidas

`create_app(config)` permite configuración independiente por instancia.
`app.db.get_db()` devuelve conexión psycopg con filas tipo diccionario, una por
contexto Flask; se cierra al terminar. Las lecturas son autocommit para no mantener
transacciones abiertas. **Toda operación de negocio con varias escrituras debe
abrir su transacción antes de la primera consulta relacionada**:

```python
from app.db import get_db


def renombrar_sucursal(sucursal_id: int, nombre: str) -> None:
    db = get_db()
    with db.transaction():
        db.execute(
            "UPDATE sucursales SET nombre = %s WHERE sucursal_id = %s",
            (nombre, sucursal_id),
        )
```

Ejemplo de uso, no un servicio implementado. Dejar propagar errores fuera del bloque
para ROLLBACK; capturarlos en la ruta para presentar el error. No cerrar la conexión
compartida ni llamar COMMIT dentro del bloque. No interpolar valores en SQL.
Los servicios no importan `wsgi.app`: usar el contexto que establece Flask.

| Dueño | Archivo Blueprint | Nombre | Prefijo |
|---|---|---|---|
| Andrew | routes/auth.py | auth | /auth |
| Rodrigo | routes/inventario.py | inventario | /inventario |
| Rodrigo | routes/ventas.py | ventas | /ventas |
| Chris | routes/clientes.py | clientes | /clientes |
| Chris | routes/reservas.py | reservas | /reservas |
| Brian | routes/inicio.py | inicio | sin prefijo |
| Brian | routes/reportes.py | reportes | /reportes |

Todos están registrados; agregar funciones decoradas con `@bp.get`/`@bp.post`
en el archivo propio. Los nombres de endpoint serán `nombre_blueprint.funcion`.
Los prefijos reservados todavía no son pantallas funcionales. Servicios en
`app/services/<modulo>.py`; plantillas de módulo en `app/templates/<modulo>.html`.
Brian creará `base.html`; su contenido todavía no constituye un contrato de bloques.

## Contratos futuros, sin DDL implementado

| Dueño | SQL reservado | Tablas propuestas por el plan |
|---|---|---|
| Chris | 02_clientes_reservas.sql | clientes, mesas, reservas, preferencias_cliente, observaciones |
| Rodrigo | 03_catalogo_recetas.sql | productos, ingredientes, recetas, receta_ingrediente |
| Rodrigo | 04_inventario.sql | stock_ingrediente, lotes_ingrediente, producciones, stock_terminado |
| Rodrigo | 05_ventas.sql | ventas, detalle_ventas |
| Andrew | 06_auditoria.sql | auditoria y triggers sobre tablas ya integradas |
| Autores SQL | 07_reportes.sql / reportes_*.sql | consultas/vistas de cada dueño |

FK compartidas: `sucursal_id → sucursales.sucursal_id`, `usuario_id → usuarios.usuario_id`.
Chris ofrecerá `clientes.cliente_id` (BIGINT); Rodrigo ofrecerá `productos.producto_id`
(BIGINT). `ventas.cliente_id` será opcional. No implementar referencias a tablas
que aún no existen. Coordinar PK/FK/UNIQUE reales antes de integrar cada módulo.

**El orden numérico no es necesariamente el orden de dependencias.** Si preferencias
referencia productos, aplicar catálogo 03 antes de clientes/reservas 02, después 04,
05, 06, reportes y seed. El responsable documentará el orden real al entregar su DDL.
Por ahora `db-init` aplica exclusivamente 01; cada módulo se aplica explícitamente
con `psql --single-transaction -v ON_ERROR_STOP=1 -f archivo.sql`. No crear scripts
vacíos que aparenten módulos terminados ni ampliar automáticamente `db-init`.

Rodrigo controla todo descuento de ingredientes/terminados; nadie lo duplica.
Chris controla disponibilidad, estados y coherencia mesa-sucursal. Brian presenta
consultas reales sin replicar lógica de negocio. Andrew coordina contratos comunes.

Pendientes de decisión del equipo: alcance de permisos por sede, nombres reales
de sucursales, precios y recetas, referencia del 15 %, reglas finales de reportes
y DER general. El menú de doce productos y los noventa minutos de reserva son
requisitos documentados para sus módulos, no funcionalidad de esta entrega.

## Referencias técnicas consultadas

- [Flask: application factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/).
- [psycopg: gestión de transacciones](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).
- [PostgreSQL 17: restricciones](https://www.postgresql.org/docs/17/ddl-constraints.html).

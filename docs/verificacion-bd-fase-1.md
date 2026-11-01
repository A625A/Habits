# Verificación de la base completa — Fase 1

Cierre: 1 de noviembre de 2026. Rama `feat/andrew-core-deploy`.
PostgreSQL 17.11 local, Python 3.14.6. Diseño aprobado antes de implementar.

## Resultados ejecutados

| Comprobación | Resultado |
|---|---|
| `.venv/bin/pytest -q` | 91 pruebas aprobadas en 22.25 s; suite completa ejecutada una vez al cierre |
| Pruebas nuevas de Fase 1 | 36, con PostgreSQL real en esquemas únicos de `habits_test` |
| `.venv/bin/ruff check .` | Sin errores |
| `.venv/bin/ruff format --check .` | 50 archivos con formato correcto |
| `.venv/bin/mypy` | Sin errores en 18 archivos de aplicación existentes |
| Inicialización desde base vacía | 18 tablas, 2 sucursales, 12 productos, ningún usuario inventado |
| Ampliación del core y repetición | Conserva datos/precios editados, sin duplicados ni nuevos eventos por repetir seed |
| Esquema parcial incompatible | Rechazado sin borrar su contenido |
| Aplicación a `habits` local | 18 tablas, 2 sucursales, 12 productos; segunda ejecución correcta |
| Conservación de la base local | Contenido de sucursales, usuarios y sesiones idéntico antes/después |
| EXPLAIN de agenda por sede/fecha | Utiliza `idx_reservas_sucursal_fecha` en la base local; no es un benchmark |

Los datos de pruebas son sintéticos y quedan dentro de esquemas temporales que
se eliminan al terminar cada prueba. La base de uso local recibió únicamente el
esquema y los datos iniciales autorizados: las sucursales y los doce productos.

## Cobertura de comportamiento

- Contactos, categorías, cantidades, relaciones únicas y referencias por sucursal.
- Reserva de noventa minutos, capacidad, coherencia de sede y exclusión de traslapes.
- Cancelación libera intervalo; llegada crea visita sin liberar los noventa minutos.
- Reserva completada y visita se validan juntas al COMMIT; visita futura rechazada.
- Visitas sin reserva y varias ventas por atención, sin duplicar frecuencia.
- Usuario, cliente, sucursal y mesa inactivos rechazados al registrar visita.
- Recetas compartidas, consumos futuros según receta actual, sin recalcular el pasado.
- FEFO, lotes vencidos excluidos, vencimiento de hoy utilizable y saldos no negativos.
- Producción consume ingredientes; vender terminados no los consume otra vez.
- Venta guarda precio histórico; falla en segunda línea revierte primera, saldos y bitácora.
- Triggers de auditoría INSERT/UPDATE/DELETE y rollback de los eventos junto con el cambio.
- Cinco reportes SQL: visitas reales, reservas por estado, ventas y stock actual por mes de vencimiento.
- Rol operativo sin DML de saldos/detalles ni lectura de hashes; procedimientos funcionan con ese rol.
- Dos conexiones: reservas simultáneas, última unidad vendida, reducción de capacidad y cambio de unidad.

## Ciclos TDD y errores corregidos

Se observaron fallos por tablas/objetos todavía inexistentes antes de implementar
catálogo, reservas/llegada, lotes/producción, ventas y reportes. Cada bloque se validó
antes de continuar; los tests usan interfaces SQL, no mocks de PostgreSQL.

La revisión detectó referencias inactivas admitidas por visitas: cuatro pruebas
fallaron primero y pasaron después de añadir controles de actividad y adscripción.
Se protegió también el ingrediente durante el alta de inventario para impedir una
carrera contra el cambio de unidad, comprobada con dos conexiones.

Se reprodujo `permission denied for table reservas` al COMMIT de una llegada bajo
el rol restringido en PostgreSQL 17. El trigger diferido se ejecutaba sin los
privilegios del procedimiento. Las funciones diferidas ahora usan SECURITY DEFINER,
search_path fijo y revocación de ejecución pública; llegada y cancelación confirman
sin conceder DML sobre reservas. La prueba de regresión forma parte de las 91.

## Revisión independiente

Se revisó el trabajo local contra el DER aprobado y los estándares del repositorio.
Se respetó la base histórica de revisión `5bb3939`; el trabajo anterior de auth se
usó como contexto. El alcance de cambios de esta entrega son SQL, tests y documentación.

### Standards

Sin infracciones documentadas. Se verificaron SQL parametrizado, identificadores
seguros, ausencia de secretos versionados, transacciones externas e instalación
no destructiva. Una sugerencia opcional fue nombrar las posiciones de la tupla de
IDs de las pruebas; no es un bloqueo y no justifica añadir clases o abstracciones.

### Spec

Tres hallazgos concretos corregidos: actividad/adscripción al registrar visitas,
cambio de unidad concurrente con inventario y privilegios de validaciones diferidas.
La revisión de cierre confirmó la corrección del último hallazgo; no quedaron
hallazgos bloqueantes abiertos en esa revisión.

## Respaldo, alcance y pendientes

Antes de ampliar `habits` se generó un respaldo privado con pg_dump en
`.local/backups/`, excluido de Git. También se comparó el contenido de las tres
tablas de datos existentes que debían conservarse; la bitácora creció por el catálogo.

La Fase 1 solicitada queda implementada y verificada. No hay bloqueo técnico abierto
para el esquema, los datos iniciales autorizados o los objetos SQL de esta entrega.
Las recetas operativas, recepciones físicas y datos de clientes se deben registrar
cuando existan: no se sustituyeron por existencias o ventas ficticias. La base no
promete vender productos sin receta o stock; los procedimientos lo rechazan.

Backend, UI, cambios de login, despliegue y publicación no forman parte de esta fase.
La integración futura deberá invocar los procedimientos con el usuario autenticado
y permisos SQL limitados, en lugar de modificar saldos o detalles directamente.

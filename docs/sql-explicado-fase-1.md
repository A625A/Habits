# SQL de clase aplicado al diseño de Habits

**Guía didáctica del diseño aprobado.** Los fragmentos explican los conceptos;
no ejecutarlos como una segunda migración. La implementación completa y verificada
está en `sql/fase1/` y se aplica con [estas instrucciones](implementacion-bd-fase-1.md).
Algunos ejemplos simplifican una regla para enseñarla; el SQL implementado incluye
las validaciones adicionales indicadas en el DER.

## Qué aporta cada concepto

| Concepto | Uso concreto | Cuándo |
|---|---|---|
| PK, FK, UNIQUE, CHECK | Identidad, relaciones y datos válidos | Implementación del esquema aprobado de Fase 1 |
| Índices | Buscar agenda, historial y lotes FEFO | Fase 1; verificar utilidad con EXPLAIN |
| Vistas | Stock disponible y totales calculados sin duplicar cantidades | Fase 1, sobre el esquema aprobado |
| CTE | Separar conteos antes de combinar resultados | Consultas SQL de validación/reportes |
| Funciones | Cálculo de alertas y validación reutilizable de reglas | Donde lo exijan las restricciones/consultas |
| Triggers | Auditoría y reglas entre tablas | Fase 1, sin duplicar descuentos de stock |
| Stored procedures | Centralizar una operación de negocio en la BD | Su contrato se diseña aquí; implementación se acuerda después |
| Transacciones | Confirmar todos los cambios o ninguno | Carga y pruebas de Fase 1; luego operaciones completas |

No se añade un concepto solo por nombrarlo: la función de auditoría ya existe;
una vista evita mantener un total; una transacción evita dejar una venta a medias.

## 1. PK, FK y CHECK: datos válidos desde PostgreSQL

Fragmentos del esquema propuesto:

```sql
CREATE TABLE receta_ingrediente (
    receta_ingrediente_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto_id BIGINT NOT NULL REFERENCES productos(producto_id) ON DELETE RESTRICT,
    ingrediente_id BIGINT NOT NULL REFERENCES ingredientes(ingrediente_id) ON DELETE RESTRICT,
    cantidad NUMERIC(14,3) NOT NULL CHECK (cantidad > 0),
    UNIQUE (producto_id, ingrediente_id)
);
```

La PK identifica una fila; las FK exigen producto e ingrediente existentes;
UNIQUE evita repetir el mismo ingrediente en la receta; CHECK rechaza cero/negativos.

La FK compuesta de reserva asegura que su mesa pertenece a su sucursal:

```sql
ALTER TABLE mesas
ADD CONSTRAINT uq_mesa_sucursal UNIQUE (mesa_id, sucursal_id);

ALTER TABLE reservas
ADD CONSTRAINT fk_reserva_mesa_sucursal
FOREIGN KEY (mesa_id, sucursal_id)
REFERENCES mesas (mesa_id, sucursal_id) ON DELETE RESTRICT;

ALTER TABLE reservas
ADD CONSTRAINT ck_reserva_duracion
CHECK (fecha_fin = fecha_inicio + INTERVAL '90 minutes');
```

Una FK a mesa y otra a sucursal, por separado, no comprueban que correspondan.
Para la visita, el vínculo compuesto incluye también cliente y una mesa no nula
cuando hay reserva. El diccionario del DER detalla esa nulabilidad.

## 2. Exclusión: evitar reservas simultáneas sobre la misma mesa

Se conserva la idea de Chris, usando fechas con zona e incluyendo completadas,
como aceptó Andrew. Registrar la llegada no libera el intervalo:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE reservas
ADD CONSTRAINT no_traslape_mesa
EXCLUDE USING gist (
    mesa_id WITH =,
    tstzrange(fecha_inicio, fecha_fin, '[)') WITH &&
)
WHERE (estado IN ('pendiente', 'confirmada', 'completada'));
```

`[)` incluye el inicio y excluye el fin: 10:00–11:30 y 11:30–13:00 no chocan.
Una cancelada no participa en la restricción. La exclusión resuelve el conflicto
también cuando dos conexiones intentan reservar al mismo tiempo.

Fuente: [rangos y exclusiones de PostgreSQL 17](https://www.postgresql.org/docs/17/rangetypes.html#RANGETYPES-CONSTRAINT).

## 3. Índice: encontrar primero el lote que vence antes

```sql
CREATE INDEX idx_lotes_fefo
ON lotes_ingrediente (inventario_id, fecha_vencimiento, lote_id)
WHERE cantidad_disponible > 0;
```

Este índice acompaña el filtro por inventario y el orden de consumo. No contiene
CURRENT_DATE en su condición: un índice no debe depender de que pase el día para
decidir si una fila pertenece a él. La consulta aplica el filtro temporal:

```sql
SELECT lote_id, cantidad_disponible
FROM lotes_ingrediente
WHERE inventario_id = :inventario_id
  AND cantidad_disponible > 0
  AND fecha_vencimiento >=
      (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date
ORDER BY fecha_vencimiento, lote_id
FOR UPDATE;
```

`:inventario_id` representa una variable de psql previamente definida; en Python
se usarán parámetros psycopg. El SELECT se ejecutará dentro de la transacción de
consumo. FOR UPDATE bloquea los lotes seleccionados mientras se usan. Al consumir
varios ingredientes se tomará un orden común de bloqueo para evitar conflictos.
Este fragmento selecciona lotes: todavía no implementa el descuento de una receta.

## 4. Vista: calcular existencias sin mantener otro saldo

```sql
CREATE VIEW v_stock_ingredientes AS
SELECT i.inventario_id,
       i.sucursal_id,
       i.ingrediente_id,
       i.cantidad_referencia,
       COALESCE(
           SUM(l.cantidad_disponible) FILTER (
               WHERE l.fecha_vencimiento >=
                   (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date
           ),
           0
       ) AS cantidad_disponible
FROM inventario_ingrediente i
LEFT JOIN lotes_ingrediente l USING (inventario_id)
GROUP BY i.inventario_id, i.sucursal_id,
         i.ingrediente_id, i.cantidad_referencia;
```

La vista incluye inventarios sin lotes como cero. Excluye vencidos del saldo
utilizable, pero no borra esos lotes. Una vista normal calcula el resultado al
consultarla; no es otra tabla de saldos que debamos actualizar.

## 5. Función: expresar la regla aceptada del 15 %

```sql
CREATE FUNCTION stock_bajo(actual NUMERIC, referencia NUMERIC)
RETURNS BOOLEAN
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT actual <= referencia * 0.15;
$$;

SELECT stock_bajo(15, 100);  -- true

SELECT inventario_id, cantidad_disponible, cantidad_referencia
FROM v_stock_ingredientes
WHERE stock_bajo(cantidad_disponible, cantidad_referencia);
```

La referencia positiva se garantiza en su tabla. La función devuelve un valor;
no modifica inventario. IMMUTABLE corresponde porque depende solo de sus argumentos.
La misma regla puede usarse en consulta de alertas y reporte mensual.

## 6. CTE: contar visitas antes de incorporar otros datos

```sql
WITH frecuencia AS (
    SELECT cliente_id, COUNT(*) AS visitas
    FROM visitas
    WHERE atendida_en >= :'desde'::timestamptz
      AND atendida_en < :'hasta'::timestamptz
    GROUP BY cliente_id
)
SELECT c.cliente_id, c.nombre, f.visitas
FROM frecuencia f
JOIN clientes c USING (cliente_id)
ORDER BY f.visitas DESC, c.cliente_id
LIMIT 10;
```

`desde` y `hasta` son variables psql con fechas y zona, previamente definidas.
Una CTE nombra un resultado intermedio. Aquí contamos visitas, no ventas ni reservas:
si una visita tiene tres compras, sigue contando una vez. La comparación de sucursales
usará CTE independientes para reservas y ventas antes de unirlas por sede.
Una reserva confirmada sin llegada no tiene una visita creada y no aparece en este
ranking. La operación de llegada registrará la hora real de la atención, no una
fecha futura tomada de la reserva.

## 7. Triggers: auditar y validar lo que un CHECK no puede

El trigger de auditoría existente se puede conectar a las nuevas tablas:

```sql
CREATE TRIGGER auditar_lotes_ingrediente
AFTER INSERT OR UPDATE OR DELETE ON lotes_ingrediente
FOR EACH ROW EXECUTE FUNCTION auditar_cambio(
    'lote_id', 'lote_id', 'inventario_id',
    'fecha_vencimiento', 'cantidad_inicial', 'cantidad_disponible'
);
```

El primer argumento indica la PK; los demás son los campos permitidos en la bitácora.
El evento y el cambio se confirman o revierten juntos. La capacidad de una mesa
requiere consultar otra tabla; no se resuelve con CHECK(personas <= capacidad):

```sql
CREATE FUNCTION validar_capacidad_reserva()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    capacidad_mesa INTEGER;
BEGIN
    SELECT capacidad INTO capacidad_mesa
    FROM mesas
    WHERE mesa_id = NEW.mesa_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'La mesa no existe';
    END IF;
    IF NEW.personas > capacidad_mesa THEN
        RAISE EXCEPTION 'La mesa no tiene capacidad suficiente';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER comprobar_capacidad_reserva
BEFORE INSERT OR UPDATE OF mesa_id, personas ON reservas
FOR EACH ROW EXECUTE FUNCTION validar_capacidad_reserva();
```

Este ejemplo ilustra el control al insertar/cambiar una reserva. Falta implementar
la validación inversa al reducir capacidad y las reglas de estados/actividad del DER;
no debe presentarse como implementación completa de reservas. El CHECK de una fila
no es el lugar para garantizar reglas que dependen de otras filas/tablas.
Fuente: [restricciones en PostgreSQL 17](https://www.postgresql.org/docs/17/ddl-constraints.html).

## 8. Stored procedure y transacción: una operación coherente

Ejemplo corto de una operación centralizada: cancelar una reserva solo si su estado
lo permite. No borra la reserva; el trigger de auditoría registra la actualización.

```sql
CREATE PROCEDURE cancelar_reserva(p_reserva_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE reservas
    SET estado = 'cancelada'
    WHERE reserva_id = p_reserva_id
      AND estado IN ('pendiente', 'confirmada');

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Reserva inexistente o no cancelable';
    END IF;
END;
$$;

BEGIN;
CALL cancelar_reserva(:reserva_id);
COMMIT;
```

`:reserva_id` representa una reserva real de prueba en psql; no un ID inventado.
La autorización del operador y el actor de auditoría se establecerán al integrar
la operación: este ejemplo explica la regla de cancelación, no implementa permisos.

Una función devuelve un resultado; un procedimiento se invoca con CALL y expresa
una operación. Usaremos una sola transacción exterior: los procedimientos de venta
y producción no harán COMMIT por ingrediente o por detalle. Si ocurre una excepción,
no se confirma ninguna parte; la conexión debe ejecutar ROLLBACK antes de continuar.

En venta/producción, el flujo SQL futuro será: validar datos → bloquear existencias
→ comprobar cantidades/vencimientos → descontar → guardar operación completa.
La auditoría participa en esa misma transacción. El dueño SQL y los permisos de
escritura de los procedimientos se definirán antes de considerarlos una interfaz
de operación; no se asume que una función por sí sola impida escrituras directas.

Fuentes: [CREATE PROCEDURE](https://www.postgresql.org/docs/17/sql-createprocedure.html)
y [transacciones en PL/pgSQL](https://www.postgresql.org/docs/17/plpgsql-transactions.html).

## Evidencia de implementación

Las dos rondas y el DER fueron aprobados. Los resultados de PostgreSQL real se
registran en [verificacion-bd-fase-1.md](verificacion-bd-fase-1.md). Los fragmentos
anteriores son material didáctico; el instalador es `sql/fase1/inicializar.sql`.

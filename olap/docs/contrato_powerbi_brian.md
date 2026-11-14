# Contrato Power BI para Brian

Conectar Power BI a PostgreSQL y seleccionar **`dm.v_ventas_detalle` como fuente
principal**. Tiene una fila por producto dentro de un ticket. Los datos estarán
vacíos hasta que Rodrigo complete y valide el ETL. Moneda GTQ; período noviembre
2025 a octubre 2026. Preparación de la conexión, medidas y dashboard corresponde
al equipo; Andrew no entrega un archivo PBIX.

| Vista | Campos |
|---|---|
| `v_ventas_detalle` | `detalle_id`, `ticket_id`, `fecha`, `dia`, `mes`, `trimestre`, `anio`, `producto_id`, `codigo_producto`, `producto`, `categoria`, `sucursal_id`, `codigo_sucursal`, `sucursal`, `tipo_venta`, `cantidad`, `precio_unitario`, `importe` |
| `v_ventas_mensuales` | `mes_inicio`, `anio`, `mes`, `sucursal_id`, `codigo_sucursal`, `sucursal`, `tipo_venta`, `ingresos`, `tickets`, `unidades`, `ticket_promedio` |
| `v_productos` | `producto_id`, `codigo_producto`, `producto`, `categoria`, `ingresos`, `tickets`, `unidades`, `ticket_promedio` |
| `v_sucursales` | `sucursal_id`, `codigo_sucursal`, `sucursal`, `ingresos`, `tickets`, `unidades`, `ticket_promedio` |

Los últimos tres campos de medidas adicionales en cada agregado son siempre
`tickets`, `unidades`, `ticket_promedio`, además de `ingresos`. La vista mensual
agrupa mes + sucursal + tipo. Productos y sucursales son acumulados de todo el
período; **no responden por sí solos a filtros de fecha o categoría ajenos a su grano**.
Usarlos para verificar resultados. No unir ni anexar agregados a la tabla de detalle;
eso duplicaría ingresos. No crear relaciones muchos a muchos entre estas vistas.

## KPIs y filtros

Sobre `v_ventas_detalle`: ingresos = SUM(importe); unidades = SUM(cantidad);
tickets = DISTINCTCOUNT(ticket_id); ticket promedio = ingresos / tickets,
con división segura y vacío cuando no hay tickets. No sumar precio_unitario ni
contar filas como tickets. Si el conector importa BIGINT como número decimal,
convertir los IDs a texto antes de cualquier pérdida de precisión; no son medidas.

Filtrar `fecha` como Date, `sucursal`/`codigo_sucursal`, `categoria` y `tipo_venta`.
Ordenar meses por fecha o año/mes, no solo por nombre/número de mes. Para mostrar
meses sin ventas, Brian puede crear un calendario 2025-11-01 a 2026-10-31 con
relación 1:N hacia `fecha` de detalle y mostrar categorías sin datos.

Cada ticket puede aparecer en varios productos/categorías: sumar sus conteos
parciales duplica compras. Power BI debe recalcular DISTINCTCOUNT en el contexto
actual. Al filtrar una categoría, su ticket promedio es el ingreso **de esa
categoría** dividido entre tickets que la compraron. El promedio total se calcula
con ingresos totales / tickets distintos; no con AVG de promedios por fila.

## SQL para comparar con Power BI

Sustituir filtros por los mismos que utiliza el visual. `desde` es inclusivo y
`hasta` exclusivo; al parametrizar desde código, usar parámetros del controlador.

```sql
SELECT SUM(importe) AS ingresos, COUNT(DISTINCT ticket_id) AS tickets,
       SUM(cantidad) AS unidades,
       SUM(importe)/NULLIF(COUNT(DISTINCT ticket_id),0) AS ticket_promedio
FROM dm.v_ventas_detalle
WHERE fecha >= DATE '2025-11-01' AND fecha < DATE '2026-11-01';

-- Ejemplo con fecha, sucursal y categoría: aplicar esos mismos filtros en el visual.
SELECT SUM(importe) AS ingresos, COUNT(DISTINCT ticket_id) AS tickets,
       SUM(cantidad) AS unidades,
       SUM(importe)/NULLIF(COUNT(DISTINCT ticket_id),0) AS ticket_promedio
FROM dm.v_ventas_detalle
WHERE fecha >= DATE '2025-11-01' AND fecha < DATE '2025-12-01'
  AND codigo_sucursal='DEMO-01' AND categoria='bebida';

SELECT mes_inicio,SUM(ingresos) AS ingresos,SUM(tickets) AS tickets,
       SUM(unidades) AS unidades,
       SUM(ingresos)/NULLIF(SUM(tickets),0) AS ticket_promedio
FROM dm.v_ventas_mensuales GROUP BY mes_inicio ORDER BY mes_inicio;

SELECT producto,categoria,SUM(cantidad) AS unidades,SUM(importe) AS ingresos
FROM dm.v_ventas_detalle GROUP BY producto,categoria
ORDER BY unidades DESC,producto;

SELECT sucursal,tipo_venta,SUM(importe) AS ingresos,
       COUNT(DISTINCT ticket_id) AS tickets,SUM(cantidad) AS unidades
FROM dm.v_ventas_detalle GROUP BY sucursal,tipo_venta ORDER BY sucursal,tipo_venta;
```

Los tickets de la vista mensual sí se pueden sumar entre sus grupos después de
validar que cada ticket tiene una sola fecha, sucursal y tipo. No sumar tickets de
`v_productos` ni promediar `ticket_promedio` de ninguna vista.

La cuenta lectora necesita CONNECT a la base, USAGE en `dm` y SELECT en sus cuatro
vistas; no necesita escritura ni acceso a tablas de Proyecto 2. La guía incluye
los GRANT opcionales, sin contraseñas en archivos. En modo Import, actualizar
Power BI después del ETL; las vistas normales no requieren REFRESH en PostgreSQL.

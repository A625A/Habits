"""Consultas de lotes y alertas usando existencias calculadas por PostgreSQL."""

from typing import Any

from app.db import get_db


def alerts(sucursal_id: int | None, days: int) -> dict[str, Any]:
    db = get_db()
    scope = (sucursal_id, sucursal_id)
    low = db.execute(
        """SELECT s.*,i.nombre,i.unidad FROM v_stock_ingredientes s
        JOIN ingredientes i USING(ingrediente_id)
        WHERE (%s::bigint IS NULL OR sucursal_id=%s)
        AND stock_bajo(cantidad_disponible,cantidad_referencia) ORDER BY inventario_id""",
        scope,
    ).fetchall()
    ingredients = db.execute(
        """SELECT l.*,i.sucursal_id,i.ingrediente_id,
        l.fecha_vencimiento < (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date AS vencido
        FROM lotes_ingrediente l JOIN inventario_ingrediente i USING(inventario_id)
        WHERE (%s::bigint IS NULL OR sucursal_id=%s) AND l.cantidad_disponible>0
        AND fecha_vencimiento <= (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date + %s
        ORDER BY fecha_vencimiento,lote_id""",
        (*scope, days),
    ).fetchall()
    finished = db.execute(
        """SELECT *,fecha_vencimiento <
        (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date AS vencido FROM producciones
        WHERE (%s::bigint IS NULL OR sucursal_id=%s) AND cantidad_disponible>0
        AND fecha_vencimiento <= (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date + %s
        ORDER BY fecha_vencimiento,produccion_id""",
        (*scope, days),
    ).fetchall()
    return {
        "stock_bajo": low,
        "ingredientes_por_vencer": [r for r in ingredients if not r["vencido"]],
        "ingredientes_vencidos": [r for r in ingredients if r["vencido"]],
        "terminados_por_vencer": [r for r in finished if not r["vencido"]],
        "terminados_vencidos": [r for r in finished if r["vencido"]],
    }

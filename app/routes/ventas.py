"""Ventas confirmadas y precios históricos mediante registrar_venta."""

from typing import Any

from flask import abort, g, request
from psycopg.types.json import Jsonb

from app.api import (
    blueprint,
    body,
    branch,
    endpoint,
    identifier,
    instant,
    integer,
    optional_id,
    pagination,
    query_id,
    text,
)
from app.db import get_db
from app.services.operaciones import one

bp = blueprint("ventas", "/ventas")


def sale_detail(venta_id: int) -> dict[str, Any]:
    result = one(
        """SELECT v.*,t.total,t.unidades FROM ventas v
        JOIN v_totales_ventas t USING(venta_id) WHERE venta_id=%s""",
        (venta_id,),
    )
    branch(result["sucursal_id"])
    result["lineas"] = (
        get_db()
        .execute(
            """SELECT d.*,p.nombre FROM detalle_ventas d
        JOIN productos p USING(producto_id) WHERE venta_id=%s ORDER BY producto_id""",
            (venta_id,),
        )
        .fetchall()
    )
    return result


@bp.get("", strict_slashes=False)
@endpoint()
def index() -> dict[str, Any]:
    sede, visit = branch(query_id("sucursal_id")), query_id("visita_id")
    since = instant(request.args["desde"]) if "desde" in request.args else None
    until = instant(request.args["hasta"]) if "hasta" in request.args else None
    if since is not None and until is not None and since >= until:
        abort(400, description="desde debe ser anterior a hasta.")
    return {
        "ventas": get_db()
        .execute(
            """SELECT v.*,t.total,t.unidades FROM ventas v
        JOIN v_totales_ventas t USING(venta_id)
        WHERE (%s::bigint IS NULL OR v.sucursal_id=%s) AND (%s::bigint IS NULL OR v.visita_id=%s)
        AND (%s::timestamptz IS NULL OR v.fecha>=%s) AND (%s::timestamptz IS NULL OR v.fecha<%s)
        ORDER BY v.fecha DESC,venta_id DESC LIMIT %s OFFSET %s""",
            (sede, sede, visit, visit, since, since, until, until, *pagination()),
        )
        .fetchall()
    }


@bp.get("/<int:venta_id>")
@endpoint()
def detail(venta_id: int) -> dict[str, Any]:
    return sale_detail(venta_id)


def sale_lines(value: Any) -> list[dict[str, int]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 200:
        abort(400, description="Se requiere una lista de 1 a 200 productos.")
    result = []
    for row in value:
        if not isinstance(row, dict) or row.keys() != {"producto_id", "cantidad"}:
            abort(400, description="Cada línea requiere producto_id y cantidad, sin precio manual.")
        result.append(
            {"producto_id": identifier(row["producto_id"]), "cantidad": integer(row["cantidad"])}
        )
    return result


@bp.post("", strict_slashes=False)
@endpoint()
def create() -> tuple[dict[str, Any], int]:
    data = body(
        {
            "sucursal_id": identifier,
            "tipo": text,
            "visita_id": optional_id,
            "mesa_id": optional_id,
            "lineas": sale_lines,
        },
        {"sucursal_id", "tipo", "lineas"},
    )
    branch(data["sucursal_id"])
    result = one(
        "CALL registrar_venta(%s,%s,%s,%s,%s,%s,NULL)",
        (
            data["sucursal_id"],
            g.user["usuario_id"],
            data["tipo"],
            data.get("visita_id"),
            data.get("mesa_id"),
            Jsonb(data["lineas"]),
        ),
    )
    return sale_detail(result["p_venta"]), 201

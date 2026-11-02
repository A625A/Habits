"""Producción transaccional mediante el procedimiento aprobado de Fase 1."""

from typing import Any

from flask import g

from app.api import (
    blueprint,
    body,
    branch,
    day,
    endpoint,
    identifier,
    integer,
    pagination,
    query_id,
)
from app.db import get_db
from app.services.operaciones import one

bp = blueprint("producciones", "/producciones")


@bp.get("", strict_slashes=False)
@endpoint("administrador", "gerente")
def index() -> dict[str, Any]:
    sede = branch(query_id("sucursal_id"))
    product = query_id("producto_id")
    return {
        "producciones": get_db()
        .execute(
            """SELECT * FROM producciones
        WHERE (%s::bigint IS NULL OR sucursal_id=%s) AND (%s::bigint IS NULL OR producto_id=%s)
        ORDER BY producida_en DESC,produccion_id DESC LIMIT %s OFFSET %s""",
            (sede, sede, product, product, *pagination()),
        )
        .fetchall()
    }


@bp.get("/<int:produccion_id>")
@endpoint("administrador", "gerente")
def detail(produccion_id: int) -> dict[str, Any]:
    result = one("SELECT * FROM producciones WHERE produccion_id=%s", (produccion_id,))
    branch(result["sucursal_id"])
    return result


@bp.post("", strict_slashes=False)
@endpoint("administrador", "gerente")
def create() -> tuple[dict[str, Any], int]:
    fields = {
        "sucursal_id": identifier,
        "producto_id": identifier,
        "cantidad": integer,
        "fecha_vencimiento": day,
    }
    data = body(fields, set(fields))
    branch(data["sucursal_id"])
    result = one(
        "CALL registrar_produccion(%s,%s,%s,%s,%s,NULL)",
        (
            data["sucursal_id"],
            data["producto_id"],
            g.user["usuario_id"],
            data["cantidad"],
            data["fecha_vencimiento"],
        ),
    )
    return one("SELECT * FROM producciones WHERE produccion_id=%s", (result["p_produccion"],)), 201

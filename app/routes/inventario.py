"""Recepciones y consulta de existencias; no expone edición de saldos."""

from typing import Any

from flask import abort, g, request

from app.api import (
    blueprint,
    body,
    branch,
    day,
    decimal,
    endpoint,
    identifier,
    pagination,
    query_id,
)
from app.db import get_db
from app.services.inventario import alerts
from app.services.operaciones import insert, one, update

bp = blueprint("inventario", "/inventario")


@bp.get("/existencias")
@endpoint("administrador", "gerente")
def stock() -> dict[str, Any]:
    sede = branch(query_id("sucursal_id"))
    return {
        "ingredientes": get_db()
        .execute(
            """SELECT s.*,i.nombre,i.unidad,
        stock_bajo(cantidad_disponible,cantidad_referencia) AS stock_bajo
        FROM v_stock_ingredientes s JOIN ingredientes i USING(ingrediente_id)
        WHERE (%s::bigint IS NULL OR sucursal_id=%s)
        ORDER BY inventario_id LIMIT %s OFFSET %s""",
            (sede, sede, *pagination()),
        )
        .fetchall()
    }


@bp.get("/terminados")
@endpoint()
def finished_stock() -> dict[str, Any]:
    sede = branch(query_id("sucursal_id"))
    return {
        "terminados": get_db()
        .execute(
            """SELECT * FROM v_stock_terminados
        WHERE (%s::bigint IS NULL OR sucursal_id=%s)
        ORDER BY sucursal_id,producto_id LIMIT %s OFFSET %s""",
            (sede, sede, *pagination()),
        )
        .fetchall()
    }


@bp.post("/configuraciones")
@endpoint("administrador", "gerente")
def configure() -> tuple[dict[str, Any], int]:
    fields = {
        "sucursal_id": identifier,
        "ingrediente_id": identifier,
        "cantidad_referencia": decimal,
    }
    data = body(fields, set(fields))
    branch(data["sucursal_id"])
    return insert("inventario_ingrediente", data), 201


@bp.patch("/configuraciones/<int:inventario_id>")
@endpoint("administrador", "gerente")
def edit_config(inventario_id: int) -> dict[str, Any]:
    existing = one(
        "SELECT sucursal_id FROM inventario_ingrediente WHERE inventario_id=%s", (inventario_id,)
    )
    branch(existing["sucursal_id"])
    return update(
        "inventario_ingrediente",
        "inventario_id",
        inventario_id,
        body({"cantidad_referencia": decimal}, {"cantidad_referencia"}),
    )


@bp.post("/recepciones")
@endpoint("administrador", "gerente")
def receive() -> tuple[dict[str, Any], int]:
    fields = {"inventario_id": identifier, "cantidad": decimal, "fecha_vencimiento": day}
    data = body(fields, set(fields))
    existing = one(
        "SELECT sucursal_id FROM inventario_ingrediente WHERE inventario_id=%s",
        (data["inventario_id"],),
    )
    branch(existing["sucursal_id"])
    result = one(
        "CALL registrar_recepcion(%s,%s,%s,%s,NULL)",
        (data["inventario_id"], g.user["usuario_id"], data["cantidad"], data["fecha_vencimiento"]),
    )
    return one("SELECT * FROM lotes_ingrediente WHERE lote_id=%s", (result["p_lote"],)), 201


@bp.get("/lotes")
@endpoint("administrador", "gerente")
def lots() -> dict[str, Any]:
    sede, inventory = branch(query_id("sucursal_id")), query_id("inventario_id")
    return {
        "lotes": get_db()
        .execute(
            """SELECT l.*,i.sucursal_id,i.ingrediente_id
        FROM lotes_ingrediente l JOIN inventario_ingrediente i USING(inventario_id)
        WHERE (%s::bigint IS NULL OR sucursal_id=%s)
        AND (%s::bigint IS NULL OR inventario_id=%s)
        ORDER BY fecha_vencimiento,lote_id LIMIT %s OFFSET %s""",
            (sede, sede, inventory, inventory, *pagination()),
        )
        .fetchall()
    }


@bp.get("/alertas")
@endpoint("administrador", "gerente")
def stock_alerts() -> dict[str, Any]:
    raw = request.args.get("dias", "7")
    if len(raw) > 3 or not raw.isascii() or not raw.isdigit() or not 0 <= int(raw) <= 365:
        abort(400, description="dias debe estar entre 0 y 365.")
    return alerts(branch(query_id("sucursal_id")), int(raw))

"""Mesas y visitas reales, incluidas atenciones sin reserva."""

from typing import Any

from flask import g

from app.api import (
    blueprint,
    body,
    boolean,
    branch,
    endpoint,
    identifier,
    integer,
    optional_id,
    pagination,
    query_id,
    text,
)
from app.db import get_db
from app.services.operaciones import insert, one, update

bp = blueprint("atencion", "")
TABLE_FIELDS = {
    "sucursal_id": identifier,
    "numero_mesa": integer,
    "capacidad": integer,
    "activa": boolean,
}


@bp.get("/sucursales")
@endpoint()
def branches() -> dict[str, Any]:
    sede = branch()
    return {
        "sucursales": get_db()
        .execute(
            """SELECT sucursal_id,codigo,nombre,activa
        FROM sucursales WHERE (%s::bigint IS NULL OR sucursal_id=%s) ORDER BY codigo""",
            (sede, sede),
        )
        .fetchall()
    }


@bp.get("/mesas")
@endpoint()
def tables() -> dict[str, Any]:
    sede = branch(query_id("sucursal_id"))
    return {
        "mesas": get_db()
        .execute(
            """SELECT * FROM mesas
        WHERE (%s::bigint IS NULL OR sucursal_id=%s) ORDER BY sucursal_id,numero_mesa
        LIMIT %s OFFSET %s""",
            (sede, sede, *pagination()),
        )
        .fetchall()
    }


@bp.post("/mesas")
@endpoint("administrador", "gerente")
def create_table() -> tuple[dict[str, Any], int]:
    data = body(TABLE_FIELDS, {"sucursal_id", "numero_mesa", "capacidad"})
    branch(data["sucursal_id"])
    return insert("mesas", data), 201


@bp.patch("/mesas/<int:mesa_id>")
@endpoint("administrador", "gerente")
def edit_table(mesa_id: int) -> dict[str, Any]:
    existing = one("SELECT sucursal_id FROM mesas WHERE mesa_id=%s FOR UPDATE", (mesa_id,))
    branch(existing["sucursal_id"])
    data = body({key: value for key, value in TABLE_FIELDS.items() if key != "sucursal_id"})
    return update("mesas", "mesa_id", mesa_id, data)


@bp.get("/visitas")
@endpoint()
def visits() -> dict[str, Any]:
    sede, customer = branch(query_id("sucursal_id")), query_id("cliente_id")
    return {
        "visitas": get_db()
        .execute(
            """SELECT * FROM visitas
        WHERE (%s::bigint IS NULL OR sucursal_id=%s) AND (%s::bigint IS NULL OR cliente_id=%s)
        ORDER BY atendida_en DESC,visita_id DESC LIMIT %s OFFSET %s""",
            (sede, sede, customer, customer, *pagination()),
        )
        .fetchall()
    }


@bp.get("/visitas/<int:visita_id>")
@endpoint()
def visit(visita_id: int) -> dict[str, Any]:
    row = one("SELECT * FROM visitas WHERE visita_id=%s", (visita_id,))
    branch(row["sucursal_id"])
    return row


@bp.post("/visitas")
@endpoint()
def create_visit() -> tuple[dict[str, Any], int]:
    data = body(
        {"sucursal_id": identifier, "cliente_id": identifier, "mesa_id": optional_id, "tipo": text},
        {"sucursal_id", "cliente_id", "tipo"},
    )
    branch(data["sucursal_id"])
    return insert("visitas", {**data, "usuario_id": g.user["usuario_id"]}), 201

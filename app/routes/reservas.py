"""Agenda JSON adaptada de Chris (f27bb8e); PostgreSQL controla la integridad."""

from typing import Any

from flask import abort, g, request

from app.api import (
    blueprint,
    body,
    branch,
    day,
    endpoint,
    identifier,
    instant,
    integer,
    pagination,
    query_id,
)
from app.db import get_db
from app.services.operaciones import one

bp = blueprint("reservas", "/reservas")


@bp.get("", strict_slashes=False)
@endpoint()
def index() -> dict[str, Any]:
    sede = branch(query_id("sucursal_id"))
    customer, table = query_id("cliente_id"), query_id("mesa_id")
    date_filter = day(request.args["fecha"]) if "fecha" in request.args else None
    state = request.args.get("estado")
    if state not in {None, "pendiente", "confirmada", "completada", "cancelada"}:
        abort(400, description="Estado de reserva inválido.")
    return {
        "reservas": get_db()
        .execute(
            """SELECT r.*,s.nombre AS sucursal,
        m.numero_mesa,c.nombre AS cliente FROM reservas r
        JOIN sucursales s USING(sucursal_id) JOIN mesas m USING(mesa_id,sucursal_id)
        JOIN clientes c USING(cliente_id)
        WHERE (%s::bigint IS NULL OR r.sucursal_id=%s)
        AND (%s::date IS NULL OR (fecha_inicio AT TIME ZONE 'America/Guatemala')::date=%s)
        AND (%s::text IS NULL OR estado=%s) AND (%s::bigint IS NULL OR cliente_id=%s)
        AND (%s::bigint IS NULL OR mesa_id=%s)
        ORDER BY fecha_inicio DESC,reserva_id DESC LIMIT %s OFFSET %s""",
            (
                sede,
                sede,
                date_filter,
                date_filter,
                state,
                state,
                customer,
                customer,
                table,
                table,
                *pagination(),
            ),
        )
        .fetchall()
    }


@bp.post("", strict_slashes=False)
@endpoint()
def create() -> tuple[dict[str, Any], int]:
    fields = {
        "sucursal_id": identifier,
        "mesa_id": identifier,
        "cliente_id": identifier,
        "fecha_inicio": instant,
        "personas": integer,
    }
    data = body(fields, set(fields))
    branch(data["sucursal_id"])
    return one(
        """INSERT INTO reservas(sucursal_id,mesa_id,cliente_id,fecha_inicio,fecha_fin,personas,estado)
        VALUES (%s,%s,%s,%s,%s + interval '90 minutes',%s,'confirmada') RETURNING *""",
        (
            data["sucursal_id"],
            data["mesa_id"],
            data["cliente_id"],
            data["fecha_inicio"],
            data["fecha_inicio"],
            data["personas"],
        ),
    ), 201


def get_reservation(reserva_id: int) -> dict[str, Any]:
    row = one("SELECT * FROM reservas WHERE reserva_id=%s FOR UPDATE", (reserva_id,))
    branch(row["sucursal_id"])
    return row


@bp.get("/<int:reserva_id>")
@endpoint()
def detail(reserva_id: int) -> dict[str, Any]:
    return get_reservation(reserva_id)


@bp.post("/<int:reserva_id>/confirmar")
@endpoint()
def confirm(reserva_id: int) -> dict[str, Any]:
    get_reservation(reserva_id)
    return one(
        "UPDATE reservas SET estado='confirmada' WHERE reserva_id=%s RETURNING *", (reserva_id,)
    )


@bp.post("/<int:reserva_id>/cancelar")
@endpoint()
def cancel(reserva_id: int) -> dict[str, Any]:
    get_reservation(reserva_id)
    get_db().execute("CALL cancelar_reserva(%s)", (reserva_id,))
    return one("SELECT * FROM reservas WHERE reserva_id=%s", (reserva_id,))


@bp.post("/<int:reserva_id>/llegada")
@endpoint()
def arrive(reserva_id: int) -> tuple[dict[str, Any], int]:
    get_reservation(reserva_id)
    result = one("CALL registrar_llegada(%s,%s,NULL)", (reserva_id, g.user["usuario_id"]))
    return one("SELECT * FROM visitas WHERE visita_id=%s", (result["p_visita"],)), 201

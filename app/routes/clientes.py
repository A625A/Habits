"""Clientes compartidos; historial operativo limitado a la sede autorizada.

Adapta la búsqueda y consultas de historial de Chris (f27bb8e) al contrato JSON.
"""

from typing import Any

from flask import abort, g, request

from app.api import (
    blueprint,
    body,
    boolean,
    branch,
    endpoint,
    nullable_text,
    optional_id,
    pagination,
    text,
)
from app.db import get_db
from app.services.operaciones import insert, one, update

bp = blueprint("clientes", "/clientes")
FIELDS = {"nombre": text, "telefono": nullable_text, "email": nullable_text, "activo": boolean}


@bp.get("", strict_slashes=False)
@endpoint()
def index() -> dict[str, Any]:
    query = "%" + request.args.get("q", "").strip() + "%"
    active = request.args.get("activo")
    if active not in {None, "true", "false"}:
        abort(400, description="activo debe ser true o false.")
    rows = (
        get_db()
        .execute(
            """SELECT * FROM clientes WHERE (nombre ILIKE %s OR email ILIKE %s OR telefono ILIKE %s)
        AND (%s::boolean IS NULL OR activo=%s) ORDER BY nombre,cliente_id LIMIT %s OFFSET %s""",
            (
                query,
                query,
                query,
                None if active is None else active == "true",
                None if active is None else active == "true",
                *pagination(),
            ),
        )
        .fetchall()
    )
    return {"clientes": rows}


@bp.post("", strict_slashes=False)
@endpoint()
def create() -> tuple[dict[str, Any], int]:
    return insert("clientes", body(FIELDS, {"nombre"})), 201


@bp.get("/<int:cliente_id>")
@endpoint()
def detail(cliente_id: int) -> dict[str, Any]:
    return one("SELECT * FROM clientes WHERE cliente_id=%s", (cliente_id,))


@bp.patch("/<int:cliente_id>")
@endpoint()
def edit(cliente_id: int) -> dict[str, Any]:
    return update("clientes", "cliente_id", cliente_id, body(FIELDS))


@bp.get("/<int:cliente_id>/historial")
@endpoint()
def history(cliente_id: int) -> dict[str, Any]:
    one("SELECT cliente_id FROM clientes WHERE cliente_id=%s", (cliente_id,))
    sede = branch()
    params = (cliente_id, sede, sede, *pagination())
    db = get_db()
    return {
        "reservas": db.execute(
            """SELECT r.*,s.nombre AS sucursal,m.numero_mesa FROM reservas r
            JOIN sucursales s USING(sucursal_id) JOIN mesas m USING(mesa_id,sucursal_id)
            WHERE cliente_id=%s AND (%s::bigint IS NULL OR r.sucursal_id=%s)
            ORDER BY fecha_inicio DESC,reserva_id DESC LIMIT %s OFFSET %s""",
            params,
        ).fetchall(),
        "visitas": db.execute(
            """SELECT * FROM visitas WHERE cliente_id=%s
            AND (%s::bigint IS NULL OR sucursal_id=%s)
            ORDER BY atendida_en DESC,visita_id DESC LIMIT %s OFFSET %s""",
            params,
        ).fetchall(),
        "compras": db.execute(
            """SELECT t.*,v.tipo FROM v_totales_ventas t
            JOIN ventas v USING(venta_id) JOIN visitas a ON a.visita_id=v.visita_id
            WHERE a.cliente_id=%s AND (%s::bigint IS NULL OR v.sucursal_id=%s)
            ORDER BY t.fecha DESC,t.venta_id DESC LIMIT %s OFFSET %s""",
            params,
        ).fetchall(),
    }


def customer_exists(cliente_id: int, active: bool = False) -> None:
    row = one("SELECT activo FROM clientes WHERE cliente_id=%s FOR SHARE", (cliente_id,))
    if active and not row["activo"]:
        abort(409, description="Cliente inactivo.")


@bp.get("/<int:cliente_id>/preferencias")
@endpoint()
def preferences(cliente_id: int) -> dict[str, Any]:
    customer_exists(cliente_id)
    return {
        "preferencias": get_db()
        .execute(
            """SELECT p.*,c.nombre AS producto
        FROM preferencias_cliente p JOIN productos c USING(producto_id)
        WHERE cliente_id=%s ORDER BY preferencia_id LIMIT %s OFFSET %s""",
            (cliente_id, *pagination()),
        )
        .fetchall()
    }


@bp.put("/<int:cliente_id>/preferencias/<int:producto_id>")
@endpoint()
def set_preference(cliente_id: int, producto_id: int) -> dict[str, Any]:
    customer_exists(cliente_id, active=True)
    data = body({"nota_preferencia": nullable_text}, {"nota_preferencia"})
    return one(
        """INSERT INTO preferencias_cliente(cliente_id,producto_id,nota_preferencia)
        VALUES (%s,%s,%s) ON CONFLICT (cliente_id,producto_id)
        DO UPDATE SET nota_preferencia=EXCLUDED.nota_preferencia RETURNING *""",
        (cliente_id, producto_id, data["nota_preferencia"]),
    )


@bp.delete("/<int:cliente_id>/preferencias/<int:producto_id>")
@endpoint()
def delete_preference(cliente_id: int, producto_id: int) -> dict[str, Any]:
    return one(
        """DELETE FROM preferencias_cliente WHERE cliente_id=%s AND producto_id=%s
        RETURNING preferencia_id""",
        (cliente_id, producto_id),
    )


@bp.get("/<int:cliente_id>/observaciones")
@endpoint()
def observations(cliente_id: int) -> dict[str, Any]:
    customer_exists(cliente_id)
    sede = branch()
    return {
        "observaciones": get_db()
        .execute(
            """SELECT o.* FROM observaciones_cliente o
        LEFT JOIN visitas v USING(visita_id) WHERE o.cliente_id=%s
        AND (%s::bigint IS NULL OR o.visita_id IS NULL OR v.sucursal_id=%s)
        ORDER BY fecha_creacion DESC,observacion_id DESC LIMIT %s OFFSET %s""",
            (cliente_id, sede, sede, *pagination()),
        )
        .fetchall()
    }


@bp.post("/<int:cliente_id>/observaciones")
@endpoint()
def add_observation(cliente_id: int) -> tuple[dict[str, Any], int]:
    customer_exists(cliente_id, active=True)
    data = body({"observacion": text, "visita_id": optional_id}, {"observacion"})
    if data.get("visita_id") is not None:
        visit = one("SELECT sucursal_id FROM visitas WHERE visita_id=%s", (data["visita_id"],))
        branch(visit["sucursal_id"])
    return insert(
        "observaciones_cliente",
        {**data, "cliente_id": cliente_id, "usuario_id": g.user["usuario_id"]},
    ), 201


@bp.patch("/<int:cliente_id>/observaciones/<int:observacion_id>")
@endpoint()
def edit_observation(cliente_id: int, observacion_id: int) -> dict[str, Any]:
    existing = one(
        """SELECT o.usuario_id,v.sucursal_id FROM observaciones_cliente o
        LEFT JOIN visitas v USING(visita_id) WHERE o.cliente_id=%s AND observacion_id=%s""",
        (cliente_id, observacion_id),
    )
    branch(existing["sucursal_id"])
    if existing["usuario_id"] != g.user["usuario_id"] and g.user["rol"] != "administrador":
        abort(403)
    return update(
        "observaciones_cliente",
        "observacion_id",
        observacion_id,
        body({"observacion": text}, {"observacion"}),
    )

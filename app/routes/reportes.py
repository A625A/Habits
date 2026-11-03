"""Presentación HTML de los cinco reportes definitivos de PostgreSQL."""

import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
from flask import Blueprint, current_app, render_template, request

from app.db import get_db
from app.security import require_roles

bp = Blueprint("reportes", __name__, url_prefix="/reportes")
GUATEMALA = ZoneInfo("America/Guatemala")


def _month_after(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _default_filters() -> dict[str, str]:
    today = datetime.now(GUATEMALA).date()
    first = today.replace(day=1)
    return {
        "desde": first.isoformat(),
        "hasta": _month_after(first).isoformat(),
        "mes": first.strftime("%Y-%m"),
    }


def _parse_filters() -> tuple[dict[str, Any] | None, dict[str, str], str | None]:
    values = _default_filters()
    for key in values:
        if key in request.args:
            values[key] = request.args[key].strip()

    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", values["desde"]):
            raise ValueError
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", values["hasta"]):
            raise ValueError
        if not re.fullmatch(r"\d{4}-\d{2}", values["mes"]):
            raise ValueError
        since = date.fromisoformat(values["desde"])
        until = date.fromisoformat(values["hasta"])
        inventory_month = date.fromisoformat(values["mes"] + "-01")
    except ValueError:
        return None, values, "Usá fechas válidas con los formatos indicados."

    if since >= until:
        return None, values, "La fecha inicial debe ser anterior a la fecha final."

    parsed = {
        "desde": datetime.combine(since, time.min, GUATEMALA),
        "hasta": datetime.combine(until, time.min, GUATEMALA),
        "mes": inventory_month,
    }
    return parsed, values, None


def _load_reports(filters: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    interval = (filters["desde"], filters["hasta"])
    db = get_db()
    with db.transaction():
        db.execute("SET LOCAL ROLE habits_operaciones")
        products = db.execute(
            "SELECT * FROM reporte_productos(%s::timestamptz,%s::timestamptz)", interval
        ).fetchall()
        frequent = db.execute(
            "SELECT * FROM reporte_frecuentes(%s::timestamptz,%s::timestamptz)", interval
        ).fetchall()
        reservations = db.execute(
            "SELECT * FROM reporte_reservas(%s::timestamptz,%s::timestamptz)", interval
        ).fetchall()
        inventory = db.execute(
            """SELECT r.*,s.nombre AS sucursal,i.nombre AS ingrediente,i.unidad
            FROM reporte_inventario(%s::date) r
            JOIN sucursales s USING(sucursal_id)
            JOIN ingredientes i USING(ingrediente_id)
            ORDER BY r.sucursal_id,r.ingrediente_id,r.vencimiento,r.lote_id""",
            (filters["mes"],),
        ).fetchall()
        branches = db.execute(
            "SELECT * FROM reporte_sucursales(%s::timestamptz,%s::timestamptz)", interval
        ).fetchall()
    return {
        "productos": products,
        "frecuentes": frequent,
        "reservas": reservations,
        "inventario": inventory,
        "sucursales": branches,
    }


def _totals(reports: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    return {
        "productos": {
            "unidades": sum(row["unidades"] for row in reports["productos"]),
            "importe": sum((row["importe"] for row in reports["productos"]), Decimal(0)),
        },
        "sucursales": {
            "reservas": sum(row["reservas"] for row in reports["sucursales"]),
            "ventas": sum(row["ventas"] for row in reports["sucursales"]),
            "importe": sum((row["importe"] for row in reports["sucursales"]), Decimal(0)),
        },
    }


@bp.app_template_filter("money")
def money(value: Any) -> str:
    return f"Q {Decimal(value):,.2f}"


@bp.app_template_filter("quantity")
def quantity(value: Any) -> str:
    rendered = f"{Decimal(value):,.3f}"
    return rendered.rstrip("0").rstrip(".")


@bp.get("", strict_slashes=False)
@require_roles("administrador")
def index() -> tuple[str, int] | str:
    parsed, values, validation_error = _parse_filters()
    if validation_error is not None or parsed is None:
        page = render_template(
            "reportes.html", filters=values, reports=None, totals=None, error=validation_error
        )
        return page, 400

    try:
        reports = _load_reports(parsed)
    except psycopg.Error as error:
        current_app.logger.warning(
            "No se pudieron consultar reportes (SQLSTATE %s)", error.sqlstate
        )
        page = render_template(
            "reportes.html",
            filters=values,
            reports=None,
            totals=None,
            error="No fue posible consultar los reportes. Intentá de nuevo más tarde.",
        )
        return page, 503

    return render_template(
        "reportes.html", filters=values, reports=reports, totals=_totals(reports)
    )

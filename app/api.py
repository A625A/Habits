"""Contrato JSON, validación de transporte y transacciones del backend operativo."""

from collections.abc import Callable, Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from typing import Any

import psycopg
from flask import Blueprint, Response, abort, g, jsonify, request
from werkzeug.exceptions import HTTPException

from app.db import get_db
from app.security import check_csrf, require_roles


def blueprint(name: str, prefix: str) -> Blueprint:
    bp = Blueprint(name, __name__, url_prefix=prefix)
    bp.before_request(check_csrf)

    @bp.errorhandler(HTTPException)
    def http_error(error: HTTPException) -> tuple[dict[str, str], int]:
        return {"error": error.description or error.name}, error.code or 500

    @bp.errorhandler(psycopg.Error)
    def db_error(error: psycopg.Error) -> tuple[dict[str, str], int]:
        state = error.sqlstate or ""
        if state in {"23505", "23P01", "40001", "40P01"}:
            return {
                "error": "Conflicto con datos existentes; consultá el estado antes de reintentar."
            }, 409
        if state.startswith(("22", "23")):
            return {"error": "Datos inválidos o referencias incompatibles."}, 400
        if state == "P0001":
            # Mensajes de negocio controlados por los triggers, sin detalle SQL ni valores.
            return {"error": error.diag.message_primary or "Operación no permitida."}, 409
        return {"error": "Base de datos no disponible. Contactá al administrador."}, 503

    @bp.after_request
    def headers(response: Response) -> Response:
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return bp


def json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def endpoint(*roles: str) -> Callable[..., Any]:
    """Autenticar antes de bajar privilegios; confirmar antes de devolver éxito."""

    def decorate(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        @require_roles(*roles)
        def wrapped(*args: Any, **kwargs: Any) -> Response:
            db = get_db()
            with db.transaction():
                db.execute("SET LOCAL ROLE habits_operaciones")
                db.execute(
                    "SELECT set_config('habits.usuario_id', %s, true)", (str(g.user["usuario_id"]),)
                )
                result = view(*args, **kwargs)
            data, status = result if isinstance(result, tuple) else (result, 200)
            response = jsonify(json_value(data))
            response.status_code = status
            return response

        return wrapped

    return decorate


def body(
    spec: Mapping[str, Callable[[Any], Any]], required: set[str] | None = None
) -> dict[str, Any]:
    data = request.get_json()
    if not isinstance(data, dict) or data.keys() - spec.keys() or (required or set()) - data.keys():
        abort(400, description="Campos faltantes o desconocidos.")
    if not data:
        abort(400, description="Se requieren datos.")
    return {key: spec[key](value) for key, value in data.items()}


def text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        abort(400, description="Se requiere texto no vacío.")
    return value.strip()


def nullable_text(value: Any) -> str | None:
    return None if value is None else text(value)


def integer(value: Any) -> int:
    if type(value) is not int or not 0 < value <= 2147483647:
        abort(400, description="Se requiere un entero positivo válido.")
    return int(value)


def identifier(value: Any) -> int:
    if type(value) is not int or not 0 < value <= 9223372036854775807:
        abort(400, description="Identificador inválido.")
    return int(value)


def optional_id(value: Any) -> int | None:
    return None if value is None else identifier(value)


def boolean(value: Any) -> bool:
    if type(value) is not bool:
        abort(400, description="Se requiere true o false.")
    return bool(value)


def _decimal(value: Any, scale: int) -> Decimal:
    try:
        number = Decimal(str(value))
        if (
            not number.is_finite()
            or number <= 0
            or number >= 10**10
            or number.as_tuple().exponent not in range(-scale, 100)
        ):
            raise ValueError
        return number
    except (InvalidOperation, ValueError):
        abort(400, description=f"Cantidad positiva con hasta {scale} decimales requerida.")


def decimal(value: Any) -> Decimal:
    return _decimal(value, 3)


def price(value: Any) -> Decimal:
    return _decimal(value, 2)


def day(value: Any) -> date:
    try:
        return date.fromisoformat(text(value))
    except ValueError:
        abort(400, description="Fecha inválida; usar AAAA-MM-DD.")


def instant(value: Any) -> datetime:
    try:
        result = datetime.fromisoformat(text(value))
        if result.tzinfo is None:
            raise ValueError
        return result
    except ValueError:
        abort(400, description="Fecha/hora ISO 8601 con zona horaria requerida.")


def query_id(name: str) -> int | None:
    value = request.args.get(name)
    if value is None:
        return None
    if len(value) > 19 or not value.isascii() or not value.isdigit():
        abort(400, description="Filtro de identificador inválido.")
    return identifier(int(value))


def branch(value: int | None = None) -> int | None:
    """El administrador consulta todas; el resto solo su sede, aun por ID directo."""
    if g.user["rol"] != "administrador":
        if value is not None and value != g.user["sucursal_id"]:
            abort(403)
        return int(g.user["sucursal_id"])
    return value


def pagination() -> tuple[int, int]:
    values = []
    for key, default, maximum in [("limite", "50", 200), ("offset", "0", 2147483647)]:
        raw = request.args.get(key, default)
        if len(raw) > 10 or not raw.isascii() or not raw.isdigit() or not 0 <= int(raw) <= maximum:
            abort(400, description="Paginación inválida.")
        values.append(int(raw))
    if values[0] == 0:
        abort(400, description="El límite debe ser positivo.")
    return values[0], values[1]

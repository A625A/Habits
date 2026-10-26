import psycopg
from flask import Blueprint

from app.db import get_db

bp = Blueprint("health", __name__, url_prefix="/health")


@bp.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}


@bp.get("/db")
def database_health() -> tuple[dict[str, str], int]:
    try:
        get_db().execute("SELECT 1").fetchone()
    except psycopg.Error:
        return {"status": "error", "database": "unavailable"}, 503
    return {"status": "ok", "database": "ok"}, 200

from pathlib import Path
from typing import Any

from flask import current_app

from app.db import get_db


def comparar_sucursales(sucursal_id: int | None = None) -> list[dict[str, Any]]:
    sql_file = Path(current_app.root_path).parent / "sql" / "reportes_sucursales.sql"
    query = sql_file.read_text(encoding="utf-8")
    db = get_db()
    result = db.execute(query, {"sucursal_id": sucursal_id})
    return result.fetchall()

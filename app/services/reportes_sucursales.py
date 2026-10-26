from pathlib import Path
from typing import Any

from flask import current_app

from app.db import get_db


def comparar_sucursales(sucursal_id: int | None = None) -> list[dict[str, Any]]:
    query = Path(current_app.root_path).parent / "sql" / "reportes_sucursales.sql"
    return (
        get_db().execute(query.read_text(encoding="utf-8"), {"sucursal_id": sucursal_id}).fetchall()
    )

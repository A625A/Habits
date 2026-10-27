"""Andrew: datos del reporte. Brian conserva su Blueprint de presentación."""

from flask import Blueprint, g

from app.security import require_roles
from app.services.reportes_sucursales import comparar_sucursales

bp = Blueprint("comparacion", __name__, url_prefix="/reportes")


@bp.get("/sucursales")
@require_roles("administrador", "gerente")
def sucursales() -> tuple[dict[str, object], int, dict[str, str]]:
    branch_id = None
    if g.user["rol"] == "gerente":
        branch_id = g.user["sucursal_id"]
    data: dict[str, object] = {
        "estado_operativo": "pendiente_modulos",
        "sucursales": comparar_sucursales(branch_id),
    }
    return data, 200, {"Cache-Control": "no-store"}

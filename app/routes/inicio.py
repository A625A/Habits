"""Inicio y navegación de la interfaz compartida."""

from flask import Blueprint, render_template

from app.security import require_roles

bp = Blueprint("inicio", __name__, url_prefix="")


@bp.get("/")
@require_roles()
def index() -> str:
    """Mostrar accesos disponibles sin presentar las APIs como pantallas terminadas."""
    return render_template("index.html")

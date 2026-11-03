"""Inicio y navegación de la interfaz compartida."""

from flask import (
    Blueprint,
    abort,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.wrappers import Response

from app.security import csrf_token, require_roles

bp = Blueprint("inicio", __name__, url_prefix="")

MODULOS = {
    "clientes": "Clientes e historial",
    "reservas": "Reservas",
    "visitas": "Visitas",
    "mesas": "Mesas",
    "catalogo": "Productos y recetas",
    "ingredientes": "Ingredientes",
    "inventario": "Inventario y recepciones",
    "producciones": "Producción",
    "ventas": "Ventas",
}


@bp.before_request
def abrir_login() -> Response | None:
    if request.endpoint == "inicio.index" and not session.get("token"):
        return redirect(url_for("auth.login"))
    return None


@bp.get("/operacion/<modulo>")
@require_roles()
def operacion(modulo: str) -> str:
    if modulo not in MODULOS:
        abort(404)
    if modulo in {"inventario", "producciones"} and g.user["rol"] == "mesero":
        abort(403)
    return render_template(
        "operacion.html",
        modulo=modulo,
        titulo=MODULOS[modulo],
        modulos=MODULOS,
        csrf_token=csrf_token(),
    )


@bp.get("/")
@require_roles()
def index() -> str:
    """Mostrar los módulos disponibles para la persona que inició sesión."""
    return render_template("index.html")

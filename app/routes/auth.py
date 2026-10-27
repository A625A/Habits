from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask.typing import ResponseReturnValue

from app.db import get_db
from app.security import check_csrf, csrf_token, require_roles
from app.services.auth import ROLES, authenticate, end_session, register_personnel

bp = Blueprint("auth", __name__, url_prefix="/auth")
bp.before_request(check_csrf)


@bp.after_request
def auth_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@bp.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
    if request.method != "POST":
        return render_template("auth/login.html", csrf_token=csrf_token())

    email = request.form.get("email", "")
    password = request.form.get("password", "")
    token = authenticate(email, password)
    if token is None:
        page = render_template(
            "auth/login.html", csrf_token=csrf_token(), error="Correo o contraseña incorrectos."
        )
        return page, 401

    previous_token = session.get("token")
    if isinstance(previous_token, str):
        end_session(previous_token)
    session.clear()
    session["token"] = token
    session.permanent = True
    return redirect(url_for("auth.account"), code=303)


@bp.get("/me")
@require_roles()
def me() -> dict[str, object]:
    return dict(g.user)


@bp.get("/cuenta")
@require_roles()
def account() -> str:
    return render_template("auth/cuenta.html", user=g.user, csrf_token=csrf_token())


@bp.post("/logout")
@require_roles()
def logout() -> ResponseReturnValue:
    end_session(session["token"])
    session.clear()
    return redirect(url_for("auth.login"), code=303)


@bp.route("/register", methods=["GET", "POST"])
@require_roles("administrador")
def register() -> ResponseReturnValue:
    error = None
    if request.method == "POST":
        try:
            branch_id = int(request.form.get("sucursal_id", "0"))
        except ValueError:
            branch_id = 0
        try:
            register_personnel(
                g.user["usuario_id"],
                request.form.get("nombre", ""),
                request.form.get("email", ""),
                request.form.get("password", ""),
                request.form.get("rol", ""),
                branch_id,
            )
        except PermissionError:
            abort(403)
        except ValueError as exc:
            error = str(exc)
        else:
            flash("Personal registrado.")
            return redirect(url_for("auth.register"), code=303)
    db = get_db()
    result = db.execute("SELECT sucursal_id, nombre FROM sucursales WHERE activa ORDER BY codigo")
    branches = result.fetchall()
    status = 200
    if error:
        status = 400
    page = render_template(
        "auth/register.html", csrf_token=csrf_token(), branches=branches, roles=ROLES, error=error
    )
    return page, status

import secrets
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import abort, g, request, session

from app.services.auth import session_user


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return str(session["csrf_token"])


def check_csrf() -> None:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = session.get("csrf_token")
        supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if (
            not isinstance(expected, str)
            or not supplied
            or not secrets.compare_digest(expected.encode(), supplied.encode())
        ):
            abort(400, description="Solicitud inválida. Recargá el formulario.")


def require_roles(*roles: str) -> Callable[..., Any]:
    def decorate(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            token = session.get("token")
            user = session_user(token) if isinstance(token, str) else None
            if user is None:
                session.clear()
                abort(401)
            if roles and user["rol"] not in roles:
                abort(403)
            g.user = user
            return view(*args, **kwargs)

        return wrapped

    return decorate

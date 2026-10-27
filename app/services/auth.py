import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db

ROLES = ("administrador", "gerente", "mesero")
_DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32), method="scrypt")
SESSION_LIFETIME = timedelta(hours=8)
DEMO_EMAIL = "admin@demo.invalid"


def demo_enabled() -> bool:
    return (
        current_app.config["HABITS_ENV"] == "development"
        and current_app.config["HABITS_DEMO_LOGIN"] is True
    )


def create_demo_admin() -> None:
    if not demo_enabled():
        raise ValueError("La cuenta demo requiere development y HABITS_DEMO_LOGIN=1.")
    db = get_db()
    with db.transaction():
        db.execute("LOCK TABLE usuarios IN SHARE ROW EXCLUSIVE MODE")
        existing = db.execute(
            "SELECT password_hash, rol, activo FROM usuarios WHERE LOWER(email) = %s",
            (DEMO_EMAIL,),
        ).fetchone()
        if existing:
            if (
                existing["rol"] != "administrador"
                or not existing["activo"]
                or not check_password_hash(existing["password_hash"], "123")
            ):
                raise ValueError("La cuenta reservada ya existe con otros datos; no se modificó.")
            return
        branch = db.execute(
            "SELECT sucursal_id FROM sucursales WHERE codigo = 'DEMO-01' AND activa"
        ).fetchone()
        if branch is None:
            raise ValueError("La demo requiere la sucursal DEMO-01 activa; ejecutá db-seed.")
        db.execute(
            """INSERT INTO usuarios (nombre, email, password_hash, rol, sucursal_id)
               VALUES (%s, %s, %s, 'administrador', %s)""",
            (
                "Administrador demo",
                DEMO_EMAIL,
                generate_password_hash("123", method="scrypt"),
                branch["sucursal_id"],
            ),
        )


def _insert_user(nombre: str, email: str, password: str, rol: str, sucursal_id: int) -> int:
    nombre, email = nombre.strip(), email.strip().lower()
    if email == DEMO_EMAIL:
        raise ValueError("Correo reservado para el comando de demo local.")
    if not nombre or len(nombre) > 120:
        raise ValueError("Ingresá un nombre de hasta 120 caracteres.")
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Ingresá un correo válido.")
    if not 12 <= len(password) <= 128:
        raise ValueError("La contraseña debe tener entre 12 y 128 caracteres.")
    if rol not in ROLES:
        raise ValueError("Rol no válido.")
    db = get_db()
    if not db.execute(
        "SELECT sucursal_id FROM sucursales WHERE sucursal_id = %s AND activa", (sucursal_id,)
    ).fetchone():
        raise ValueError("Elegí una sucursal activa.")
    try:
        row: dict[str, Any] | None = db.execute(
            """INSERT INTO usuarios (nombre, email, password_hash, rol, sucursal_id)
               VALUES (%s, %s, %s, %s, %s) RETURNING usuario_id""",
            (nombre, email, generate_password_hash(password, method="scrypt"), rol, sucursal_id),
        ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise ValueError("Ese correo ya está registrado.") from None
    assert row is not None
    return int(row["usuario_id"])


def bootstrap_admin(nombre: str, email: str, password: str, sucursal: str) -> int:
    db = get_db()
    with db.transaction():
        # Serializa altas iniciales concurrentes sin crear dos administradores iniciales.
        db.execute("LOCK TABLE usuarios IN SHARE ROW EXCLUSIVE MODE")
        if db.execute("SELECT 1 FROM usuarios WHERE rol = 'administrador'").fetchone():
            raise ValueError("Ya existe un administrador; usá el registro autenticado.")
        branch = db.execute(
            "SELECT sucursal_id FROM sucursales WHERE codigo = %s AND activa", (sucursal,)
        ).fetchone()
        if branch is None:
            raise ValueError("La sucursal no existe o está inactiva.")
        return _insert_user(nombre, email, password, "administrador", branch["sucursal_id"])


def authenticate(email: str, password: str) -> str | None:
    if len(email) > 254 or len(password) > 128:
        return None
    email = email.strip().lower()
    if email == "admin":
        email = DEMO_EMAIL
    if email == DEMO_EMAIL and not demo_enabled():
        return None
    db = get_db()
    with db.transaction():
        user = db.execute(
            """SELECT u.usuario_id, u.password_hash, u.activo, s.activa
               FROM usuarios u JOIN sucursales s USING (sucursal_id)
               WHERE LOWER(u.email) = %s FOR SHARE OF u, s""",
            (email,),
        ).fetchone()
        valid = check_password_hash(user["password_hash"] if user else _DUMMY_HASH, password)
        if not user or not valid or not user["activo"] or not user["activa"]:
            return None
        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO sesiones (token_hash, usuario_id, expira_en) VALUES (%s, %s, %s)",
            (
                hashlib.sha256(token.encode()).hexdigest(),
                user["usuario_id"],
                datetime.now(UTC) + SESSION_LIFETIME,
            ),
        )
        return token


def session_user(token: str) -> dict[str, Any] | None:
    return (
        get_db()
        .execute(
            """SELECT u.usuario_id, u.nombre, u.email, u.rol, u.sucursal_id
           FROM sesiones se JOIN usuarios u USING (usuario_id)
           JOIN sucursales s USING (sucursal_id)
           WHERE se.token_hash = %s AND se.expira_en > CURRENT_TIMESTAMP
             AND u.activo AND s.activa
             AND (LOWER(u.email) <> %s OR %s)""",
            (hashlib.sha256(token.encode()).hexdigest(), DEMO_EMAIL, demo_enabled()),
        )
        .fetchone()
    )


def end_session(token: str) -> None:
    with get_db().transaction():
        get_db().execute(
            "DELETE FROM sesiones WHERE token_hash = %s",
            (hashlib.sha256(token.encode()).hexdigest(),),
        )


def register_personnel(
    actor_id: int, nombre: str, email: str, password: str, rol: str, sucursal_id: int
) -> int:
    db = get_db()
    with db.transaction():
        actor = db.execute(
            """SELECT u.usuario_id FROM usuarios u JOIN sucursales s USING (sucursal_id)
               WHERE u.usuario_id = %s AND u.rol = 'administrador' AND u.activo AND s.activa
               FOR SHARE OF u, s""",
            (actor_id,),
        ).fetchone()
        if actor is None:
            raise PermissionError("Solo un administrador activo puede registrar personal.")
        db.execute("SELECT set_config('habits.usuario_id', %s, true)", (str(actor_id),))
        return _insert_user(nombre, email, password, rol, sucursal_id)

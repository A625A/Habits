import os
from datetime import timedelta
from typing import Any

import psycopg
from dotenv import load_dotenv
from flask import Flask


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        HABITS_ENV=os.environ.get("HABITS_ENV", "development"),
        SESSION_COOKIE_NAME="habits_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_REFRESH_EACH_REQUEST=False,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if test_config is not None:
        app.config.update(test_config)
    if not app.config["DATABASE_URL"]:
        raise ValueError("DATABASE_URL es obligatoria. Configurá .env antes de iniciar Flask.")
    secret = app.config["SECRET_KEY"]
    if not isinstance(secret, str) or len(secret) < 32 or secret.startswith("CAMBIAR"):
        raise ValueError("SECRET_KEY debe ser un valor aleatorio de al menos 32 caracteres.")
    if app.config["HABITS_ENV"] not in {"development", "production"}:
        raise ValueError("HABITS_ENV debe ser development o production.")
    app.config["SESSION_COOKIE_SECURE"] = app.config["HABITS_ENV"] == "production"

    from app import db
    from app.auth_cli import create_admin_command
    from app.routes import register_blueprints

    db.init_app(app)
    app.cli.add_command(create_admin_command)
    register_blueprints(app)

    @app.errorhandler(psycopg.Error)
    def database_error(error: psycopg.Error) -> tuple[dict[str, str], int]:
        app.logger.warning("Error PostgreSQL (SQLSTATE %s)", error.sqlstate)
        return {"error": "Base de datos no disponible. Contactá al administrador."}, 503

    return app

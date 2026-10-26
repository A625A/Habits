import os
from typing import Any

from dotenv import load_dotenv
from flask import Flask


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        SECRET_KEY=os.environ.get("SECRET_KEY"),
    )
    if test_config is not None:
        app.config.update(test_config)
    if not app.config["DATABASE_URL"]:
        raise ValueError("DATABASE_URL es obligatoria. Configurá .env antes de iniciar Flask.")

    from app import db
    from app.routes import register_blueprints

    db.init_app(app)
    register_blueprints(app)
    return app

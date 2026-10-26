from pathlib import Path
from typing import Any

import click
import psycopg
from flask import Flask, current_app, g
from flask.cli import with_appcontext
from psycopg.rows import dict_row


def get_db() -> psycopg.Connection[dict[str, Any]]:
    """Una conexión por contexto. Agrupar escrituras en `with get_db().transaction()`."""
    if "db" not in g:
        g.db = psycopg.connect(
            current_app.config["DATABASE_URL"],
            autocommit=True,
            row_factory=dict_row,
            connect_timeout=3,
        )
    return g.db


def close_db(error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)
    app.cli.add_command(upgrade_db_command)


@click.command("db-init")
@with_appcontext
def init_db_command() -> None:
    """Crear únicamente el esquema core en una base vacía, sin borrar datos."""
    script = Path(current_app.root_path).parent / "sql" / "01_core.sql"
    try:
        with get_db().transaction():
            get_db().execute(script.read_text(encoding="utf-8"))
    except psycopg.Error:
        raise click.ClickException(
            "No se pudo crear el core. Verificá conexión y que las tablas no existan."
        ) from None
    click.echo("Esquema core creado.")


@click.command("db-seed")
@with_appcontext
def seed_db_command() -> None:
    """Agregar las dos sucursales ficticias, conservando las existentes."""
    script = Path(current_app.root_path).parent / "sql" / "08_seed.sql"
    try:
        with get_db().transaction():
            get_db().execute(script.read_text(encoding="utf-8"))
    except psycopg.Error:
        raise click.ClickException(
            "No se pudo cargar el seed. Verificá conexión y ejecutá db-init primero."
        ) from None
    click.echo("Sucursales demo disponibles.")


@click.command("db-upgrade")
@with_appcontext
def upgrade_db_command() -> None:
    """Aplicar ampliaciones de Andrew sobre el core existente sin borrar datos."""
    scripts = Path(current_app.root_path).parent / "sql"
    try:
        with get_db().transaction():
            get_db().execute((scripts / "01_auth.sql").read_text(encoding="utf-8"))
            get_db().execute((scripts / "06_auditoria.sql").read_text(encoding="utf-8"))
    except psycopg.Error as error:
        raise click.ClickException(
            f"No se pudo actualizar el esquema (SQLSTATE {error.sqlstate}). "
            "Verificá conexión y ejecutá db-init primero en una base nueva."
        ) from None
    click.echo("Ampliaciones de Andrew aplicadas.")

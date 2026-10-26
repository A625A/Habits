import click
import psycopg
from flask.cli import with_appcontext

from app.services.auth import bootstrap_admin


@click.command("create-admin")
@click.option("--nombre", prompt="Nombre")
@click.option("--email", prompt="Correo")
@click.option("--sucursal", prompt="Código de sucursal")
@with_appcontext
def create_admin_command(nombre: str, email: str, sucursal: str) -> None:
    """Alta inicial local; la contraseña se solicita oculta, nunca como argumento."""
    password = click.prompt("Contraseña", hide_input=True, confirmation_prompt=True)
    try:
        bootstrap_admin(nombre, email, password, sucursal)
    except ValueError as error:
        raise click.ClickException(str(error)) from None
    except psycopg.Error:
        raise click.ClickException(
            "No se pudo crear el administrador. Revisá la conexión y el esquema."
        ) from None
    click.echo("Administrador creado. Iniciá sesión en /auth/login.")

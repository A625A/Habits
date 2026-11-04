"""Iniciar Habits en esta computadora y abrir su página."""

import argparse
import os
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import psycopg
from dotenv import load_dotenv

from app import create_app

ROOT = Path(__file__).resolve().parent


def iniciar_postgres() -> None:
    """Encender la base existente sin crear tablas ni reemplazar datos."""
    carpeta = os.environ.get("HABITS_PGDATA")
    if not carpeta:
        return
    datos = Path(carpeta)
    if not datos.is_absolute():
        datos = ROOT / datos
    if not (datos / "PG_VERSION").is_file():
        raise RuntimeError("No se encontró la base local. Revisa HABITS_PGDATA en .env.")
    comando = os.environ.get("HABITS_PG_CTL") or shutil.which("pg_ctl")
    if not comando:
        raise RuntimeError("No se encontró pg_ctl. Indica su ruta en HABITS_PG_CTL dentro de .env.")
    estado = subprocess.run([comando, "-D", str(datos), "status"], capture_output=True, check=False)
    if estado.returncode == 0:
        return
    if estado.returncode != 3:
        raise RuntimeError("No se pudo comprobar PostgreSQL. Revisa su carpeta y permisos.")
    puerto = int(os.environ.get("HABITS_PGPORT", "55439"))
    resultado = subprocess.run(
        [
            comando,
            "-D",
            str(datos),
            "-l",
            str(datos.parent / "postgres.log"),
            "-o",
            f"-h 127.0.0.1 -p {puerto}",
            "-w",
            "start",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if resultado.returncode:
        raise RuntimeError("PostgreSQL no inició. Revisa .local/postgres.log.")


def abrir_cuando_responda(url: str) -> None:
    for _ in range(60):
        try:
            with urlopen(url + "/health", timeout=1) as respuesta:
                if respuesta.status == 200:
                    webbrowser.open(url)
                    return
        except (URLError, TimeoutError):
            time.sleep(0.5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Abrir Habits en esta computadora.")
    parser.add_argument("--sin-navegador", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    iniciar_postgres()
    app = create_app()
    # Revisar la conexión antes de mostrar la página, sin imprimir contraseñas.
    try:
        with psycopg.connect(app.config["DATABASE_URL"], connect_timeout=5) as conexion:
            esquema = conexion.execute("SELECT to_regclass('productos')").fetchone()
            if esquema is None or esquema[0] is None:
                raise RuntimeError("Falta instalar la base completa. Consulta el README.")
    except psycopg.Error as exc:
        raise RuntimeError("No se pudo conectar con la base. Revisa DATABASE_URL en .env.") from exc
    puerto = int(os.environ.get("HABITS_PORT", "5059"))
    url = f"http://127.0.0.1:{puerto}"
    with socket.socket() as prueba:
        ocupado = prueba.connect_ex(("127.0.0.1", puerto)) == 0
    if ocupado:
        try:
            with urlopen(url + "/health", timeout=2) as respuesta:
                correcto = respuesta.status == 200 and b'"status"' in respuesta.read()
        except (URLError, TimeoutError):
            correcto = False
        if not correcto:
            raise RuntimeError(f"El puerto {puerto} está ocupado. Revisa HABITS_PORT en .env.")
        print(f"Habits ya está abierto: {url}")
        if not args.sin_navegador:
            webbrowser.open(url)
        return
    print(f"Abre {url}. Deja esta ventana abierta; Ctrl+C detiene la aplicación.")
    if not args.sin_navegador:
        threading.Thread(target=abrir_cuando_responda, args=(url,), daemon=True).start()
    app.run(host="127.0.0.1", port=puerto, debug=False, use_reloader=False)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from None

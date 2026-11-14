"""Pruebas con un clúster efímero propio; nunca usa DATABASE_URL ni archivos .env."""

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg
from psycopg.conninfo import make_conninfo

ROOT = Path(__file__).resolve().parents[2]


def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--proyecto2", action="store_true", help="Ejecutar además la suite original"
    )
    args = parser.parse_args()
    for executable in ("initdb", "pg_ctl", "psql"):
        if not shutil.which(executable):
            parser.error(f"Falta {executable}; agregar PostgreSQL 17 al PATH.")

    # /tmp evita superar el límite de longitud de sockets de PostgreSQL en macOS.
    with tempfile.TemporaryDirectory(prefix="habits_olap_", dir="/tmp") as directory:
        base = Path(directory)
        data = base / "data"
        run(
            "initdb",
            "-D",
            str(data),
            "-U",
            "habits_olap_admin",
            "--auth-local=trust",
            "--auth-host=reject",
            "--encoding=UTF8",
            "--locale=C",
            stdout=subprocess.DEVNULL,
        )
        run(
            "pg_ctl",
            "-D",
            str(data),
            "-l",
            str(base / "server.log"),
            "-o",
            f"-h '' -p 55439 -k {base}",
            "-w",
            "start",
        )
        try:
            admin_dsn = make_conninfo(
                host=directory, port=55439, user="habits_olap_admin", dbname="postgres"
            )
            with psycopg.connect(admin_dsn, autocommit=True) as conn:
                conn.execute("CREATE ROLE habits_olap_owner LOGIN")
                conn.execute("CREATE DATABASE habits_olap_admin_test")
                if args.proyecto2:
                    conn.execute("CREATE ROLE habits_test LOGIN")
                    conn.execute("CREATE ROLE habits_operaciones NOLOGIN")
                    conn.execute("GRANT habits_operaciones TO habits_test")
                    conn.execute("CREATE DATABASE habits_p2_test OWNER habits_test")
            env = os.environ.copy()
            env["SECRET_KEY"] = secrets.token_hex(32)
            env["OLAP_TEST_ADMIN_DSN"] = make_conninfo(admin_dsn, dbname="habits_olap_admin_test")
            run(sys.executable, "-m", "pytest", "olap/tests", "-q", cwd=ROOT, env=env)
            if args.proyecto2:
                env["TEST_DATABASE_URL"] = make_conninfo(
                    admin_dsn, user="habits_test", dbname="habits_p2_test"
                )
                run(sys.executable, "-m", "pytest", cwd=ROOT, env=env)
        finally:
            run("pg_ctl", "-D", str(data), "-m", "fast", "-w", "stop")


if __name__ == "__main__":
    main()

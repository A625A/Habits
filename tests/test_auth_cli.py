import psycopg
from werkzeug.security import check_password_hash


def test_actualizacion_repetible_conserva_core_y_agrega_sesiones(app, database_url):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["db-init"]).exit_code == 0
    assert runner.invoke(args=["db-seed"]).exit_code == 0
    with psycopg.connect(database_url) as conn:
        before = conn.execute("SELECT * FROM sucursales ORDER BY sucursal_id").fetchall()
    for _ in range(2):
        result = runner.invoke(args=["db-upgrade"])
        assert result.exit_code == 0, result.output
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT * FROM sucursales ORDER BY sucursal_id").fetchall() == before
        assert conn.execute("SELECT COUNT(*) FROM sesiones").fetchone() == (0,)


def test_primer_admin_requiere_datos_y_guarda_hash_sin_repetir_alta(
    auth_app, database_url, admin_password
):
    runner = auth_app.test_cli_runner()
    args = [
        "create-admin",
        "--nombre",
        "Admin prueba",
        "--email",
        "Admin@example.test",
        "--sucursal",
        "DEMO-01",
    ]
    result = runner.invoke(args=args, input=f"{admin_password}\n{admin_password}\n")
    assert result.exit_code == 0, result.output
    assert admin_password not in result.output
    with psycopg.connect(database_url) as conn:
        row = conn.execute("SELECT email, password_hash, rol FROM usuarios").fetchone()
        assert row[0] == "admin@example.test"
        assert row[1] != admin_password
        assert check_password_hash(row[1], admin_password)
        assert row[2] == "administrador"
    again = runner.invoke(args=args, input=f"{admin_password}\n{admin_password}\n")
    assert again.exit_code != 0
    assert "administrador" in again.output


def test_fallo_de_actualizacion_revierte_todas_las_ampliaciones(app, database_url):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["db-init"]).exit_code == 0
    with psycopg.connect(database_url) as conn:
        conn.execute("CREATE TABLE auditoria (incompatible TEXT)")
    result = runner.invoke(args=["db-upgrade"])
    assert result.exit_code != 0
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT to_regclass('sesiones')").fetchone() == (None,)
        assert conn.execute("SELECT COUNT(*) FROM usuarios").fetchone() == (0,)

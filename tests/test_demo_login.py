import re

import psycopg
import pytest
from werkzeug.security import check_password_hash


def login_demo(client, identifier="admin"):
    page = client.get("/auth/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    return client.post(
        "/auth/login", data={"email": identifier, "password": "123", "csrf_token": token}
    )


def test_comando_demo_explicito_guarda_hash_y_es_repetible(auth_app, database_url):
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT count(*) FROM usuarios").fetchone() == (0,)
    auth_app.config["HABITS_DEMO_LOGIN"] = True
    runner = auth_app.test_cli_runner()
    for _ in range(2):
        result = runner.invoke(args=["create-demo-admin"])
        assert result.exit_code == 0, result.output
    with psycopg.connect(database_url) as conn:
        users = conn.execute("SELECT email, password_hash, rol FROM usuarios").fetchall()
        assert len(users) == 1
        assert users[0][0] == "admin@demo.invalid"
        assert users[0][1] != "123"
        assert check_password_hash(users[0][1], "123")
        assert users[0][2] == "administrador"


def test_formulario_admite_admin_sin_correo_y_autentica_con_123(auth_app):
    auth_app.config["HABITS_DEMO_LOGIN"] = True
    assert auth_app.test_cli_runner().invoke(args=["create-demo-admin"]).exit_code == 0
    client = auth_app.test_client()
    page = client.get("/auth/login")
    assert 'type="text" name="email"' in page.text
    assert login_demo(client).status_code == 303
    assert client.get("/auth/me").json["rol"] == "administrador"
    assert client.get("/auth/register").status_code == 200


@pytest.mark.parametrize("environment,enabled", [("development", False), ("production", True)])
def test_demo_bloqueada_sin_bandera_o_en_produccion_incluso_sesion_previa(
    auth_app, environment, enabled
):
    auth_app.config["HABITS_DEMO_LOGIN"] = True
    runner = auth_app.test_cli_runner()
    assert runner.invoke(args=["create-demo-admin"]).exit_code == 0
    client = auth_app.test_client()
    assert login_demo(client).status_code == 303
    auth_app.config.update(HABITS_ENV=environment, HABITS_DEMO_LOGIN=enabled)
    assert runner.invoke(args=["create-demo-admin"]).exit_code != 0
    assert client.get("/auth/me").status_code == 401
    for identifier in ("admin", "admin@demo.invalid"):
        assert login_demo(client, identifier).status_code == 401


def test_comando_demo_no_reemplaza_cuenta_existente(auth_app, database_url):
    auth_app.config["HABITS_DEMO_LOGIN"] = True
    runner = auth_app.test_cli_runner()
    assert runner.invoke(args=["create-demo-admin"]).exit_code == 0
    with psycopg.connect(database_url) as conn:
        conn.execute("UPDATE usuarios SET rol = 'mesero'")
        before = conn.execute("SELECT * FROM usuarios").fetchall()
    result = runner.invoke(args=["create-demo-admin"])
    assert result.exit_code != 0
    assert "no se modificó" in result.output
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT * FROM usuarios").fetchall() == before

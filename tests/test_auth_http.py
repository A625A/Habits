import re
import secrets

import psycopg
import pytest


def csrf(client, path="/auth/login"):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def login(client, password, email="admin@example.test"):
    return client.post(
        "/auth/login",
        data={
            "email": email,
            "password": password,
            "csrf_token": csrf(client),
        },
    )


def test_login_y_consulta_de_sesion_sin_exponer_hash(admin_app, admin_password):
    client = admin_app.test_client()
    assert client.get("/auth/me").status_code == 401
    response = login(client, admin_password)
    assert response.status_code == 303
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json["email"] == "admin@example.test"
    assert me.json["rol"] == "administrador"
    assert "password" not in me.text


def test_logout_revoca_cookie_copiada_y_exige_csrf(admin_app, admin_password):
    client = admin_app.test_client()
    assert login(client, admin_password).status_code == 303
    copied = client.get_cookie(admin_app.config["SESSION_COOKIE_NAME"])
    assert copied is not None
    assert client.post("/auth/logout").status_code == 400
    assert client.get("/auth/me").status_code == 200
    result = client.post("/auth/logout", data={"csrf_token": csrf(client, "/auth/cuenta")})
    assert result.status_code == 303
    replay = admin_app.test_client()
    replay.set_cookie(admin_app.config["SESSION_COOKIE_NAME"], copied.value)
    assert replay.get("/auth/me").status_code == 401


def register(client, password, rol="mesero", email="personal@example.test"):
    page = client.get("/auth/register")
    assert page.status_code == 200
    branch = re.search(r'<option value="(\d+)"', page.text)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    return client.post(
        "/auth/register",
        data={
            "nombre": "Personal prueba",
            "email": email,
            "password": password,
            "rol": rol,
            "sucursal_id": branch.group(1),
            "csrf_token": token.group(1),
        },
    )


@pytest.mark.parametrize("rol", ["administrador", "gerente", "mesero"])
def test_solo_admin_registra_personal_con_rol(admin_app, admin_password, rol):
    admin = admin_app.test_client()
    assert admin.get("/auth/register").status_code == 401
    assert login(admin, admin_password).status_code == 303
    password = secrets.token_urlsafe(24)
    assert register(admin, password, rol).status_code == 303
    staff = admin_app.test_client()
    assert login(staff, password, "personal@example.test").status_code == 303
    assert staff.get("/auth/me").json["rol"] == rol
    assert staff.get("/auth/register").status_code == (200 if rol == "administrador" else 403)
    if rol != "administrador":
        response = staff.post(
            "/auth/register",
            data={
                "csrf_token": csrf(staff, "/auth/cuenta"),
                "rol": "administrador",
                "nombre": "Intruso",
                "email": "intruso@example.test",
                "password": password,
                "sucursal_id": "1",
            },
        )
        assert response.status_code == 403


def test_registro_auditado_atribuye_actor_sin_credenciales(admin_app, admin_password, database_url):
    client = admin_app.test_client()
    login(client, admin_password)
    actor = client.get("/auth/me").json["usuario_id"]
    assert register(client, secrets.token_urlsafe(24)).status_code == 303
    with psycopg.connect(database_url) as conn:
        event = conn.execute(
            "SELECT usuario_id, datos_nuevos FROM auditoria WHERE tabla = 'usuarios' ORDER BY auditoria_id DESC LIMIT 1"
        ).fetchone()
        assert event[0] == actor
        assert event[1]["rol"] == "mesero"
        assert "password_hash" not in event[1]


@pytest.mark.parametrize(
    "assignment",
    [
        "rol = 'mesero'",
        "password_hash = 'cambio-solo-prueba'",
        "activo = FALSE",
        "sucursal_id = (SELECT sucursal_id FROM sucursales WHERE codigo = 'DEMO-02')",
    ],
)
def test_cambio_de_seguridad_revoca_sesion(admin_app, admin_password, database_url, assignment):
    from psycopg import sql

    client = admin_app.test_client()
    login(client, admin_password)
    with psycopg.connect(database_url) as conn:
        # SQL literal de la parametrización cerrada del test, nunca entrada del usuario.
        conn.execute(sql.SQL("UPDATE usuarios SET ") + sql.SQL(assignment))
    assert client.get("/auth/me").status_code == 401


def test_desactivar_y_reactivar_sucursal_no_resucita_cookie(
    admin_app, admin_password, database_url
):
    client = admin_app.test_client()
    login(client, admin_password)
    with psycopg.connect(database_url) as conn:
        conn.execute("UPDATE sucursales SET activa = FALSE WHERE codigo = 'DEMO-01'")
        conn.execute("UPDATE sucursales SET activa = TRUE WHERE codigo = 'DEMO-01'")
    assert client.get("/auth/me").status_code == 401


def test_sesion_expirada_no_autoriza(admin_app, admin_password, database_url):
    client = admin_app.test_client()
    login(client, admin_password)
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "UPDATE sesiones SET creada_en = CURRENT_TIMESTAMP - INTERVAL '9 hours', expira_en = CURRENT_TIMESTAMP - INTERVAL '1 hour'"
        )
    assert client.get("/auth/me").status_code == 401


def test_login_invalido_generico_csrf_y_sin_redireccion_externa(admin_app, admin_password):
    client = admin_app.test_client()
    assert (
        client.post(
            "/auth/login", data={"email": "admin@example.test", "password": admin_password}
        ).status_code
        == 400
    )
    invalid = login(client, secrets.token_urlsafe(24))
    unknown = login(client, secrets.token_urlsafe(24), "no-existe@example.test")
    assert invalid.status_code == unknown.status_code == 401
    assert (
        "Correo o contraseña incorrectos." in invalid.text
        and "Correo o contraseña incorrectos." in unknown.text
    )
    assert client.get("/auth/me").status_code == 401
    response = client.post(
        "/auth/login?next=https://externo.example.test",
        data={
            "csrf_token": csrf(client),
            "email": "admin@example.test",
            "password": admin_password,
        },
    )
    assert response.status_code == 303 and response.headers["Location"] == "/auth/cuenta"


def test_registro_valida_datos_y_no_cambia_sesion_del_admin(admin_app, admin_password):
    client = admin_app.test_client()
    login(client, admin_password)
    assert register(client, "corta").status_code == 400
    assert register(client, secrets.token_urlsafe(24), "superusuario").status_code == 400
    assert (
        register(client, secrets.token_urlsafe(24), email="ADMIN@example.test").status_code == 400
    )
    assert register(client, secrets.token_urlsafe(24)).status_code == 303
    assert client.get("/auth/me").json["email"] == "admin@example.test"


def test_login_sin_esquema_devuelve_503_generico(app):
    client = app.test_client()
    response = login(client, secrets.token_urlsafe(24))
    assert response.status_code == 503
    assert response.json == {"error": "Base de datos no disponible. Contactá al administrador."}


def test_csrf_malformado_unicode_se_rechaza_sin_error_interno(app):
    client = app.test_client()
    csrf(client)
    response = client.post("/auth/login", data={"csrf_token": "token-inválido"})
    assert response.status_code == 400

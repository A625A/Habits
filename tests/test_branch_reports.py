import secrets

import psycopg
from test_auth_http import login, register


def test_comparacion_core_usa_datos_reales_y_no_simula_modulos(admin_app, admin_password):
    client = admin_app.test_client()
    assert client.get("/reportes/sucursales").status_code == 401
    login(client, admin_password)
    response = client.get("/reportes/sucursales")
    assert response.status_code == 200
    assert response.json["estado_operativo"] == "pendiente_modulos"
    rows = response.json["sucursales"]
    assert [(r["codigo"], r["usuarios_totales"], r["usuarios_activos"]) for r in rows] == [
        ("DEMO-01", 1, 1),
        ("DEMO-02", 0, 0),
    ]
    assert all(
        r["reservas"] is None and r["ventas"] is None and r["importe_ventas"] is None for r in rows
    )
    assert register(client, secrets.token_urlsafe(24)).status_code == 303
    rows = client.get("/reportes/sucursales").json["sucursales"]
    assert rows[0]["usuarios_totales"] == 2
    assert rows[0]["meseros_activos"] == 1


def test_gerente_ve_solo_su_sede_y_mesero_no_accede(admin_app, admin_password, database_url):
    admin = admin_app.test_client()
    login(admin, admin_password)
    password = secrets.token_urlsafe(24)
    register(admin, password, "gerente")
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "UPDATE usuarios SET sucursal_id = (SELECT sucursal_id FROM sucursales WHERE codigo = 'DEMO-02') WHERE email = 'personal@example.test'"
        )
    manager = admin_app.test_client()
    login(manager, password, "personal@example.test")
    response = manager.get("/reportes/sucursales?sucursal_id=1")
    assert response.status_code == 200
    assert [r["codigo"] for r in response.json["sucursales"]] == ["DEMO-02"]
    register(admin, password, "mesero", "mesero@example.test")
    waiter = admin_app.test_client()
    login(waiter, password, "mesero@example.test")
    assert waiter.get("/reportes/sucursales").status_code == 403

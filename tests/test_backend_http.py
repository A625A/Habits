"""Contrato HTTP de Fase 2 sobre PostgreSQL real y datos exclusivamente efímeros."""

import re
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

SQL = Path(__file__).resolve().parents[1] / "sql"


@pytest.fixture
def backend_app(admin_app, database_url):
    with psycopg.connect(database_url, autocommit=True) as conn:
        schema = conn.execute("SELECT current_schema()").fetchone()[0]
        conn.execute("CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public")
        conn.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
        with conn.transaction():
            for path in sorted((SQL / "fase1").glob("[0-9]*.sql")):
                conn.execute(path.read_text())
            conn.execute((SQL / "fase1/cargar_catalogo.sql").read_text())
            for path in sorted((SQL / "fase2").glob("[0-9]*.sql")):
                conn.execute(path.read_text())
    return admin_app


def authenticate(app, password, email="admin@example.test"):
    client = app.test_client()
    page = client.get("/auth/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert (
        client.post(
            "/auth/login",
            data={
                "email": email,
                "password": password,
                "csrf_token": token,
            },
        ).status_code
        == 303
    )
    page = client.get("/auth/cuenta")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    client.environ_base["HTTP_X_CSRF_TOKEN"] = token
    return client


@pytest.fixture
def api(backend_app, admin_password):
    return authenticate(backend_app, admin_password)


def create(api, url, payload):
    response = api.post(url, json=payload)
    assert response.status_code == 201, response.text
    return response.json


def test_registrar_buscar_actualizar_y_desactivar_cliente(api):
    customer = create(api, "/clientes", {"nombre": "Ana prueba", "telefono": "TEST-123"})
    cid = customer["cliente_id"]
    assert api.get("/clientes?q=TEST-123").json["clientes"][0]["cliente_id"] == cid
    assert api.patch(f"/clientes/{cid}", json={"email": "ana@example.test"}).status_code == 200
    assert api.get(f"/clientes/{cid}").json["email"] == "ana@example.test"
    assert api.patch(f"/clientes/{cid}", json={"activo": False}).status_code == 200
    assert api.get(f"/clientes/{cid}").json["activo"] is False
    assert api.get("/clientes?activo=false").json["clientes"][0]["cliente_id"] == cid
    assert api.get(f"/clientes/{cid}/historial").json == {
        "reservas": [],
        "visitas": [],
        "compras": [],
    }


def test_preferencias_y_observaciones_se_consultan_y_actualizan(api):
    customer = create(api, "/clientes", {"nombre": "Ana", "email": "ana@example.test"})
    cid = customer["cliente_id"]
    products = api.get("/catalogo/productos")
    assert products.status_code == 200
    product = products.json["productos"][0]["producto_id"]
    url = f"/clientes/{cid}/preferencias/{product}"
    assert api.put(url, json={"nota_preferencia": "Sin azúcar"}).status_code == 200
    assert (
        api.get(f"/clientes/{cid}/preferencias").json["preferencias"][0]["nota_preferencia"]
        == "Sin azúcar"
    )
    note = create(
        api, f"/clientes/{cid}/observaciones", {"observacion": "Prefiere atención en terraza"}
    )
    assert (
        api.patch(
            f"/clientes/{cid}/observaciones/{note['observacion_id']}",
            json={"observacion": "Prefiere interior"},
        ).status_code
        == 200
    )
    assert (
        api.get(f"/clientes/{cid}/observaciones").json["observaciones"][0]["observacion"]
        == "Prefiere interior"
    )
    assert api.delete(url).status_code == 200
    assert api.get(f"/clientes/{cid}/preferencias").json["preferencias"] == []


@pytest.fixture
def attention(api):
    branches = api.get("/sucursales").json["sucursales"]
    customer = create(api, "/clientes", {"nombre": "Cliente atención", "telefono": "TEST"})
    table = create(
        api, "/mesas", {"sucursal_id": branches[0]["sucursal_id"], "numero_mesa": 1, "capacidad": 4}
    )
    return branches, customer, table


def reservation_payload(attention, **changes):
    branches, customer, table = attention
    return {
        "sucursal_id": branches[0]["sucursal_id"],
        "cliente_id": customer["cliente_id"],
        "mesa_id": table["mesa_id"],
        "fecha_inicio": "2030-01-01T10:00:00-06:00",
        "personas": 2,
        **changes,
    }


def test_reserva_conflicto_cancelacion_llegada_y_visita_sin_reserva(api, attention):
    payload = reservation_payload(attention)
    reserve = create(api, "/reservas", payload)
    rid = reserve["reserva_id"]
    assert reserve["estado"] == "confirmada"
    assert api.get("/visitas").json["visitas"] == []
    assert api.post("/reservas", json=payload).status_code == 409
    assert (
        api.get("/reservas?fecha=2030-01-01&estado=confirmada").json["reservas"][0]["reserva_id"]
        == rid
    )
    assert api.post(f"/reservas/{rid}/cancelar").status_code == 200
    reserve = create(api, "/reservas", payload)
    visit = create(api, f"/reservas/{reserve['reserva_id']}/llegada", {})
    assert visit["reserva_id"] == reserve["reserva_id"]
    assert api.get(f"/reservas/{reserve['reserva_id']}").json["estado"] == "completada"
    assert api.post("/reservas", json=payload).status_code == 409
    assert api.post(f"/reservas/{reserve['reserva_id']}/llegada").status_code == 409
    create(
        api,
        "/visitas",
        {
            "sucursal_id": payload["sucursal_id"],
            "cliente_id": payload["cliente_id"],
            "tipo": "llevar",
        },
    )
    history = api.get(f"/clientes/{payload['cliente_id']}/historial").json
    assert len(history["visitas"]) == 2
    assert len(history["reservas"]) == 2
    assert history["compras"] == []


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"personas": 5}, 409),
        ({"fecha_fin": "2030-01-01T11:00:00-06:00"}, 400),
        ({"fecha_inicio": "2030-01-01T10:00:00"}, 400),
        ({"estado": "completada"}, 400),
    ],
)
def test_reservas_rechazan_capacidad_duracion_y_estado_inyectados(api, attention, change, expected):
    assert (
        api.post("/reservas", json=reservation_payload(attention, **change)).status_code == expected
    )


def test_mesa_de_otra_sucursal_rechazada_y_reserva_adyacente_valida(api, attention):
    assert (
        api.post(
            "/reservas",
            json=reservation_payload(attention, sucursal_id=attention[0][1]["sucursal_id"]),
        ).status_code
        == 400
    )
    create(api, "/reservas", reservation_payload(attention))
    create(
        api, "/reservas", reservation_payload(attention, fecha_inicio="2030-01-01T11:30:00-06:00")
    )


def test_catalogo_precios_recetas_e_ingredientes(api):
    products = api.get("/catalogo/productos").json["productos"]
    assert len(products) == 12
    assert products[0]["codigo"] == "HAB-01" and products[0]["precio"] == "26.00"
    pid = products[0]["producto_id"]
    assert api.patch(f"/catalogo/productos/{pid}", json={"precio": "27.50"}).status_code == 200
    ingredient = create(api, "/catalogo/ingredientes", {"nombre": "Insumo prueba", "unidad": "g"})
    recipe = {
        "ingredientes": [{"ingrediente_id": ingredient["ingrediente_id"], "cantidad": "5.000"}]
    }
    assert api.put(f"/catalogo/productos/{pid}/receta", json=recipe).status_code == 200
    assert (
        api.get(f"/catalogo/productos/{pid}/receta").json["ingredientes"][0]["cantidad"] == "5.000"
    )
    # Una sustitución inválida conserva íntegra la receta anterior.
    bad = {"ingredientes": [{"ingrediente_id": 9223372036854775806, "cantidad": "2"}]}
    assert api.put(f"/catalogo/productos/{pid}/receta", json=bad).status_code == 400
    assert (
        api.get(f"/catalogo/productos/{pid}/receta").json["ingredientes"][0]["cantidad"] == "5.000"
    )
    assert (
        api.patch(
            f"/catalogo/ingredientes/{ingredient['ingrediente_id']}", json={"unidad": "ml"}
        ).status_code
        == 409
    )


@pytest.fixture
def inventory(api):
    branch = api.get("/sucursales").json["sucursales"][0]["sucursal_id"]
    products = api.get("/catalogo/productos").json["productos"]
    ingredient = create(
        api, "/catalogo/ingredientes", {"nombre": "Ingrediente sintético", "unidad": "g"}
    )
    for product in [products[0], products[6]]:
        assert (
            api.put(
                f"/catalogo/productos/{product['producto_id']}/receta",
                json={
                    "ingredientes": [
                        {"ingrediente_id": ingredient["ingrediente_id"], "cantidad": "5"}
                    ],
                },
            ).status_code
            == 200
        )
    config = create(
        api,
        "/inventario/configuraciones",
        {
            "sucursal_id": branch,
            "ingrediente_id": ingredient["ingrediente_id"],
            "cantidad_referencia": "100",
        },
    )
    return branch, products[0]["producto_id"], products[6]["producto_id"], config["inventario_id"]


def local_day(delta=0):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    return (datetime.now(ZoneInfo("America/Guatemala")).date() + timedelta(days=delta)).isoformat()


def receive(api, inventory_id, quantity, days=3):
    return create(
        api,
        "/inventario/recepciones",
        {
            "inventario_id": inventory_id,
            "cantidad": str(quantity),
            "fecha_vencimiento": local_day(days),
        },
    )


def test_recepcion_produccion_fefo_vencimiento_y_alertas(api, inventory):
    branch, _beverage, bread, iid = inventory
    later = receive(api, iid, 10, 5)
    early = receive(api, iid, 10, 0)
    expired = receive(api, iid, 100, -1)
    stock = api.get("/inventario/existencias").json["ingredientes"][0]
    assert stock["cantidad_disponible"] == "20.000"
    production = create(
        api,
        "/producciones",
        {
            "sucursal_id": branch,
            "producto_id": bread,
            "cantidad": 3,
            "fecha_vencimiento": local_day(2),
        },
    )
    assert production["cantidad_disponible"] == 3
    lots = {r["lote_id"]: r for r in api.get("/inventario/lotes").json["lotes"]}
    assert lots[early["lote_id"]]["cantidad_disponible"] == "0.000"
    assert lots[later["lote_id"]]["cantidad_disponible"] == "5.000"
    assert lots[expired["lote_id"]]["cantidad_disponible"] == "100.000"
    alerts = api.get("/inventario/alertas?dias=7").json
    assert alerts["stock_bajo"][0]["cantidad_disponible"] == "5.000"
    assert alerts["ingredientes_por_vencer"][0]["lote_id"] == later["lote_id"]
    assert alerts["terminados_por_vencer"][0]["produccion_id"] == production["produccion_id"]
    assert alerts["ingredientes_vencidos"][0]["lote_id"] == expired["lote_id"]
    response = api.post(
        "/producciones",
        json={
            "sucursal_id": branch,
            "producto_id": bread,
            "cantidad": 2,
            "fecha_vencimiento": local_day(2),
        },
    )
    assert response.status_code == 409
    assert len(api.get("/producciones").json["producciones"]) == 1
    assert (
        api.get("/inventario/existencias").json["ingredientes"][0]["cantidad_disponible"] == "5.000"
    )


def test_venta_mixta_precio_historico_y_rollback_completo(api, inventory):
    branch, beverage, bread, iid = inventory
    receive(api, iid, 50)
    create(
        api,
        "/producciones",
        {
            "sucursal_id": branch,
            "producto_id": bread,
            "cantidad": 2,
            "fecha_vencimiento": local_day(2),
        },
    )
    sale = create(
        api,
        "/ventas",
        {
            "sucursal_id": branch,
            "tipo": "llevar",
            "lineas": [
                {"producto_id": beverage, "cantidad": 2},
                {"producto_id": bread, "cantidad": 1},
            ],
        },
    )
    sid = sale["venta_id"]
    assert sale["total"] == "74.00"
    assert (
        api.get("/inventario/existencias").json["ingredientes"][0]["cantidad_disponible"]
        == "30.000"
    )
    assert api.patch(f"/catalogo/productos/{beverage}", json={"precio": "99"}).status_code == 200
    assert api.get(f"/ventas/{sid}").json["total"] == "74.00"
    failure = api.post(
        "/ventas",
        json={
            "sucursal_id": branch,
            "tipo": "llevar",
            "lineas": [
                {"producto_id": beverage, "cantidad": 1},
                {"producto_id": bread, "cantidad": 2},
            ],
        },
    )
    assert failure.status_code == 409
    assert len(api.get("/ventas").json["ventas"]) == 1
    assert (
        api.get("/inventario/existencias").json["ingredientes"][0]["cantidad_disponible"]
        == "30.000"
    )
    assert api.get("/inventario/terminados").json["terminados"][0]["cantidad_disponible"] == 1


def test_venta_identificada_reutiliza_visita_y_no_duplica_frecuencia(api, inventory, attention):
    branch, beverage, _, iid = inventory
    receive(api, iid, 20)
    visit = create(
        api,
        "/visitas",
        {"sucursal_id": branch, "cliente_id": attention[1]["cliente_id"], "tipo": "llevar"},
    )
    data = {
        "sucursal_id": branch,
        "visita_id": visit["visita_id"],
        "tipo": "llevar",
        "lineas": [{"producto_id": beverage, "cantidad": 1}],
    }
    create(api, "/ventas", data)
    create(api, "/ventas", data)
    history = api.get(f"/clientes/{attention[1]['cliente_id']}/historial").json
    assert len(history["visitas"]) == 1 and len(history["compras"]) == 2


def staff_client(api, app, password, role):
    page = api.get("/auth/register")
    branch = re.search(r'<option value="(\d+)"', page.text).group(1)
    response = api.post(
        "/auth/register",
        data={
            "nombre": "Personal prueba",
            "email": f"{role}@example.test",
            "password": password,
            "rol": role,
            "sucursal_id": branch,
        },
    )
    assert response.status_code == 303
    return authenticate(app, password, f"{role}@example.test")


@pytest.mark.parametrize("role", ["gerente", "mesero"])
def test_permisos_y_aislamiento_de_sucursal(api, backend_app, admin_password, attention, role):
    staff = staff_client(api, backend_app, admin_password, role)
    foreign_branch = attention[0][1]["sucursal_id"]
    table = create(api, "/mesas", {"sucursal_id": foreign_branch, "numero_mesa": 1, "capacidad": 4})
    reserve = create(
        api,
        "/reservas",
        reservation_payload(attention, sucursal_id=foreign_branch, mesa_id=table["mesa_id"]),
    )
    visit = create(
        api,
        "/visitas",
        {"sucursal_id": foreign_branch, "cliente_id": attention[1]["cliente_id"], "tipo": "llevar"},
    )
    for path in [
        "/sucursales",
        "/mesas",
        "/reservas",
        "/visitas",
        "/ventas",
        "/inventario/terminados",
    ]:
        response = staff.get(path)
        assert response.status_code == 200
        assert all(r["sucursal_id"] != foreign_branch for r in next(iter(response.json.values())))
    for path in [
        f"/reservas/{reserve['reserva_id']}",
        f"/visitas/{visit['visita_id']}",
        f"/reservas?sucursal_id={foreign_branch}",
    ]:
        assert staff.get(path).status_code == 403
    assert staff.post(f"/reservas/{reserve['reserva_id']}/cancelar").status_code == 403
    assert staff.post(f"/reservas/{reserve['reserva_id']}/llegada").status_code == 403
    assert staff.get(f"/clientes/{attention[1]['cliente_id']}/historial").json["visitas"] == []
    assert (
        staff.post(
            "/catalogo/ingredientes", json={"nombre": "No autorizado", "unidad": "g"}
        ).status_code
        == 403
    )
    assert staff.get("/inventario/existencias").status_code == (200 if role == "gerente" else 403)
    assert (
        staff.post(
            "/producciones",
            json={
                "sucursal_id": foreign_branch,
                "producto_id": 1,
                "cantidad": 1,
                "fecha_vencimiento": local_day(1),
            },
        ).status_code
        == 403
    )
    assert (
        staff.post(
            "/ventas",
            json={
                "sucursal_id": foreign_branch,
                "tipo": "llevar",
                "lineas": [{"producto_id": 1, "cantidad": 1}],
            },
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "path",
    [
        "/clientes",
        "/reservas",
        "/visitas",
        "/catalogo/productos",
        "/inventario/existencias",
        "/producciones",
        "/ventas",
    ],
)
def test_api_exige_autenticacion_json(backend_app, path):
    response = backend_app.test_client().get(path)
    assert response.status_code == 401
    assert response.is_json


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/clientes", {"nombre": "X", "telefono": "TEST"}),
        ("patch", "/clientes/1", {"activo": False}),
        ("put", "/clientes/1/preferencias/1", {"nota_preferencia": "X"}),
        ("delete", "/clientes/1/preferencias/1", None),
        ("post", "/reservas/1/cancelar", None),
        ("post", "/reservas/1/llegada", None),
        ("post", "/inventario/recepciones", {}),
        ("post", "/producciones", {}),
        ("post", "/ventas", {}),
    ],
)
def test_csrf_obligatorio_en_todas_las_mutaciones(api, method, path, payload):
    response = getattr(api, method)(path, json=payload, headers={"X-CSRF-Token": "incorrecto"})
    assert response.status_code == 400 and response.is_json


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"nombre": []},
        {"nombre": True},
        {"nombre": "X", "telefono": "TEST", "usuario_id": 1},
        {"nombre": "X", "telefono": "TEST", "activo": "false"},
        {"nombre": "Sin contacto"},
        {"nombre": " "},
    ],
)
def test_cliente_rechaza_entrada_invalida_sin_500(api, payload):
    response = api.post("/clientes", json=payload)
    assert response.status_code in {400, 415}
    assert response.is_json
    assert "SELECT" not in response.text and "INSERT" not in response.text


def test_cliente_inactivo_conserva_historial_y_no_admite_reserva(api, attention):
    reserve = create(api, "/reservas", reservation_payload(attention))
    customer = attention[1]["cliente_id"]
    assert api.patch(f"/clientes/{customer}", json={"activo": False}).status_code == 200
    assert len(api.get(f"/clientes/{customer}/historial").json["reservas"]) == 1
    assert (
        api.post(
            "/reservas",
            json=reservation_payload(attention, fecha_inicio="2030-01-02T10:00:00-06:00"),
        ).status_code
        == 409
    )
    assert api.post(f"/reservas/{reserve['reserva_id']}/llegada").status_code == 409
    assert api.get("/visitas").json["visitas"] == []


def concurrent_requests(app, api, path, payload):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2)
    cookie = api.get_cookie(app.config["SESSION_COOKIE_NAME"])
    token = api.environ_base["HTTP_X_CSRF_TOKEN"]

    def perform():
        client = app.test_client()
        client.set_cookie(app.config["SESSION_COOKIE_NAME"], cookie.value)
        barrier.wait(timeout=5)
        return client.post(path, json=payload, headers={"X-CSRF-Token": token}).status_code

    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(perform) for _ in range(2)]
        return sorted(future.result(timeout=10) for future in futures)


def test_concurrencia_http_no_reserva_doble(api, backend_app, attention):
    assert concurrent_requests(backend_app, api, "/reservas", reservation_payload(attention)) == [
        201,
        409,
    ]
    assert len(api.get("/reservas").json["reservas"]) == 1


def test_concurrencia_http_no_vende_mas_stock(api, backend_app, inventory):
    branch, beverage, _, iid = inventory
    receive(api, iid, 5)
    data = {
        "sucursal_id": branch,
        "tipo": "llevar",
        "lineas": [{"producto_id": beverage, "cantidad": 1}],
    }
    assert concurrent_requests(backend_app, api, "/ventas", data) == [201, 409]
    assert len(api.get("/ventas").json["ventas"]) == 1
    assert (
        api.get("/inventario/existencias").json["ingredientes"][0]["cantidad_disponible"] == "0.000"
    )


def test_instalacion_backend_repetible_y_rol_sin_dml_de_saldos(backend_app, database_url):
    result = backend_app.test_cli_runner().invoke(args=["db-backend-upgrade"])
    assert result.exit_code == 0, result.output
    assert backend_app.test_cli_runner().invoke(args=["db-backend-upgrade"]).exit_code == 0
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("SET ROLE habits_operaciones")
        for query in [
            "UPDATE lotes_ingrediente SET cantidad_disponible=0",
            "UPDATE producciones SET cantidad_disponible=0",
            "DELETE FROM ventas",
            "DELETE FROM detalle_ventas",
            "SELECT password_hash FROM usuarios",
            "SELECT * FROM sesiones",
            "DELETE FROM auditoria",
        ]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(query)


def test_errores_de_ruta_y_metodo_son_json(api):
    for response in [api.get("/clientes/no-existe"), api.delete("/ventas/1")]:
        assert response.status_code in {404, 405} and response.is_json


def test_filtros_excesivos_son_400_y_token_csrf_json(api):
    assert api.get("/reservas?sucursal_id=" + "9" * 5000).status_code == 400
    assert api.get("/clientes?offset=" + "9" * 5000).status_code == 400
    assert api.get("/auth/csrf").json["csrf_token"] == api.environ_base["HTTP_X_CSRF_TOKEN"]


@pytest.mark.parametrize(
    "lines",
    [
        [],
        {},
        [{"producto_id": 1, "cantidad": 0}],
        [{"producto_id": 1, "cantidad": True}],
        [{"producto_id": 1, "cantidad": 1.5}],
        [{"producto_id": 1, "cantidad": 1, "precio_unitario": 1}],
        [{"producto_id": 1, "cantidad": 2147483648}],
        [None],
    ],
)
def test_ventas_rechazan_cantidades_y_precios_enviados_por_cliente(api, lines):
    branch = api.get("/sucursales").json["sucursales"][0]["sucursal_id"]
    response = api.post("/ventas", json={"sucursal_id": branch, "tipo": "llevar", "lineas": lines})
    assert response.status_code == 400
    assert api.get("/ventas").json["ventas"] == []


@pytest.mark.parametrize("quantity", ["NaN", "Infinity", "0.0001", True, -1, {}, []])
def test_recetas_rechazan_cantidades_no_representables(api, quantity):
    product = api.get("/catalogo/productos").json["productos"][0]["producto_id"]
    response = api.put(
        f"/catalogo/productos/{product}/receta",
        json={"ingredientes": [{"ingrediente_id": 1, "cantidad": quantity}]},
    )
    assert response.status_code == 400


def test_gerente_produce_y_mesero_vende_en_su_sucursal(api, backend_app, admin_password, inventory):
    branch, beverage, bread, iid = inventory
    manager = staff_client(api, backend_app, admin_password, "gerente")
    waiter = staff_client(api, backend_app, admin_password, "mesero")
    receive(manager, iid, 20)
    create(
        manager,
        "/producciones",
        {
            "sucursal_id": branch,
            "producto_id": bread,
            "cantidad": 1,
            "fecha_vencimiento": local_day(1),
        },
    )
    sale = create(
        waiter,
        "/ventas",
        {
            "sucursal_id": branch,
            "tipo": "llevar",
            "lineas": [
                {"producto_id": beverage, "cantidad": 1},
                {"producto_id": bread, "cantidad": 1},
            ],
        },
    )
    assert sale["total"] == "48.00"
    assert waiter.get(f"/ventas/{sale['venta_id']}").status_code == 200
    assert (
        waiter.post(
            "/inventario/recepciones",
            json={"inventario_id": iid, "cantidad": "1", "fecha_vencimiento": local_day(1)},
        ).status_code
        == 403
    )


def test_venta_sin_receta_y_terminado_vencido_no_consumen(api, inventory, database_url):
    branch, _beverage, bread, _iid = inventory
    # Datos históricos exclusivamente en la base de pruebas; el HTTP no permite retrofechar.
    with psycopg.connect(database_url) as conn:
        actor = api.get("/auth/me").json["usuario_id"]
        conn.execute(
            """INSERT INTO producciones(sucursal_id,producto_id,usuario_id,
            producida_en,fecha_vencimiento,cantidad_producida,cantidad_disponible)
            VALUES (%s,%s,%s,CURRENT_TIMESTAMP-interval '3 days',%s,2,2)""",
            (branch, bread, actor, local_day(-1)),
        )
    payload = {
        "sucursal_id": branch,
        "tipo": "llevar",
        "lineas": [{"producto_id": bread, "cantidad": 1}],
    }
    assert api.post("/ventas", json=payload).status_code == 409
    products = api.get("/catalogo/productos").json["productos"]
    payload["lineas"] = [{"producto_id": products[1]["producto_id"], "cantidad": 1}]
    assert api.post("/ventas", json=payload).status_code == 409
    assert api.get("/ventas").json["ventas"] == []
    assert api.get("/inventario/alertas").json["terminados_vencidos"][0]["cantidad_disponible"] == 2


def test_fefo_terminados_y_agrupacion_de_lineas(api, inventory):
    branch, _, bread, iid = inventory
    receive(api, iid, 20)
    later = create(
        api,
        "/producciones",
        {
            "sucursal_id": branch,
            "producto_id": bread,
            "cantidad": 2,
            "fecha_vencimiento": local_day(3),
        },
    )
    early = create(
        api,
        "/producciones",
        {
            "sucursal_id": branch,
            "producto_id": bread,
            "cantidad": 2,
            "fecha_vencimiento": local_day(0),
        },
    )
    sale = create(
        api,
        "/ventas",
        {
            "sucursal_id": branch,
            "tipo": "llevar",
            "lineas": [
                {"producto_id": bread, "cantidad": 1},
                {"producto_id": bread, "cantidad": 2},
            ],
        },
    )
    assert len(sale["lineas"]) == 1 and sale["lineas"][0]["cantidad"] == 3
    assert api.get(f"/producciones/{early['produccion_id']}").json["cantidad_disponible"] == 0
    assert api.get(f"/producciones/{later['produccion_id']}").json["cantidad_disponible"] == 1
    assert (
        api.get("/inventario/existencias").json["ingredientes"][0]["cantidad_disponible"] == "0.000"
    )


def test_auditoria_http_atribuye_actor_y_rollback_no_deja_eventos(api, inventory, database_url):
    branch, beverage, bread, iid = inventory
    receive(api, iid, 20)
    actor = api.get("/auth/me").json["usuario_id"]
    with psycopg.connect(database_url, autocommit=True) as conn:
        event = conn.execute(
            "SELECT usuario_id FROM auditoria WHERE tabla='lotes_ingrediente'"
        ).fetchone()
        assert event == (actor,)
        before = conn.execute("SELECT count(*) FROM auditoria").fetchone()[0]
        response = api.post(
            "/ventas",
            json={
                "sucursal_id": branch,
                "tipo": "llevar",
                "lineas": [
                    {"producto_id": beverage, "cantidad": 1},
                    {"producto_id": bread, "cantidad": 1},
                ],
            },
        )
        assert response.status_code == 409
        assert conn.execute("SELECT count(*) FROM auditoria").fetchone()[0] == before
    assert (
        api.get("/inventario/existencias").json["ingredientes"][0]["cantidad_disponible"]
        == "20.000"
    )


def test_sesion_revocada_no_puede_modificar_clientes(api, database_url):
    with psycopg.connect(database_url) as conn:
        conn.execute("UPDATE usuarios SET activo=false")
    assert api.post("/clientes", json={"nombre": "X", "telefono": "TEST"}).status_code == 401


def test_http_real_en_loopback_con_cookie_login_csrf_y_json(backend_app, admin_password):
    import json
    from http.cookiejar import CookieJar
    from threading import Thread
    from urllib.parse import urlencode
    from urllib.request import HTTPCookieProcessor, Request, build_opener

    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", 0, backend_app)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}"
    http = build_opener(HTTPCookieProcessor(CookieJar()))

    def read(path):
        with http.open(url + path, timeout=5) as response:
            assert response.headers["Cache-Control"] == "no-store"
            return json.load(response)

    try:
        token = read("/auth/csrf")["csrf_token"]
        data = urlencode(
            {"email": "admin@example.test", "password": admin_password, "csrf_token": token}
        ).encode()
        with http.open(Request(url + "/auth/login", data=data), timeout=5) as response:
            assert response.status == 200
        token = read("/auth/csrf")["csrf_token"]
        request = Request(
            url + "/clientes",
            data=json.dumps({"nombre": "Cliente HTTP real", "telefono": "TEST"}).encode(),
            headers={"Content-Type": "application/json", "X-CSRF-Token": token},
        )
        with http.open(request, timeout=5) as response:
            assert response.status == 201
            customer = json.load(response)
        assert read(f"/clientes/{customer['cliente_id']}")["nombre"] == "Cliente HTTP real"
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()

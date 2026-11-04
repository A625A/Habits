import secrets
from datetime import date, datetime, time
from pathlib import Path

import psycopg
import pytest
from flask import Flask
from psycopg import sql
from test_auth_http import login, register

from app.routes.reportes import GUATEMALA, _load_reports, _month_after, _parse_filters

SQL = Path(__file__).resolve().parents[1] / "sql"


def test_filtros_validos_conservan_intervalo_exclusivo_y_zona_horaria():
    app = Flask(__name__)
    with app.test_request_context("/reportes?desde=2030-01-01&hasta=2030-02-01&mes=2030-01"):
        parsed, values, error = _parse_filters()

    assert error is None
    assert parsed is not None
    assert parsed["desde"].isoformat() == "2030-01-01T00:00:00-06:00"
    assert parsed["hasta"].isoformat() == "2030-02-01T00:00:00-06:00"
    assert parsed["mes"] == date(2030, 1, 1)
    assert values == {"desde": "2030-01-01", "hasta": "2030-02-01", "mes": "2030-01"}


def test_filtros_invalidos_no_intentan_preparar_consulta():
    app = Flask(__name__)
    with app.test_request_context("/reportes?desde=2030-02-01&hasta=2030-01-01&mes=2030-01"):
        parsed, _values, error = _parse_filters()

    assert parsed is None
    assert error is not None


@pytest.fixture
def reports_app(admin_app, database_url):
    with psycopg.connect(database_url, autocommit=True) as conn:
        schema = conn.execute("SELECT current_schema()").fetchone()[0]
        conn.execute("CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public")
        conn.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
        with conn.transaction():
            for path in sorted((SQL / "fase1").glob("[0-9]*.sql")):
                conn.execute(path.read_text(encoding="utf-8"))
            conn.execute((SQL / "fase1" / "cargar_catalogo.sql").read_text(encoding="utf-8"))

    result = admin_app.test_cli_runner().invoke(args=["db-backend-upgrade"])
    assert result.exit_code == 0, result.output
    return admin_app


def _seed_report_rows(database_url):
    today = datetime.now(GUATEMALA).date()
    visit_at = datetime.combine(today, time.min, GUATEMALA)
    reservation_at = datetime.combine(today, time(10), GUATEMALA)
    upper_bound = datetime.combine(_month_after(today.replace(day=1)), time.min, GUATEMALA)
    with psycopg.connect(database_url) as conn:
        branch = conn.execute(
            "SELECT sucursal_id FROM sucursales WHERE codigo='DEMO-01'"
        ).fetchone()[0]
        user = conn.execute(
            "SELECT usuario_id FROM usuarios WHERE email='admin@example.test'"
        ).fetchone()[0]
        product = conn.execute(
            "SELECT producto_id FROM productos WHERE codigo='HAB-01'"
        ).fetchone()[0]
        customer = conn.execute(
            """INSERT INTO clientes(nombre,email) VALUES
            ('Cliente reportes','reportes@example.test') RETURNING cliente_id"""
        ).fetchone()[0]
        table = conn.execute(
            """INSERT INTO mesas(sucursal_id,numero_mesa,capacidad)
            VALUES (%s,99,4) RETURNING mesa_id""",
            (branch,),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO reservas(sucursal_id,mesa_id,cliente_id,fecha_inicio,fecha_fin,
            personas,estado) VALUES (%s,%s,%s,%s,%s + interval '90 minutes',
            2,'confirmada')""",
            (branch, table, customer, reservation_at, reservation_at),
        )
        conn.execute(
            """INSERT INTO visitas(cliente_id,sucursal_id,usuario_id,tipo,atendida_en)
            VALUES (%s,%s,%s,'llevar',%s)""",
            (customer, branch, user, visit_at),
        )
        conn.execute(
            """INSERT INTO preferencias_cliente(cliente_id,producto_id,nota_preferencia)
            VALUES (%s,%s,'Preferido')""",
            (customer, product),
        )
        ingredient = conn.execute(
            "INSERT INTO ingredientes(nombre,unidad) VALUES ('Ingrediente reportes','g') RETURNING ingrediente_id"
        ).fetchone()[0]
        inventory = conn.execute(
            """INSERT INTO inventario_ingrediente(sucursal_id,ingrediente_id,cantidad_referencia)
            VALUES (%s,%s,100) RETURNING inventario_id""",
            (branch, ingredient),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO lotes_ingrediente(inventario_id,usuario_id,fecha_vencimiento,
            cantidad_inicial,cantidad_disponible) VALUES (%s,%s,%s,10,10)""",
            (inventory, user, today),
        )
        sale = conn.execute(
            """INSERT INTO ventas(sucursal_id,usuario_id,tipo,fecha)
            VALUES (%s,%s,'llevar',%s) RETURNING venta_id""",
            (branch, user, visit_at),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO detalle_ventas(venta_id,producto_id,cantidad,precio_unitario)
            VALUES (%s,%s,2,26)""",
            (sale, product),
        )
        excluded_sale = conn.execute(
            """INSERT INTO ventas(sucursal_id,usuario_id,tipo,fecha)
            VALUES (%s,%s,'llevar',%s) RETURNING venta_id""",
            (branch, user, upper_bound),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO detalle_ventas(venta_id,producto_id,cantidad,precio_unitario)
            VALUES (%s,%s,5,26)""",
            (excluded_sale, product),
        )
    return today.replace(day=1)


def test_inicio_exige_sesion_y_reportes_solo_permite_administrador(reports_app, admin_password):
    anonymous = reports_app.test_client()
    assert anonymous.get("/").status_code == 302
    assert anonymous.get("/").headers["Location"].endswith("/auth/login")
    assert anonymous.get("/reportes").status_code == 401

    admin = reports_app.test_client()
    assert login(admin, admin_password).status_code == 303
    assert admin.get("/").status_code == 200
    assert admin.get("/reportes").status_code == 200

    password = secrets.token_urlsafe(24)
    assert register(admin, password, "gerente", "gerente@example.test").status_code == 303
    manager = reports_app.test_client()
    assert login(manager, password, "gerente@example.test").status_code == 303
    assert manager.get("/").status_code == 200
    assert 'href="/reportes"' not in manager.get("/auth/cuenta").text
    assert manager.get("/reportes").status_code == 403

    assert register(admin, password, "mesero", "mesero@example.test").status_code == 303
    waiter = reports_app.test_client()
    assert login(waiter, password, "mesero@example.test").status_code == 303
    assert waiter.get("/reportes").status_code == 403


@pytest.mark.parametrize(
    "query",
    [
        "desde=fecha&hasta=2030-02-01&mes=2030-01",
        "desde=2030-02-01&hasta=2030-01-01&mes=2030-01",
        "desde=2030-01-01&hasta=2030-02-01&mes=2030-13",
    ],
)
def test_reportes_rechaza_filtros_invalidos(reports_app, admin_password, query):
    client = reports_app.test_client()
    login(client, admin_password)
    assert client.get(f"/reportes?{query}").status_code == 400


def test_reportes_vacios_no_se_confunden_con_error(reports_app, admin_password):
    client = reports_app.test_client()
    login(client, admin_password)
    response = client.get("/reportes?desde=2030-01-01&hasta=2030-02-01&mes=2030-01")
    assert response.status_code == 200
    filters = {
        "desde": datetime(2030, 1, 1, tzinfo=GUATEMALA),
        "hasta": datetime(2030, 2, 1, tzinfo=GUATEMALA),
        "mes": date(2030, 1, 1),
    }
    with reports_app.app_context():
        reports = _load_reports(filters)
    assert reports["productos"] == []
    assert reports["frecuentes"] == []
    assert reports["reservas"] == []
    assert reports["inventario"] == []
    assert len(reports["sucursales"]) == 2
    assert all(row["reservas"] == row["ventas"] == 0 for row in reports["sucursales"])


def test_consulta_real_consume_las_cinco_funciones(reports_app, database_url):
    month = _seed_report_rows(database_url)
    filters = {
        "desde": datetime.combine(month, time.min, GUATEMALA),
        "hasta": datetime.combine(_month_after(month), time.min, GUATEMALA),
        "mes": month,
    }
    with reports_app.app_context():
        reports = _load_reports(filters)

    assert len(reports["productos"]) == 1
    assert reports["productos"][0]["unidades"] == 2
    assert reports["productos"][0]["importe"] == 52

    assert len(reports["frecuentes"]) == 1
    assert reports["frecuentes"][0]["visitas"] == 1

    assert len(reports["reservas"]) == 1
    assert reports["reservas"][0]["confirmadas"] == 1
    assert reports["reservas"][0]["completadas"] == 0
    assert reports["reservas"][0]["reservas"] == 1
    assert reports["reservas"][0]["preferencias"] == ["Latte de cardamomo y miel"]

    assert len(reports["inventario"]) == 1
    inventory = reports["inventario"][0]
    assert inventory["unidad"] == "g"
    assert inventory["disponible_actual"] == 10
    assert inventory["referencia"] == 100
    assert inventory["saldo_lote"] == 10
    assert inventory["bajo_stock"] is True

    assert len(reports["sucursales"]) == 2
    first, second = reports["sucursales"]
    assert (first["reservas"], first["ventas"], first["importe"]) == (1, 1, 52)
    assert (second["reservas"], second["ventas"], second["importe"]) == (0, 0, 0)


def test_falla_de_base_devuelve_estado_distinto_de_resultado_vacio(admin_app, admin_password):
    client = admin_app.test_client()
    login(client, admin_password)
    response = client.get("/reportes?desde=2030-01-01&hasta=2030-02-01&mes=2030-01")
    assert response.status_code == 503


@pytest.mark.parametrize(
    "modulo",
    [
        "clientes",
        "reservas",
        "visitas",
        "mesas",
        "catalogo",
        "ingredientes",
        "inventario",
        "producciones",
        "ventas",
    ],
)
def test_pantallas_operativas_requieren_sesion_y_cargan_formulario(
    reports_app, admin_password, modulo
):
    client = reports_app.test_client()
    assert client.get(f"/operacion/{modulo}").status_code == 401
    login(client, admin_password)
    response = client.get(f"/operacion/{modulo}")
    assert response.status_code == 200
    assert f'data-module="{modulo}"' in response.text
    assert 'data-csrf="' in response.text
    assert "js/operaciones.js" in response.text
    assert 'id="operation-form"' in response.text


def test_mesero_solo_ve_modulos_permitidos(reports_app, admin_password):
    admin = reports_app.test_client()
    login(admin, admin_password)
    password = secrets.token_urlsafe(24)
    register(admin, password, "mesero", "mesero@example.test")
    client = reports_app.test_client()
    login(client, password, "mesero@example.test")
    assert client.get("/operacion/inventario").status_code == 403
    assert client.get("/operacion/producciones").status_code == 403
    assert client.get("/operacion/ventas").status_code == 200
    assert "/operacion/inventario" not in client.get("/").text
    assert "/operacion/producciones" not in client.get("/").text
    assert client.get("/operacion/desconocido").status_code == 404

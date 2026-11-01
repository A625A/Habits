from pathlib import Path

import psycopg
import pytest
from psycopg import sql

SQL = Path(__file__).resolve().parents[1] / "sql"


@pytest.fixture
def db(auth_app, database_url):
    with psycopg.connect(database_url, autocommit=True) as conn:
        schema = conn.execute("SELECT current_schema()").fetchone()[0]
        conn.execute("CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public")
        conn.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
        with conn.transaction():
            for path in sorted((SQL / "fase1").glob("[0-9]*.sql")):
                conn.execute(path.read_text())
        yield conn


def test_catalogo_compartido_y_referencia_por_sucursal(db):
    product = db.execute("""INSERT INTO productos(codigo,nombre,categoria,precio)
        VALUES ('PRUEBA','Producto de prueba','bebida',10) RETURNING producto_id""").fetchone()[0]
    ingredient = db.execute("""INSERT INTO ingredientes(nombre,unidad)
        VALUES ('Ingrediente de prueba','g') RETURNING ingrediente_id""").fetchone()[0]
    db.execute(
        "INSERT INTO receta_ingrediente(producto_id,ingrediente_id,cantidad) VALUES (%s,%s,5)",
        (product, ingredient),
    )
    db.execute(
        """INSERT INTO inventario_ingrediente(sucursal_id,ingrediente_id,cantidad_referencia)
        SELECT sucursal_id,%s,100 FROM sucursales""",
        (ingredient,),
    )
    assert db.execute("SELECT count(*) FROM inventario_ingrediente").fetchone()[0] == 2
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("UPDATE inventario_ingrediente SET cantidad_referencia=0")
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute(
            "INSERT INTO receta_ingrediente(producto_id,ingrediente_id,cantidad) VALUES (%s,%s,1)",
            (product, ingredient),
        )


@pytest.fixture
def datos(db):
    import secrets

    from werkzeug.security import generate_password_hash

    branches = [r[0] for r in db.execute("SELECT sucursal_id FROM sucursales ORDER BY codigo")]
    user = db.execute(
        """INSERT INTO usuarios(sucursal_id,nombre,email,password_hash,rol)
        VALUES (%s,'Operador prueba','operador@example.test',%s,'administrador') RETURNING usuario_id""",
        (branches[0], generate_password_hash(secrets.token_urlsafe(20))),
    ).fetchone()[0]
    client = db.execute(
        "INSERT INTO clientes(nombre,telefono) VALUES ('Cliente prueba','TEST') RETURNING cliente_id"
    ).fetchone()[0]
    table = db.execute(
        "INSERT INTO mesas(sucursal_id,numero_mesa,capacidad) VALUES (%s,1,4) RETURNING mesa_id",
        (branches[0],),
    ).fetchone()[0]
    return branches[0], branches[1], user, client, table


def reservar(db, datos, inicio="2030-01-01 10:00:00-06", personas=2):
    branch, _, _, client, table = datos
    return db.execute(
        """INSERT INTO reservas(sucursal_id,mesa_id,cliente_id,fecha_inicio,fecha_fin,personas,estado)
        VALUES (%s,%s,%s,%s::timestamptz,%s::timestamptz+interval '90 minutes',%s,'confirmada')
        RETURNING reserva_id""",
        (branch, table, client, inicio, inicio, personas),
    ).fetchone()[0]


def test_llegada_crea_visita_sin_liberar_reserva_y_cancelacion_libera(db, datos):
    branch, _, user, client, _table = datos
    reserve = reservar(db, datos)
    db.execute("CALL registrar_llegada(%s,%s,NULL)", (reserve, user))
    assert db.execute("SELECT estado FROM reservas").fetchone()[0] == "completada"
    assert db.execute("SELECT count(*) FROM visitas").fetchone()[0] == 1
    with pytest.raises(psycopg.errors.ExclusionViolation):
        reservar(db, datos)
    with pytest.raises(psycopg.Error):
        db.execute("CALL registrar_llegada(%s,%s,NULL)", (reserve, user))
    adjacent = reservar(db, datos, "2030-01-01 11:30:00-06")
    db.execute("CALL cancelar_reserva(%s)", (adjacent,))
    reservar(db, datos, "2030-01-01 11:30:00-06")
    db.execute(
        "INSERT INTO visitas(cliente_id,sucursal_id,usuario_id,tipo) VALUES (%s,%s,%s,'llevar')",
        (client, branch, user),
    )
    assert db.execute("SELECT count(*) FROM visitas").fetchone()[0] == 2


@pytest.fixture
def receta(db, datos):
    branch, _, user, _, _ = datos
    ingredient = db.execute(
        "INSERT INTO ingredientes(nombre,unidad) VALUES ('Harina prueba','g') RETURNING ingrediente_id"
    ).fetchone()[0]
    product = db.execute(
        "INSERT INTO productos(codigo,nombre,categoria,precio) VALUES ('PAN','Pan prueba','panaderia',10) RETURNING producto_id"
    ).fetchone()[0]
    db.execute(
        "INSERT INTO receta_ingrediente(producto_id,ingrediente_id,cantidad) VALUES (%s,%s,5)",
        (product, ingredient),
    )
    inventory = db.execute(
        "INSERT INTO inventario_ingrediente(sucursal_id,ingrediente_id,cantidad_referencia) VALUES (%s,%s,100) RETURNING inventario_id",
        (branch, ingredient),
    ).fetchone()[0]
    for days, qty in [(-1, 90), (1, 10), (3, 20)]:
        db.execute(
            """INSERT INTO lotes_ingrediente(inventario_id,usuario_id,fecha_vencimiento,cantidad_inicial,cantidad_disponible)
            VALUES (%s,%s,(CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date+%s,%s,%s)""",
            (inventory, user, days, qty, qty),
        )
    return product, inventory


def test_produccion_fefo_excluye_vencidos_y_revierte_faltantes(db, datos, receta):
    branch, _, user, _, _ = datos
    product, inventory = receta
    db.execute("CALL registrar_produccion(%s,%s,%s,3,CURRENT_DATE+2,NULL)", (branch, product, user))
    assert [
        r[0]
        for r in db.execute(
            "SELECT cantidad_disponible FROM lotes_ingrediente ORDER BY fecha_vencimiento"
        )
    ] == [90, 0, 15]
    assert (
        db.execute(
            "SELECT cantidad_disponible FROM v_stock_ingredientes WHERE inventario_id=%s",
            (inventory,),
        ).fetchone()[0]
        == 15
    )
    assert db.execute("SELECT stock_bajo(15,100),stock_bajo(16,100)").fetchone() == (True, False)
    with pytest.raises(psycopg.Error):
        db.execute(
            "CALL registrar_produccion(%s,%s,%s,4,CURRENT_DATE+2,NULL)", (branch, product, user)
        )
    assert (
        db.execute(
            "SELECT cantidad_disponible FROM v_stock_ingredientes WHERE inventario_id=%s",
            (inventory,),
        ).fetchone()[0]
        == 15
    )
    assert db.execute("SELECT cantidad_disponible FROM producciones").fetchone()[0] == 3


def vender(db, datos, product, qty=1, visit=None):
    from psycopg.types.json import Jsonb

    branch, _, user, _, _ = datos
    return db.execute(
        "CALL registrar_venta(%s,%s,%s,%s,NULL,%s,NULL)",
        (branch, user, "llevar", visit, Jsonb([{"producto_id": product, "cantidad": qty}])),
    ).fetchone()[0]


def test_venta_terminado_no_duplica_consumo_y_conserva_precio(db, datos, receta):
    branch, _, user, client, _ = datos
    product, inventory = receta
    db.execute("CALL registrar_produccion(%s,%s,%s,3,CURRENT_DATE+2,NULL)", (branch, product, user))
    visit = db.execute(
        "INSERT INTO visitas(cliente_id,sucursal_id,usuario_id,tipo) VALUES (%s,%s,%s,'llevar') RETURNING visita_id",
        (client, branch, user),
    ).fetchone()[0]
    first = vender(db, datos, product, visit=visit)
    vender(db, datos, product, visit=visit)
    db.execute("UPDATE productos SET precio=25 WHERE producto_id=%s", (product,))
    assert (
        db.execute("SELECT total FROM v_totales_ventas WHERE venta_id=%s", (first,)).fetchone()[0]
        == 10
    )
    assert (
        db.execute(
            "SELECT cantidad_disponible FROM v_stock_ingredientes WHERE inventario_id=%s",
            (inventory,),
        ).fetchone()[0]
        == 15
    )
    assert db.execute("SELECT cantidad_disponible FROM producciones").fetchone()[0] == 1
    with pytest.raises(psycopg.Error):
        vender(db, datos, product, 2)
    assert db.execute("SELECT count(*) FROM ventas").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM visitas").fetchone()[0] == 1


def test_reportes_separan_reservas_visitas_ventas_y_auditoria_revierte(db, datos, receta):
    branch, other, user, client, _ = datos
    product, _ = receta
    reserva = reservar(db, datos)
    assert (
        db.execute("SELECT * FROM reporte_frecuentes('2020-01-01','2040-01-01')").fetchall() == []
    )
    db.execute("CALL registrar_llegada(%s,%s,NULL)", (reserva, user))
    # Esta venta para llevar corresponde a otra atención real, sin reserva.
    visit = db.execute(
        "INSERT INTO visitas(cliente_id,sucursal_id,usuario_id,tipo) VALUES (%s,%s,%s,'llevar') RETURNING visita_id",
        (client, branch, user),
    ).fetchone()[0]
    db.execute("CALL registrar_produccion(%s,%s,%s,3,CURRENT_DATE+2,NULL)", (branch, product, user))
    vender(db, datos, product, visit=visit)
    vender(db, datos, product, visit=visit)
    assert (
        db.execute("SELECT visitas FROM reporte_frecuentes('2020-01-01','2040-01-01')").fetchone()[
            0
        ]
        == 2
    )
    row = db.execute(
        "SELECT reservas,ventas,importe FROM reporte_sucursales('2020-01-01','2040-01-01') WHERE sucursal_id=%s",
        (branch,),
    ).fetchone()
    assert row == (1, 2, 20)
    assert db.execute(
        "SELECT reservas,ventas,importe FROM reporte_sucursales('2020-01-01','2040-01-01') WHERE sucursal_id=%s",
        (other,),
    ).fetchone() == (0, 0, 0)
    assert (
        db.execute("SELECT unidades FROM reporte_productos('2020-01-01','2040-01-01')").fetchone()[
            0
        ]
        == 2
    )
    assert (
        db.execute(
            "SELECT completadas FROM reporte_reservas('2020-01-01','2040-01-01')"
        ).fetchone()[0]
        == 1
    )
    assert db.execute("SELECT count(*) FROM reporte_inventario(CURRENT_DATE)").fetchone()[0] > 0
    before = db.execute("SELECT count(*) FROM auditoria").fetchone()[0]
    with pytest.raises(psycopg.Error):
        vender(db, datos, product, 99)
    assert db.execute("SELECT count(*) FROM auditoria").fetchone()[0] == before
    assert (
        db.execute(
            "SELECT count(*) FROM auditoria WHERE tabla='ventas' AND usuario_id=%s", (user,)
        ).fetchone()[0]
        == 2
    )


@pytest.mark.parametrize("cambio", ["sucursal", "usuario", "cliente", "mesa"])
def test_visita_rechaza_referencias_inactivas(db, datos, cambio):
    branch, _, user, client, table = datos
    changes = {
        "sucursal": ("UPDATE sucursales SET activa=false WHERE sucursal_id=%s", branch),
        "usuario": ("UPDATE usuarios SET activo=false WHERE usuario_id=%s", user),
        "cliente": ("UPDATE clientes SET activo=false WHERE cliente_id=%s", client),
        "mesa": ("UPDATE mesas SET activa=false WHERE mesa_id=%s", table),
    }
    query, ident = changes[cambio]
    db.execute(query, (ident,))
    with pytest.raises(psycopg.Error):
        db.execute(
            "INSERT INTO visitas(cliente_id,sucursal_id,usuario_id,mesa_id,tipo) VALUES (%s,%s,%s,%s,'local')",
            (client, branch, user, table),
        )


def inicializar(database_url):
    import os
    import shutil
    import subprocess

    from psycopg.conninfo import conninfo_to_dict

    config = conninfo_to_dict(database_url)
    env = os.environ.copy()
    for key, var in {
        "host": "PGHOST",
        "port": "PGPORT",
        "user": "PGUSER",
        "password": "PGPASSWORD",
        "dbname": "PGDATABASE",
        "options": "PGOPTIONS",
    }.items():
        if key in config:
            env[var] = config[key]
    env["PGOPTIONS"] = config["options"] + ",public"
    binary = shutil.which("psql") or "/opt/homebrew/opt/postgresql@17/bin/psql"
    return subprocess.run(
        [binary, "-X", "-f", str(SQL / "fase1/inicializar.sql")],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_inicializacion_repetible_preserva_datos_y_precios(auth_app, database_url):
    first = inicializar(database_url)
    assert first.returncode == 0, first.stderr
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("UPDATE productos SET precio=31 WHERE codigo='HAB-01'")
        conn.execute("UPDATE sucursales SET nombre='Nombre conservado' WHERE codigo='DEMO-01'")
        audit_before = conn.execute("SELECT count(*) FROM auditoria").fetchone()[0]
        second = inicializar(database_url)
        assert second.returncode == 0, second.stderr
        assert conn.execute("SELECT count(*) FROM productos").fetchone()[0] == 12
        assert conn.execute("SELECT count(*) FROM sucursales").fetchone()[0] == 2
        assert (
            conn.execute("SELECT precio FROM productos WHERE codigo='HAB-01'").fetchone()[0] == 31
        )
        assert (
            conn.execute("SELECT nombre FROM sucursales WHERE codigo='DEMO-01'").fetchone()[0]
            == "Nombre conservado"
        )
        assert conn.execute("SELECT count(*) FROM auditoria").fetchone()[0] == audit_before
        assert (
            conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema=current_schema() AND table_type='BASE TABLE'"
            ).fetchone()[0]
            == 18
        )


def test_operador_solo_puede_vender_mediante_procedimiento(db, datos, receta):
    branch, _, user, _, _ = datos
    product, _ = receta
    db.execute("CALL registrar_produccion(%s,%s,%s,2,CURRENT_DATE+2,NULL)", (branch, product, user))
    db.execute("SET ROLE habits_operaciones")
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute("UPDATE producciones SET cantidad_disponible=0")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(
                "INSERT INTO detalle_ventas(venta_id,producto_id,cantidad,precio_unitario) VALUES (1,1,1,1)"
            )
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute("SELECT password_hash FROM usuarios")
        sale = vender(db, datos, product)
        assert (
            db.execute("SELECT total FROM v_totales_ventas WHERE venta_id=%s", (sale,)).fetchone()[
                0
            ]
            == 10
        )
    finally:
        db.execute("RESET ROLE")


@pytest.mark.parametrize(
    "caso",
    [
        "capacidad",
        "duracion",
        "sucursal",
        "completada_sin_visita",
        "visita_sin_completar",
        "venta_sin_detalles",
        "visita_futura",
    ],
)
def test_integridad_rechaza_operaciones_incoherentes(db, datos, caso):
    branch, other, user, client, table = datos
    reserve = reservar(db, datos)
    queries = {
        "capacidad": ("UPDATE reservas SET personas=5 WHERE reserva_id=%s", (reserve,)),
        "duracion": (
            "UPDATE reservas SET fecha_fin=fecha_fin+interval '1 minute' WHERE reserva_id=%s",
            (reserve,),
        ),
        "sucursal": (
            "INSERT INTO visitas(cliente_id,sucursal_id,usuario_id,mesa_id,tipo) VALUES (%s,%s,%s,%s,'local')",
            (client, other, user, table),
        ),
        "completada_sin_visita": (
            "UPDATE reservas SET estado='completada' WHERE reserva_id=%s",
            (reserve,),
        ),
        "visita_sin_completar": (
            "INSERT INTO visitas(cliente_id,sucursal_id,usuario_id,mesa_id,reserva_id,tipo) VALUES (%s,%s,%s,%s,%s,'local')",
            (client, branch, user, table, reserve),
        ),
        "venta_sin_detalles": (
            "INSERT INTO ventas(sucursal_id,usuario_id,tipo) VALUES (%s,%s,'llevar')",
            (branch, user),
        ),
        "visita_futura": (
            "INSERT INTO visitas(cliente_id,sucursal_id,usuario_id,tipo,atendida_en) VALUES (%s,%s,%s,'llevar',CURRENT_TIMESTAMP+interval '1 day')",
            (client, branch, user),
        ),
    }
    query, params = queries[caso]
    with pytest.raises(psycopg.Error):
        db.execute(query, params)
    assert db.execute("SELECT count(*) FROM visitas").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM ventas").fetchone()[0] == 0


def test_bebida_consume_receta_completa_y_rechaza_inactivos(db, datos, receta):
    product, inventory = receta
    db.execute("UPDATE productos SET categoria='bebida' WHERE producto_id=%s", (product,))
    vender(db, datos, product, 3)
    assert (
        db.execute(
            "SELECT cantidad_disponible FROM v_stock_ingredientes WHERE inventario_id=%s",
            (inventory,),
        ).fetchone()[0]
        == 15
    )
    db.execute("UPDATE ingredientes SET activo=false")
    with pytest.raises(psycopg.Error):
        vender(db, datos, product)
    assert (
        db.execute(
            "SELECT cantidad_disponible FROM v_stock_ingredientes WHERE inventario_id=%s",
            (inventory,),
        ).fetchone()[0]
        == 15
    )
    assert db.execute("SELECT count(*) FROM ventas").fetchone()[0] == 1


def otra_conexion(db, database_url):
    conn = psycopg.connect(database_url, autocommit=True)
    schema = db.execute("SELECT current_schema()").fetchone()[0]
    conn.execute(sql.SQL("SET search_path TO {},public").format(sql.Identifier(schema)))
    conn.execute("SET lock_timeout='4s'")
    return conn


def esperar_bloqueo(db, conn, future):
    import time

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if future.done():
            pytest.fail("La segunda operación no esperó el bloqueo de la primera")
        if db.execute(
            "SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=%s",
            (conn.info.backend_pid,),
        ).fetchone()[0]:
            return
        time.sleep(0.02)
    pytest.fail("La operación no alcanzó el bloqueo esperado")


def test_dos_reservas_simultaneas_no_ocupan_la_misma_mesa(database_url, db, datos):
    from concurrent.futures import ThreadPoolExecutor

    with otra_conexion(db, database_url) as other, ThreadPoolExecutor(1) as pool:
        with db.transaction():
            reservar(db, datos)
            pending = pool.submit(reservar, other, datos)
            esperar_bloqueo(db, other, pending)
        with pytest.raises(psycopg.errors.ExclusionViolation):
            pending.result(timeout=5)
    assert db.execute("SELECT count(*) FROM reservas").fetchone()[0] == 1


def test_dos_ventas_simultaneas_no_venden_la_misma_unidad(database_url, db, datos, receta):
    from concurrent.futures import ThreadPoolExecutor

    product, _ = receta
    branch, _, user, _, _ = datos
    db.execute("CALL registrar_produccion(%s,%s,%s,1,CURRENT_DATE+2,NULL)", (branch, product, user))
    with otra_conexion(db, database_url) as other, ThreadPoolExecutor(1) as pool:
        with db.transaction():
            vender(db, datos, product)
            pending = pool.submit(vender, other, datos, product)
            esperar_bloqueo(db, other, pending)
        with pytest.raises(psycopg.Error):
            pending.result(timeout=5)
    assert db.execute("SELECT count(*) FROM ventas").fetchone()[0] == 1
    assert db.execute("SELECT cantidad_disponible FROM producciones").fetchone()[0] == 0


def test_unidad_no_cambia_mientras_se_registra_inventario(database_url, db, datos):
    from concurrent.futures import ThreadPoolExecutor

    ingredient = db.execute(
        "INSERT INTO ingredientes(nombre,unidad) VALUES ('Unidad prueba','g') RETURNING ingrediente_id"
    ).fetchone()[0]
    with otra_conexion(db, database_url) as other, ThreadPoolExecutor(1) as pool:
        with db.transaction():
            db.execute(
                "INSERT INTO inventario_ingrediente(sucursal_id,ingrediente_id,cantidad_referencia) VALUES (%s,%s,100)",
                (datos[0], ingredient),
            )
            pending = pool.submit(
                other.execute,
                "UPDATE ingredientes SET unidad='ml' WHERE ingrediente_id=%s",
                (ingredient,),
            )
            esperar_bloqueo(db, other, pending)
        with pytest.raises(psycopg.Error):
            pending.result(timeout=5)
    assert (
        db.execute(
            "SELECT unidad FROM ingredientes WHERE ingrediente_id=%s", (ingredient,)
        ).fetchone()[0]
        == "g"
    )


def test_inicializacion_desde_base_vacia(database_url):
    result = inicializar(database_url)
    assert result.returncode == 0, result.stderr
    with psycopg.connect(database_url) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema=current_schema() AND table_type='BASE TABLE'"
            ).fetchone()[0]
            == 18
        )
        assert conn.execute(
            "SELECT categoria,count(*) FROM productos GROUP BY categoria ORDER BY categoria"
        ).fetchall() == [("bebida", 6), ("panaderia", 4), ("postre", 2)]
        assert conn.execute("SELECT count(*) FROM usuarios").fetchone()[0] == 0


def test_inicializacion_rechaza_esquema_parcial_sin_borrarlo(auth_app, database_url):
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("CREATE TABLE productos (nombre text)")
        conn.execute("INSERT INTO productos VALUES ('Trabajo existente')")
        result = inicializar(database_url)
        assert result.returncode != 0
        assert "Esquema parcial" in result.stderr
        assert conn.execute("SELECT nombre FROM productos").fetchone()[0] == "Trabajo existente"
        assert conn.execute("SELECT to_regclass('visitas')").fetchone()[0] is None


def test_auditoria_insert_update_delete_y_rollback(db, datos, receta):
    product, _ = receta
    client = datos[3]
    with db.transaction():
        db.execute("SELECT set_config('habits.usuario_id',%s,true)", (str(datos[2]),))
        db.execute(
            "INSERT INTO preferencias_cliente(cliente_id,producto_id) VALUES (%s,%s)",
            (client, product),
        )
        db.execute("UPDATE preferencias_cliente SET nota_preferencia='Preferencia de prueba'")
        db.execute("DELETE FROM preferencias_cliente")
    assert [
        r[0]
        for r in db.execute(
            "SELECT operacion FROM auditoria WHERE tabla='preferencias_cliente' ORDER BY auditoria_id"
        )
    ] == ["INSERT", "UPDATE", "DELETE"]
    before = db.execute("SELECT count(*) FROM auditoria").fetchone()[0]
    with pytest.raises(RuntimeError), db.transaction():
        db.execute(
            "INSERT INTO preferencias_cliente(cliente_id,producto_id) VALUES (%s,%s)",
            (client, product),
        )
        raise RuntimeError("Revertir toda la operación")
    assert db.execute("SELECT count(*) FROM auditoria").fetchone()[0] == before
    assert db.execute("SELECT count(*) FROM preferencias_cliente").fetchone()[0] == 0


def test_fallo_en_segunda_linea_revierte_primera_y_bitacora(db, datos, receta):
    from psycopg.types.json import Jsonb

    product, _ = receta
    branch, _, user, _, _ = datos
    db.execute("CALL registrar_produccion(%s,%s,%s,1,CURRENT_DATE+2,NULL)", (branch, product, user))
    before = db.execute("SELECT count(*) FROM auditoria").fetchone()[0]
    with pytest.raises(psycopg.Error):
        db.execute(
            "CALL registrar_venta(%s,%s,'llevar',NULL,NULL,%s,NULL)",
            (
                branch,
                user,
                Jsonb(
                    [
                        {"producto_id": product, "cantidad": 1},
                        {"producto_id": 999999, "cantidad": 1},
                    ]
                ),
            ),
        )
    assert db.execute("SELECT cantidad_disponible FROM producciones").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM ventas").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM auditoria").fetchone()[0] == before


def test_terminado_vencido_bloqueado_y_vence_hoy_utilizable(db, datos, receta):
    branch, _, user, _, _ = datos
    product, _ = receta
    # Existencia histórica sintética, solo en el esquema aislado de pruebas.
    db.execute(
        """INSERT INTO producciones(sucursal_id,producto_id,usuario_id,producida_en,fecha_vencimiento,cantidad_producida,cantidad_disponible)
        VALUES (%s,%s,%s,CURRENT_TIMESTAMP-interval '3 days',CURRENT_DATE-1,1,1)""",
        (branch, product, user),
    )
    with pytest.raises(psycopg.Error):
        vender(db, datos, product)
    db.execute(
        "CALL registrar_produccion(%s,%s,%s,1,(CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date,NULL)",
        (branch, product, user),
    )
    vender(db, datos, product)
    assert [
        r[0]
        for r in db.execute(
            "SELECT cantidad_disponible FROM producciones ORDER BY fecha_vencimiento"
        )
    ] == [1, 0]


def test_reporte_mes_selecciona_vencimientos_pero_stock_es_actual(db, datos, receta):
    _, inventory = receta
    rows = db.execute(
        "SELECT disponible_actual,lote_id FROM reporte_inventario('2040-01-01')"
    ).fetchall()
    assert rows == []  # Hay 30 utilizables: no es bajo ni vence en ese mes.
    db.execute(
        "UPDATE inventario_ingrediente SET cantidad_referencia=1000 WHERE inventario_id=%s",
        (inventory,),
    )
    assert db.execute(
        "SELECT disponible_actual,lote_id,bajo_stock FROM reporte_inventario('2040-01-01')"
    ).fetchone() == (30, None, True)


def test_capacidad_no_se_reduce_con_reserva_concurrente(database_url, db, datos):
    from concurrent.futures import ThreadPoolExecutor

    with otra_conexion(db, database_url) as other, ThreadPoolExecutor(1) as pool:
        with db.transaction():
            reservar(db, datos, personas=4)
            pending = pool.submit(
                other.execute, "UPDATE mesas SET capacidad=2 WHERE mesa_id=%s", (datos[4],)
            )
            esperar_bloqueo(db, other, pending)
        with pytest.raises(psycopg.Error):
            pending.result(timeout=5)
    assert db.execute("SELECT capacidad FROM mesas").fetchone()[0] == 4


def test_receta_modificada_no_recalcula_consumos_pasados(db, datos, receta):
    branch, _, user, _, _ = datos
    product, inventory = receta
    db.execute("CALL registrar_produccion(%s,%s,%s,1,CURRENT_DATE+2,NULL)", (branch, product, user))
    db.execute("UPDATE receta_ingrediente SET cantidad=10 WHERE producto_id=%s", (product,))
    assert (
        db.execute(
            "SELECT cantidad_disponible FROM v_stock_ingredientes WHERE inventario_id=%s",
            (inventory,),
        ).fetchone()[0]
        == 25
    )
    db.execute("CALL registrar_produccion(%s,%s,%s,1,CURRENT_DATE+2,NULL)", (branch, product, user))
    assert (
        db.execute(
            "SELECT cantidad_disponible FROM v_stock_ingredientes WHERE inventario_id=%s",
            (inventory,),
        ).fetchone()[0]
        == 15
    )


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE inventario_ingrediente SET sucursal_id=(SELECT max(sucursal_id) FROM sucursales)",
        "UPDATE ingredientes SET unidad='ml'",
        "UPDATE lotes_ingrediente SET cantidad_disponible=-1",
        "UPDATE productos SET precio='NaN'",
        "DELETE FROM ingredientes",
    ],
)
def test_existencias_no_admiten_reinterpretacion_ni_valores_invalidos(db, datos, receta, query):
    with pytest.raises(psycopg.Error):
        db.execute(query)


def test_llegada_y_cancelacion_confirman_con_rol_operativo(db, datos):
    reserve = reservar(db, datos)
    cancel = reservar(db, datos, "2030-01-01 11:30:00-06")
    db.execute("SET ROLE habits_operaciones")
    try:
        with db.transaction():
            db.execute("CALL registrar_llegada(%s,%s,NULL)", (reserve, datos[2]))
        with db.transaction():
            db.execute("CALL cancelar_reserva(%s)", (cancel,))
        assert [r[0] for r in db.execute("SELECT estado FROM reservas ORDER BY reserva_id")] == [
            "completada",
            "cancelada",
        ]
    finally:
        db.execute("RESET ROLE")

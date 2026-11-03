from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

SQL = Path(__file__).resolve().parents[1] / "sql" / "datos_ejemplo" / "datos.sql"


@pytest.fixture
def db(auth_app, database_url):
    with psycopg.connect(database_url, autocommit=True) as conn:
        schema = conn.execute("SELECT current_schema()").fetchone()[0]
        conn.execute("CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public")
        conn.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
        with conn.transaction():
            for path in sorted((SQL.parents[1] / "fase1").glob("[0-9]*.sql")):
                conn.execute(path.read_text(encoding="utf-8"))
            conn.execute(
                (SQL.parents[1] / "fase1" / "cargar_catalogo.sql").read_text(encoding="utf-8")
            )
        yield conn


@pytest.fixture
def carga(db):
    from werkzeug.security import generate_password_hash

    usuario = db.execute(
        """INSERT INTO usuarios(sucursal_id,nombre,email,password_hash,rol)
        SELECT sucursal_id,'Administrador prueba','carga@example.test',%s,'administrador'
        FROM sucursales WHERE codigo='DEMO-01' RETURNING usuario_id""",
        (generate_password_hash("clave-solo-para-pruebas"),),
    ).fetchone()[0]

    def ejecutar():
        with db.transaction():
            db.execute("SELECT set_config('habits.usuario_carga',%s,true)", (str(usuario),))
            db.execute(SQL.read_text(encoding="utf-8"))

    return ejecutar


def test_carga_completa_en_dos_sucursales(db, carga):
    carga()
    assert db.execute("SELECT count(*) FROM mesas").fetchone()[0] == 6
    assert db.execute("SELECT count(*) FROM ingredientes").fetchone()[0] == 20
    assert (
        db.execute("SELECT count(DISTINCT producto_id) FROM receta_ingrediente").fetchone()[0] == 12
    )
    assert db.execute("SELECT count(*) FROM inventario_ingrediente").fetchone()[0] == 40
    assert db.execute("SELECT count(*) FROM lotes_ingrediente").fetchone()[0] == 80
    assert db.execute(
        """SELECT bool_and(cantidad_disponible=cantidad_referencia)
        FROM v_stock_ingredientes"""
    ).fetchone()[0]
    assert (
        db.execute("SELECT count(DISTINCT fecha_vencimiento) FROM lotes_ingrediente").fetchone()[0]
        == 2
    )


def test_repetir_no_repone_stock_ni_cambia_recetas(db, carga):
    carga()
    db.execute("UPDATE lotes_ingrediente SET cantidad_disponible=0")
    db.execute("UPDATE receta_ingrediente SET cantidad=cantidad+1")
    recetas = db.execute(
        "SELECT producto_id,ingrediente_id,cantidad FROM receta_ingrediente ORDER BY 1,2"
    ).fetchall()
    carga()
    assert db.execute("SELECT count(*) FROM lotes_ingrediente").fetchone()[0] == 80
    assert db.execute("SELECT sum(cantidad_disponible) FROM lotes_ingrediente").fetchone()[0] == 0
    assert (
        db.execute(
            "SELECT producto_id,ingrediente_id,cantidad FROM receta_ingrediente ORDER BY 1,2"
        ).fetchall()
        == recetas
    )
    assert db.execute("SELECT count(*) FROM mesas").fetchone()[0] == 6


def test_unidad_incompatible_deshace_toda_la_carga(db, carga):
    db.execute("INSERT INTO ingredientes(nombre,unidad) VALUES ('Leche','g')")
    with pytest.raises(psycopg.errors.RaiseException, match="unidad o estado"):
        carga()
    assert db.execute("SELECT count(*) FROM mesas").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM ingredientes").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM receta_ingrediente").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM lotes_ingrediente").fetchone()[0] == 0


def test_carga_rechaza_operador_inactivo(db, carga):
    db.execute("UPDATE usuarios SET activo=false")
    with pytest.raises(psycopg.errors.RaiseException, match="administrador activo"):
        carga()
    assert db.execute("SELECT count(*) FROM mesas").fetchone()[0] == 0


@pytest.fixture
def ejemplo(db, carga):
    carga()
    sedes = dict(db.execute("SELECT codigo,sucursal_id FROM sucursales").fetchall())
    cliente = db.execute(
        """INSERT INTO clientes(nombre,email) VALUES ('Cliente de ejemplo','cliente@example.test')
        RETURNING cliente_id"""
    ).fetchone()[0]
    mesa = db.execute(
        "SELECT mesa_id FROM mesas WHERE sucursal_id=%s AND numero_mesa=1",
        (sedes["DEMO-01"],),
    ).fetchone()[0]
    inicio = db.execute(
        """SELECT (((CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date+1)
        + time '10:00') AT TIME ZONE 'America/Guatemala'"""
    ).fetchone()[0]
    return {
        "sucursal": sedes["DEMO-01"],
        "otra_sucursal": sedes["DEMO-02"],
        "cliente": cliente,
        "mesa": mesa,
        "inicio": inicio,
    }


def reservar_ejemplo(db, ejemplo, personas=2, minutos=0):
    inicio = ejemplo["inicio"] + timedelta(minutes=minutos)
    return db.execute(
        """INSERT INTO reservas(sucursal_id,mesa_id,cliente_id,fecha_inicio,fecha_fin,
        personas,estado) VALUES (%s,%s,%s,%s,%s,%s,'confirmada') RETURNING reserva_id""",
        (
            ejemplo["sucursal"],
            ejemplo["mesa"],
            ejemplo["cliente"],
            inicio,
            inicio + timedelta(minutes=90),
            personas,
        ),
    ).fetchone()[0]


def test_reserva_usa_capacidad_exacta_y_dura_noventa_minutos(db, ejemplo):
    reserva = reservar_ejemplo(db, ejemplo)
    assert db.execute(
        "SELECT personas,fecha_fin-fecha_inicio FROM reservas WHERE reserva_id=%s", (reserva,)
    ).fetchone() == (2, timedelta(minutes=90))
    # Reservar todavía no significa que el cliente haya llegado.
    assert db.execute("SELECT count(*) FROM visitas").fetchone()[0] == 0


@pytest.mark.parametrize("minutos", [-89, 0, 89])
def test_reserva_rechaza_cruces_de_horario(db, ejemplo, minutos):
    reservar_ejemplo(db, ejemplo)
    with pytest.raises(psycopg.errors.ExclusionViolation):
        reservar_ejemplo(db, ejemplo, minutos=minutos)
    assert db.execute("SELECT count(*) FROM reservas").fetchone()[0] == 1


def test_reservas_contiguas_y_cancelacion_liberan_horario(db, ejemplo):
    primera = reservar_ejemplo(db, ejemplo)
    reservar_ejemplo(db, ejemplo, minutos=90)
    db.execute("CALL cancelar_reserva(%s)", (primera,))
    nueva = reservar_ejemplo(db, ejemplo)
    assert nueva != primera
    assert (
        db.execute("SELECT estado FROM reservas WHERE reserva_id=%s", (primera,)).fetchone()[0]
        == "cancelada"
    )


def test_reserva_rechaza_grupo_mayor_a_la_mesa(db, ejemplo):
    with pytest.raises(psycopg.errors.RaiseException, match="Capacidad insuficiente"):
        reservar_ejemplo(db, ejemplo, personas=3)
    assert db.execute("SELECT count(*) FROM reservas").fetchone()[0] == 0


def test_reserva_no_admite_mesa_de_otra_sucursal(db, ejemplo):
    ejemplo["sucursal"] = ejemplo["otra_sucursal"]
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        reservar_ejemplo(db, ejemplo)


@pytest.mark.parametrize("entidad", ["mesa", "cliente", "sucursal"])
def test_reserva_rechaza_datos_inactivos(db, ejemplo, entidad):
    consultas = {
        "mesa": "UPDATE mesas SET activa=false WHERE mesa_id=%s",
        "cliente": "UPDATE clientes SET activo=false WHERE cliente_id=%s",
        "sucursal": "UPDATE sucursales SET activa=false WHERE sucursal_id=%s",
    }
    db.execute(consultas[entidad], (ejemplo[entidad],))
    with pytest.raises(psycopg.errors.RaiseException, match="inactivo"):
        reservar_ejemplo(db, ejemplo)


@pytest.mark.parametrize(
    "disponible,alerta", [(0, True), (1499, True), (1500, True), (1501, False)]
)
def test_alerta_de_inventario_incluye_el_quince_por_ciento(db, ejemplo, disponible, alerta):
    inventario = db.execute(
        """SELECT inventario_id FROM inventario_ingrediente i JOIN ingredientes g
        USING(ingrediente_id) WHERE sucursal_id=%s AND g.nombre='Café'""",
        (ejemplo["sucursal"],),
    ).fetchone()[0]
    db.execute(
        """UPDATE lotes_ingrediente SET cantidad_disponible=
        CASE WHEN cantidad_inicial=2000 THEN %s ELSE 0 END WHERE inventario_id=%s""",
        (disponible, inventario),
    )
    assert db.execute(
        """SELECT cantidad_disponible,stock_bajo(cantidad_disponible,cantidad_referencia)
        FROM v_stock_ingredientes WHERE inventario_id=%s""",
        (inventario,),
    ).fetchone() == (disponible, alerta)
    # Cambiar una sede no modifica las existencias de la otra.
    assert (
        db.execute(
            """SELECT v.cantidad_disponible FROM v_stock_ingredientes v
        JOIN ingredientes g USING(ingrediente_id) WHERE v.sucursal_id=%s AND g.nombre='Café'""",
            (ejemplo["otra_sucursal"],),
        ).fetchone()[0]
        == 10000
    )


@pytest.mark.parametrize(
    "dias,estado,stock",
    [(-1, "vencido", 10000), (0, "proximo", 10010), (7, "proximo", 10010), (8, "posterior", 10010)],
)
def test_vencimientos_respetan_limites_y_excluyen_stock_vencido(db, ejemplo, dias, estado, stock):
    inventario, usuario = db.execute(
        """SELECT i.inventario_id,u.usuario_id FROM inventario_ingrediente i
        JOIN ingredientes g USING(ingrediente_id) CROSS JOIN usuarios u
        WHERE i.sucursal_id=%s AND g.nombre='Café' AND u.email='carga@example.test'""",
        (ejemplo["sucursal"],),
    ).fetchone()
    lote, vencimiento = db.execute(
        """INSERT INTO lotes_ingrediente(inventario_id,usuario_id,fecha_vencimiento,
        cantidad_inicial,cantidad_disponible) VALUES (%s,%s,
        (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date+%s,10,10)
        RETURNING lote_id,fecha_vencimiento""",
        (inventario, usuario, dias),
    ).fetchone()
    assert (
        db.execute(
            "SELECT cantidad_disponible FROM v_stock_ingredientes WHERE inventario_id=%s",
            (inventario,),
        ).fetchone()[0]
        == stock
    )
    # Usar el mes del lote permite comprobar también cambios de mes y de año.
    assert (
        db.execute(
            "SELECT estado FROM reporte_inventario(%s) WHERE lote_id=%s", (vencimiento, lote)
        ).fetchone()[0]
        == estado
    )


@pytest.mark.parametrize("saldo", [-1, 10001])
def test_lotes_rechazan_saldos_fuera_de_la_cantidad_recibida(db, ejemplo, saldo):
    lote, inicial, disponible = db.execute(
        "SELECT lote_id,cantidad_inicial,cantidad_disponible FROM lotes_ingrediente ORDER BY lote_id LIMIT 1"
    ).fetchone()
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "UPDATE lotes_ingrediente SET cantidad_disponible=%s WHERE lote_id=%s", (saldo, lote)
        )
    assert db.execute(
        "SELECT cantidad_inicial,cantidad_disponible FROM lotes_ingrediente WHERE lote_id=%s",
        (lote,),
    ).fetchone() == (inicial, disponible)


def test_consultas_de_revision_muestran_los_datos_sin_cambiarlos(db, ejemplo):
    reservar_ejemplo(db, ejemplo)
    antes = db.execute(
        "SELECT lote_id,cantidad_disponible FROM lotes_ingrediente ORDER BY lote_id"
    ).fetchall()
    consulta = SQL.with_name("revisar_reservas_inventario.sql").read_text(encoding="utf-8")
    cursor = db.execute(consulta)
    filas = []
    while True:
        if cursor.description is not None:
            filas.append(len(cursor.fetchall()))
        if not cursor.nextset():
            break
    assert filas == [1, 0, 40, 80]
    assert (
        db.execute(
            "SELECT lote_id,cantidad_disponible FROM lotes_ingrediente ORDER BY lote_id"
        ).fetchall()
        == antes
    )


@pytest.fixture
def operaciones(db, ejemplo):
    ejemplo["usuario"] = db.execute(
        "SELECT usuario_id FROM usuarios WHERE email='carga@example.test'"
    ).fetchone()[0]
    ejemplo["productos"] = dict(db.execute("SELECT codigo,producto_id FROM productos").fetchall())
    return ejemplo


def producir_ejemplo(db, operaciones, cantidad=2, dias=2):
    return db.execute(
        """CALL registrar_produccion(%s,%s,%s,%s,
        (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date+%s,NULL)""",
        (
            operaciones["sucursal"],
            operaciones["productos"]["HAB-09"],
            operaciones["usuario"],
            cantidad,
            dias,
        ),
    ).fetchone()[0]


def vender_ejemplo(db, operaciones, lineas):
    return db.execute(
        "CALL registrar_venta(%s,%s,'llevar',NULL,NULL,%s,NULL)",
        (operaciones["sucursal"], operaciones["usuario"], Jsonb(lineas)),
    ).fetchone()[0]


def estado_operaciones(db):
    # Comparar también la bitácora permite detectar cambios que quedaron a medias.
    return {
        tabla: db.execute(
            sql.SQL("SELECT * FROM {} ORDER BY 1").format(sql.Identifier(tabla))
        ).fetchall()
        for tabla in ("lotes_ingrediente", "producciones", "ventas", "detalle_ventas", "auditoria")
    }


def test_produccion_consume_receta_y_primero_lotes_que_vencen_antes(db, operaciones):
    antes = dict(db.execute("SELECT lote_id,cantidad_disponible FROM lotes_ingrediente").fetchall())
    produccion = producir_ejemplo(db, operaciones, cantidad=41)
    # Cada pan usa 50 g de harina: 41 panes consumen 2000 g del primer lote y 50 del segundo.
    assert db.execute(
        """SELECT l.cantidad_disponible FROM lotes_ingrediente l
        JOIN inventario_ingrediente i USING(inventario_id) JOIN ingredientes g USING(ingrediente_id)
        WHERE i.sucursal_id=%s AND g.nombre='Harina' ORDER BY l.fecha_vencimiento,l.lote_id""",
        (operaciones["sucursal"],),
    ).fetchall() == [(0,), (7950,)]
    consumos = dict(
        db.execute(
            "SELECT ingrediente_id,cantidad*41 FROM receta_ingrediente WHERE producto_id=%s",
            (operaciones["productos"]["HAB-09"],),
        ).fetchall()
    )
    for ingrediente, cantidad in consumos.items():
        lotes = db.execute(
            """SELECT l.lote_id,l.cantidad_disponible FROM lotes_ingrediente l
            JOIN inventario_ingrediente i USING(inventario_id)
            WHERE i.sucursal_id=%s AND i.ingrediente_id=%s""",
            (operaciones["sucursal"], ingrediente),
        ).fetchall()
        assert sum(antes[lote] - saldo for lote, saldo in lotes) == cantidad
    assert db.execute(
        "SELECT cantidad_producida,cantidad_disponible FROM producciones WHERE produccion_id=%s",
        (produccion,),
    ).fetchone() == (41, 41)
    assert (
        db.execute(
            "SELECT sum(cantidad_disponible) FROM v_stock_ingredientes WHERE sucursal_id=%s",
            (operaciones["otra_sucursal"],),
        ).fetchone()[0]
        == 190100
    )


def test_venta_de_bebida_descontada_por_receta_sin_produccion(db, operaciones):
    producto = operaciones["productos"]["HAB-01"]
    antes = dict(
        db.execute(
            "SELECT ingrediente_id,cantidad_disponible FROM v_stock_ingredientes WHERE sucursal_id=%s",
            (operaciones["sucursal"],),
        ).fetchall()
    )
    venta = vender_ejemplo(db, operaciones, [{"producto_id": producto, "cantidad": 2}])
    for ingrediente, cantidad in db.execute(
        "SELECT ingrediente_id,cantidad*2 FROM receta_ingrediente WHERE producto_id=%s", (producto,)
    ).fetchall():
        saldo = db.execute(
            "SELECT cantidad_disponible FROM v_stock_ingredientes WHERE sucursal_id=%s AND ingrediente_id=%s",
            (operaciones["sucursal"], ingrediente),
        ).fetchone()[0]
        assert antes[ingrediente] - saldo == cantidad
    assert db.execute("SELECT count(*) FROM producciones").fetchone()[0] == 0
    assert (
        db.execute("SELECT total FROM v_totales_ventas WHERE venta_id=%s", (venta,)).fetchone()[0]
        == 52
    )


def test_venta_de_pan_no_repite_consumo_y_conserva_precio_cobrado(db, operaciones):
    producir_ejemplo(db, operaciones)
    antes = db.execute(
        "SELECT lote_id,cantidad_disponible FROM lotes_ingrediente ORDER BY 1"
    ).fetchall()
    producto = operaciones["productos"]["HAB-09"]
    venta = vender_ejemplo(db, operaciones, [{"producto_id": producto, "cantidad": 1}])
    db.execute("UPDATE productos SET precio=99 WHERE producto_id=%s", (producto,))
    assert (
        db.execute(
            "SELECT lote_id,cantidad_disponible FROM lotes_ingrediente ORDER BY 1"
        ).fetchall()
        == antes
    )
    assert db.execute("SELECT cantidad_disponible FROM producciones").fetchone()[0] == 1
    assert (
        db.execute("SELECT total FROM v_totales_ventas WHERE venta_id=%s", (venta,)).fetchone()[0]
        == 16
    )


def test_falta_de_ingrediente_revierte_produccion_y_auditoria(db, operaciones):
    # Huevo se recorre después de harina: el error ocurre tras comenzar el descuento.
    db.execute(
        """UPDATE lotes_ingrediente SET cantidad_disponible=0 WHERE inventario_id IN
        (SELECT inventario_id FROM inventario_ingrediente JOIN ingredientes USING(ingrediente_id)
        WHERE sucursal_id=%s AND nombre='Huevo')""",
        (operaciones["sucursal"],),
    )
    antes = estado_operaciones(db)
    with pytest.raises(psycopg.errors.RaiseException, match="Ingrediente sin existencias"):
        producir_ejemplo(db, operaciones)
    assert estado_operaciones(db) == antes


def test_falla_en_segundo_producto_revierte_venta_completa(db, operaciones):
    antes = estado_operaciones(db)
    with pytest.raises(psycopg.errors.RaiseException, match="Producto sin unidades"):
        vender_ejemplo(
            db,
            operaciones,
            [
                {"producto_id": operaciones["productos"]["HAB-01"], "cantidad": 1},
                {"producto_id": operaciones["productos"]["HAB-09"], "cantidad": 1},
            ],
        )
    # Tampoco queda el descuento de la bebida, su detalle ni su evento de auditoría.
    assert estado_operaciones(db) == antes


def test_rollback_explicito_deshace_produccion_venta_y_bitacora(db, operaciones):
    antes = estado_operaciones(db)
    db.execute("BEGIN")
    try:
        producir_ejemplo(db, operaciones)
        vender_ejemplo(
            db, operaciones, [{"producto_id": operaciones["productos"]["HAB-09"], "cantidad": 1}]
        )
        assert db.execute("SELECT count(*) FROM ventas").fetchone()[0] == 1
    finally:
        db.execute("ROLLBACK")
    assert estado_operaciones(db) == antes


def test_commit_conserva_operaciones_y_actor_de_auditoria(db, operaciones, database_url):
    with db.transaction():
        producir_ejemplo(db, operaciones)
        venta = vender_ejemplo(
            db, operaciones, [{"producto_id": operaciones["productos"]["HAB-09"], "cantidad": 1}]
        )
    # Otra conexión comprueba que los cambios realmente quedaron guardados.
    with psycopg.connect(database_url) as otra:
        assert (
            otra.execute(
                "SELECT total FROM v_totales_ventas WHERE venta_id=%s", (venta,)
            ).fetchone()[0]
            == 16
        )
        assert (
            otra.execute(
                "SELECT usuario_id FROM auditoria WHERE tabla='ventas' AND registro_id=%s",
                (str(venta),),
            ).fetchone()[0]
            == operaciones["usuario"]
        )


def test_trigger_impide_confirmar_venta_sin_detalles(db, operaciones):
    antes = estado_operaciones(db)
    with (
        pytest.raises(psycopg.errors.RaiseException, match="La venta debe tener detalles"),
        db.transaction(),
    ):
        db.execute(
            "INSERT INTO ventas(sucursal_id,usuario_id,tipo) VALUES (%s,%s,'llevar')",
            (operaciones["sucursal"], operaciones["usuario"]),
        )
    assert estado_operaciones(db) == antes


def test_venta_elige_pan_que_vence_antes_aunque_se_produjo_despues(db, operaciones):
    posterior = producir_ejemplo(db, operaciones, cantidad=2, dias=5)
    cercano = producir_ejemplo(db, operaciones, cantidad=1, dias=1)
    vender_ejemplo(
        db, operaciones, [{"producto_id": operaciones["productos"]["HAB-09"], "cantidad": 2}]
    )
    assert dict(
        db.execute("SELECT produccion_id,cantidad_disponible FROM producciones").fetchall()
    ) == {posterior: 1, cercano: 0}


def test_ingrediente_vencido_no_permite_vender_bebida(db, operaciones):
    inventario = db.execute(
        """SELECT inventario_id FROM inventario_ingrediente JOIN ingredientes USING(ingrediente_id)
        WHERE sucursal_id=%s AND nombre='Café'""",
        (operaciones["sucursal"],),
    ).fetchone()[0]
    db.execute(
        "UPDATE lotes_ingrediente SET cantidad_disponible=0 WHERE inventario_id=%s", (inventario,)
    )
    db.execute(
        """INSERT INTO lotes_ingrediente(inventario_id,usuario_id,fecha_vencimiento,
        cantidad_inicial,cantidad_disponible) VALUES (%s,%s,
        (CURRENT_TIMESTAMP AT TIME ZONE 'America/Guatemala')::date-1,1000,1000)""",
        (inventario, operaciones["usuario"]),
    )
    antes = estado_operaciones(db)
    with pytest.raises(psycopg.errors.RaiseException, match="Ingrediente sin existencias"):
        vender_ejemplo(
            db, operaciones, [{"producto_id": operaciones["productos"]["HAB-01"], "cantidad": 1}]
        )
    assert estado_operaciones(db) == antes


def test_ensayo_manual_revierte_produccion_venta_e_inventario(db, operaciones, database_url):
    import os
    import subprocess

    from psycopg.conninfo import conninfo_to_dict

    entorno = os.environ.copy()
    conexion = conninfo_to_dict(database_url)
    for clave, variable in {
        "host": "PGHOST",
        "port": "PGPORT",
        "user": "PGUSER",
        "password": "PGPASSWORD",
        "dbname": "PGDATABASE",
    }.items():
        if clave in conexion:
            entorno[variable] = conexion[clave]
    esquema = db.execute("SELECT current_schema()").fetchone()[0]
    entorno["PGOPTIONS"] = f"-csearch_path={esquema},public"
    antes = estado_operaciones(db)
    resultado = subprocess.run(
        [
            "psql",
            "-X",
            "-A",
            "-t",
            "-v",
            f"usuario_id={operaciones['usuario']}",
            "-f",
            str(SQL.with_name("ensayar_produccion_venta.psql")),
        ],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "t|t|t|t" in resultado.stdout
    assert estado_operaciones(db) == antes

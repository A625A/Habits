from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

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

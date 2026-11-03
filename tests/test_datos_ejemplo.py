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

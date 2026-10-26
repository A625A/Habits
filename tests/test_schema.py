import psycopg
import pytest


def test_cli_crea_core_y_permite_usuario_vinculado_a_sucursal(app, database_url):
    result = app.test_cli_runner().invoke(args=["db-init"])
    assert result.exit_code == 0, result.output
    with psycopg.connect(database_url) as conn:
        branch_id = conn.execute(
            "INSERT INTO sucursales (codigo, nombre) VALUES (%s, %s) RETURNING sucursal_id",
            ("PRUEBA", "Sucursal de prueba"),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO usuarios (sucursal_id, nombre, email, password_hash, rol)
               VALUES (%s, %s, %s, %s, %s)""",
            (branch_id, "Personal prueba", "prueba@example.test", "hash-solo-prueba", "mesero"),
        )
        row = conn.execute(
            """SELECT s.codigo, u.nombre, u.rol FROM usuarios u
               JOIN sucursales s USING (sucursal_id)"""
        ).fetchone()
        assert row == ("PRUEBA", "Personal prueba", "mesero")


@pytest.fixture
def core(app, database_url):
    result = app.test_cli_runner().invoke(args=["db-init"])
    assert result.exit_code == 0, result.output
    with psycopg.connect(database_url, autocommit=True) as conn:
        branch_id = conn.execute(
            "INSERT INTO sucursales (codigo, nombre) VALUES ('BASE', 'Base') RETURNING sucursal_id"
        ).fetchone()[0]
        yield conn, branch_id


def test_no_se_duplican_usuarios_por_mayusculas_en_email(core):
    conn, branch_id = core
    query = """INSERT INTO usuarios (sucursal_id, nombre, email, password_hash, rol)
               VALUES (%s, 'Prueba', %s, 'hash-solo-prueba', 'mesero')"""
    conn.execute(query, (branch_id, "Persona@example.test"))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(query, (branch_id, "persona@example.test"))


def test_solo_se_admiten_roles_de_la_consigna(core):
    conn, branch_id = core
    query = """INSERT INTO usuarios (sucursal_id, nombre, email, password_hash, rol)
               VALUES (%s, 'Prueba', %s, 'hash-solo-prueba', %s)"""
    for role in ("administrador", "mesero", "gerente"):
        conn.execute(query, (branch_id, f"{role}@example.test", role))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(query, (branch_id, "invalido@example.test", "superusuario"))


@pytest.mark.parametrize(
    "column,value",
    [
        ("nombre", "  "),
        ("email", "sin-arroba"),
        ("email", " persona@example.test "),
        ("password_hash", ""),
    ],
)
def test_usuario_rechaza_campos_basicos_invalidos(core, column, value):
    from psycopg import sql

    conn, branch_id = core
    user_id = conn.execute(
        """INSERT INTO usuarios (sucursal_id, nombre, email, password_hash, rol)
           VALUES (%s, 'Prueba', 'persona@example.test', 'hash-solo-prueba', 'mesero')
           RETURNING usuario_id""",
        (branch_id,),
    ).fetchone()[0]
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            sql.SQL("UPDATE usuarios SET {} = %s WHERE usuario_id = %s").format(
                sql.Identifier(column)
            ),
            (value, user_id),
        )


@pytest.mark.parametrize("column", ["codigo", "nombre"])
def test_sucursal_rechaza_identificadores_vacios(core, column):
    from psycopg import sql

    conn, branch_id = core
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            sql.SQL("UPDATE sucursales SET {} = '  ' WHERE sucursal_id = %s").format(
                sql.Identifier(column)
            ),
            (branch_id,),
        )


def test_fk_impide_usuario_huerfano_y_borrar_sucursal_referenciada(core):
    conn, branch_id = core
    query = """INSERT INTO usuarios (sucursal_id, nombre, email, password_hash, rol)
               VALUES (%s, 'Prueba', 'prueba@example.test', 'hash-solo-prueba', 'mesero')"""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(query, (-1,))
    conn.execute(query, (branch_id,))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute("DELETE FROM sucursales WHERE sucursal_id = %s", (branch_id,))


def test_codigos_de_sucursal_son_unicos(core):
    conn, _ = core
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute("INSERT INTO sucursales (codigo, nombre) VALUES ('BASE', 'Otra')")


def test_conexion_compartida_confirma_y_revierte_operaciones_completas(app, core):
    from app.db import get_db

    observer, _ = core
    with app.app_context():
        db = get_db()
        with db.transaction():
            db.execute("INSERT INTO sucursales (codigo, nombre) VALUES ('COMMIT', 'Confirmada')")
        assert observer.execute(
            "SELECT nombre FROM sucursales WHERE codigo = 'COMMIT'"
        ).fetchone() == ("Confirmada",)
        with pytest.raises(psycopg.errors.UniqueViolation), db.transaction():
            db.execute("INSERT INTO sucursales (codigo, nombre) VALUES ('ROLLBACK', 'Temporal')")
            db.execute("INSERT INTO sucursales (codigo, nombre) VALUES ('BASE', 'Duplicada')")
        assert observer.execute(
            "SELECT COUNT(*) FROM sucursales WHERE codigo = 'ROLLBACK'"
        ).fetchone() == (0,)

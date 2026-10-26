import psycopg
import pytest


def test_triggers_registran_insert_update_delete_y_rollback(auth_app, database_url):
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.transaction():
            branch = conn.execute(
                "INSERT INTO sucursales (codigo, nombre) VALUES ('AUDIT', 'Antes') RETURNING sucursal_id"
            ).fetchone()[0]
            conn.execute(
                "UPDATE sucursales SET nombre = 'Después' WHERE sucursal_id = %s", (branch,)
            )
            conn.execute("DELETE FROM sucursales WHERE sucursal_id = %s", (branch,))
        rows = conn.execute(
            """SELECT operacion, datos_anteriores, datos_nuevos FROM auditoria
               WHERE tabla = 'sucursales' AND registro_id = %s ORDER BY auditoria_id""",
            (str(branch),),
        ).fetchall()
        assert [r[0] for r in rows] == ["INSERT", "UPDATE", "DELETE"]
        assert rows[0][1] is None and rows[0][2]["nombre"] == "Antes"
        assert rows[1][1]["nombre"] == "Antes" and rows[1][2]["nombre"] == "Después"
        assert rows[2][2] is None
        with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
            conn.execute("INSERT INTO sucursales (codigo, nombre) VALUES ('ROLL', 'Rollback')")
            conn.execute("INSERT INTO sucursales (codigo, nombre) VALUES ('ROLL', 'Duplicada')")
        assert conn.execute(
            "SELECT COUNT(*) FROM auditoria WHERE datos_nuevos->>'codigo' = 'ROLL'"
        ).fetchone() == (0,)


def test_auditoria_usuarios_omite_secretos_y_conserva_actor_eliminado(
    admin_app, database_url, admin_password
):
    with psycopg.connect(database_url, autocommit=True) as conn:
        user = conn.execute("SELECT usuario_id FROM usuarios").fetchone()[0]
        with conn.transaction():
            conn.execute("SELECT set_config('habits.usuario_id', %s, true)", (str(user),))
            conn.execute(
                "UPDATE usuarios SET nombre = 'Nuevo nombre' WHERE usuario_id = %s", (user,)
            )
            conn.execute("DELETE FROM usuarios WHERE usuario_id = %s", (user,))
        rows = conn.execute(
            "SELECT operacion, usuario_id, datos_anteriores, datos_nuevos FROM auditoria WHERE tabla = 'usuarios' ORDER BY auditoria_id"
        ).fetchall()
        assert [r[0] for r in rows] == ["INSERT", "UPDATE", "DELETE"]
        assert rows[1][1] == user and rows[2][1] == user
        for _, _, old, new in rows:
            for data in (old, new):
                if data is not None:
                    assert set(data) == {"usuario_id", "sucursal_id", "rol", "activo"}
        assert admin_password not in str(rows)
        # El actor no se filtra a la siguiente transacción/conexión compartida.
        conn.execute("UPDATE sucursales SET nombre = nombre WHERE codigo = 'DEMO-01'")
        assert conn.execute(
            "SELECT usuario_id FROM auditoria ORDER BY auditoria_id DESC LIMIT 1"
        ).fetchone() == (None,)


def test_funcion_auditoria_admite_tabla_futura_con_lista_permitida(auth_app, database_url):
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "CREATE TABLE prueba_auditable (id BIGINT PRIMARY KEY, estado TEXT, secreto TEXT)"
        )
        conn.execute(
            "CREATE TRIGGER prueba_audit AFTER INSERT OR UPDATE OR DELETE ON prueba_auditable FOR EACH ROW EXECUTE FUNCTION auditar_cambio('id', 'id', 'estado')"
        )
        conn.execute("INSERT INTO prueba_auditable VALUES (7, 'inicial', 'no registrar')")
        conn.execute("UPDATE prueba_auditable SET estado = 'final' WHERE id = 7")
        conn.execute("DELETE FROM prueba_auditable WHERE id = 7")
        rows = conn.execute(
            "SELECT operacion, datos_anteriores, datos_nuevos FROM auditoria WHERE tabla='prueba_auditable' ORDER BY auditoria_id"
        ).fetchall()
        assert [r[0] for r in rows] == ["INSERT", "UPDATE", "DELETE"]
        assert rows[1][2] == {"id": 7, "estado": "final"}
        assert "secreto" not in str(rows) and "no registrar" not in str(rows)

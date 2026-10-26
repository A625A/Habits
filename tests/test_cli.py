import psycopg


def test_seed_repetible_crea_dos_sucursales_sin_usuarios_demo(app, database_url):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["db-init"]).exit_code == 0
    for _ in range(2):
        result = runner.invoke(args=["db-seed"])
        assert result.exit_code == 0, result.output
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT codigo FROM sucursales ORDER BY codigo").fetchall() == [
            ("DEMO-01",),
            ("DEMO-02",),
        ]
        assert conn.execute("SELECT COUNT(*) FROM usuarios").fetchone() == (0,)


def test_reinicializar_no_borra_datos_existentes(app, database_url):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["db-init"]).exit_code == 0
    assert runner.invoke(args=["db-seed"]).exit_code == 0
    result = runner.invoke(args=["db-init"])
    assert result.exit_code != 0
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT COUNT(*) FROM sucursales").fetchone() == (2,)


def test_inicializacion_fallida_no_deja_tablas_parciales(app, database_url):
    with psycopg.connect(database_url) as conn:
        conn.execute("CREATE TABLE usuarios (marcador TEXT)")
        conn.execute("INSERT INTO usuarios VALUES ('preservar')")
    result = app.test_cli_runner().invoke(args=["db-init"])
    assert result.exit_code != 0
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT to_regclass('sucursales')").fetchone() == (None,)
        assert conn.execute("SELECT marcador FROM usuarios").fetchall() == [("preservar",)]


def test_seed_sin_esquema_explica_como_inicializar(app):
    result = app.test_cli_runner().invoke(args=["db-seed"])
    assert result.exit_code != 0
    assert "db-init" in result.output

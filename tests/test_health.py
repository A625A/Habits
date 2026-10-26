def test_flask_responde_sin_necesitar_postgresql():
    from app import create_app

    app = create_app({"TESTING": True, "DATABASE_URL": "postgresql://localhost/no_usada"})
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_salud_consulta_postgresql_real(app):
    response = app.test_client().get("/health/db")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "database": "ok"}


def test_base_no_disponible_devuelve_503_sin_filtrar_credenciales():
    import socket

    from app import create_app

    # Puerto reservado sin escuchar: falla real de conexión, sin mocks internos.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        app = create_app(
            {
                "TESTING": True,
                "DATABASE_URL": f"postgresql://privado:secreto@127.0.0.1:{port}/no_existe",
            }
        )
        response = app.test_client().get("/health/db")
    assert response.status_code == 503
    assert response.json == {"status": "error", "database": "unavailable"}


def test_falta_de_database_url_se_detecta_al_arrancar():
    import pytest

    from app import create_app

    with pytest.raises(ValueError, match="DATABASE_URL"):
        create_app({"DATABASE_URL": None})

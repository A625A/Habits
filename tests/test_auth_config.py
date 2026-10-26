import secrets

import pytest

from app import create_app


@pytest.mark.parametrize("key", [None, "corta", "CAMBIAR_POR_UN_VALOR_ALEATORIO"])
def test_no_arranca_sin_clave_de_sesion_utilizable(key):
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app({"DATABASE_URL": "postgresql://localhost/no_usada", "SECRET_KEY": key})


def test_cookie_https_con_flags_y_sesion_no_renovable():
    app = create_app(
        {
            "DATABASE_URL": "postgresql://localhost/no_usada",
            "SECRET_KEY": secrets.token_hex(32),
            "HABITS_ENV": "production",
        }
    )
    response = app.test_client().get("/auth/login", base_url="https://habits.example.test")
    cookie = response.headers["Set-Cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert response.headers["Cache-Control"] == "no-store"
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is False

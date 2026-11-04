"""Registro de rutas HTTP."""

from flask import Flask

from app.routes import (
    atencion,
    auth,
    catalogo,
    clientes,
    comparacion,
    health,
    inicio,
    inventario,
    producciones,
    reportes,
    reservas,
    ventas,
)


def register_blueprints(app: Flask) -> None:
    for module in (
        health,
        atencion,
        auth,
        catalogo,
        clientes,
        reservas,
        inventario,
        ventas,
        producciones,
        reportes,
        inicio,
        comparacion,
    ):
        app.register_blueprint(module.bp)

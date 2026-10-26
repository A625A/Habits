"""Blueprints HTTP; cada módulo conserva sus rutas y propietario."""

from flask import Flask

from app.routes import (
    auth,
    clientes,
    comparacion,
    health,
    inicio,
    inventario,
    reportes,
    reservas,
    ventas,
)


def register_blueprints(app: Flask) -> None:
    for module in (
        health,
        auth,
        clientes,
        reservas,
        inventario,
        ventas,
        reportes,
        inicio,
        comparacion,
    ):
        app.register_blueprint(module.bp)

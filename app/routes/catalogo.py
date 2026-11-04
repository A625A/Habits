"""Catálogo compartido y recetas."""

from typing import Any

from flask import abort

from app.api import blueprint, body, boolean, decimal, endpoint, identifier, pagination, price, text
from app.db import get_db
from app.services.operaciones import insert, one, update

bp = blueprint("catalogo", "/catalogo")
PRODUCT_FIELDS = {"nombre": text, "precio": price, "activo": boolean}
INGREDIENT_FIELDS = {"nombre": text, "unidad": text, "activo": boolean}


@bp.get("/productos")
@endpoint()
def products() -> dict[str, Any]:
    return {
        "productos": get_db()
        .execute("SELECT * FROM productos ORDER BY codigo LIMIT %s OFFSET %s", pagination())
        .fetchall()
    }


@bp.get("/productos/<int:producto_id>")
@endpoint()
def product(producto_id: int) -> dict[str, Any]:
    return one("SELECT * FROM productos WHERE producto_id=%s", (producto_id,))


@bp.patch("/productos/<int:producto_id>")
@endpoint("administrador")
def edit_product(producto_id: int) -> dict[str, Any]:
    return update("productos", "producto_id", producto_id, body(PRODUCT_FIELDS))


@bp.get("/ingredientes")
@endpoint()
def ingredients() -> dict[str, Any]:
    return {
        "ingredientes": get_db()
        .execute(
            "SELECT * FROM ingredientes ORDER BY nombre,ingrediente_id LIMIT %s OFFSET %s",
            pagination(),
        )
        .fetchall()
    }


@bp.post("/ingredientes")
@endpoint("administrador")
def create_ingredient() -> tuple[dict[str, Any], int]:
    return insert("ingredientes", body(INGREDIENT_FIELDS, {"nombre", "unidad"})), 201


@bp.patch("/ingredientes/<int:ingrediente_id>")
@endpoint("administrador")
def edit_ingredient(ingrediente_id: int) -> dict[str, Any]:
    return update("ingredientes", "ingrediente_id", ingrediente_id, body(INGREDIENT_FIELDS))


def get_recipe(producto_id: int) -> dict[str, Any]:
    one("SELECT producto_id FROM productos WHERE producto_id=%s", (producto_id,))
    return {
        "ingredientes": get_db()
        .execute(
            """SELECT r.ingrediente_id,i.nombre,i.unidad,r.cantidad
        FROM receta_ingrediente r JOIN ingredientes i USING(ingrediente_id)
        WHERE producto_id=%s ORDER BY ingrediente_id""",
            (producto_id,),
        )
        .fetchall()
    }


@bp.get("/productos/<int:producto_id>/receta")
@endpoint()
def recipe(producto_id: int) -> dict[str, Any]:
    return get_recipe(producto_id)


def recipe_lines(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 200:
        abort(400, description="Se requiere una receta de 1 a 200 ingredientes.")
    result = []
    for row in value:
        if not isinstance(row, dict) or row.keys() != {"ingrediente_id", "cantidad"}:
            abort(400, description="Cada ingrediente requiere ingrediente_id y cantidad.")
        result.append(
            {
                "ingrediente_id": identifier(row["ingrediente_id"]),
                "cantidad": decimal(row["cantidad"]),
            }
        )
    return result


@bp.put("/productos/<int:producto_id>/receta")
@endpoint("administrador")
def set_recipe(producto_id: int) -> dict[str, Any]:
    data = body({"ingredientes": recipe_lines}, {"ingredientes"})
    db = get_db()
    # Mismo bloqueo que los procedimientos: nunca consumir una receta parcial.
    one("SELECT producto_id FROM productos WHERE producto_id=%s FOR UPDATE", (producto_id,))
    db.execute("DELETE FROM receta_ingrediente WHERE producto_id=%s", (producto_id,))
    for ingredient in sorted(data["ingredientes"], key=lambda row: row["ingrediente_id"]):
        insert("receta_ingrediente", {"producto_id": producto_id, **ingredient})
    return get_recipe(producto_id)

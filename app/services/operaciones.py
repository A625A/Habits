"""Operaciones SQL parametrizadas compartidas; identificadores solo del código."""

from typing import Any

from flask import abort
from psycopg import sql

from app.db import get_db


def one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    row = get_db().execute(query, params).fetchone()
    if row is None:
        abort(404, description="Registro no encontrado.")
    return row


def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
        sql.Identifier(table),
        sql.SQL(",").join(map(sql.Identifier, values)),
        sql.SQL(",").join(sql.Placeholder() for _ in values),
    )
    row = get_db().execute(query, tuple(values.values())).fetchone()
    assert row is not None
    return row


def update(table: str, pk: str, record_id: int, values: dict[str, Any]) -> dict[str, Any]:
    query = sql.SQL("UPDATE {} SET {} WHERE {}=%s RETURNING *").format(
        sql.Identifier(table),
        sql.SQL(",").join(sql.SQL("{}=%s").format(sql.Identifier(key)) for key in values),
        sql.Identifier(pk),
    )
    row = get_db().execute(query, (*values.values(), record_id)).fetchone()
    if row is None:
        abort(404, description="Registro no encontrado.")
    return row

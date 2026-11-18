"""Pruebas reales de PostgreSQL en las bases aisladas del runner OLAP."""

from dataclasses import replace
from decimal import Decimal

import psycopg
import pytest

from olap.tests.test_etl_datos import etl


@pytest.fixture(scope="module")
def dataset():
    return etl.validar()


def snapshot(conn):
    return conn.execute("SELECT * FROM olap.fact_ventas ORDER BY detalle_id").fetchall()


def test_carga_recarga_y_tablas_operativas(model, dataset):
    model.execute("CREATE TABLE public.ventas(id integer PRIMARY KEY, total numeric)")
    model.execute("INSERT INTO public.ventas VALUES (1,123.45)")
    assert etl.cargar(model, dataset) == dataset.resumen
    antes = snapshot(model)
    assert etl.cargar(model, dataset) == dataset.resumen
    assert snapshot(model) == antes
    assert model.execute("SELECT * FROM public.ventas").fetchall() == [(1, Decimal("123.45"))]
    assert model.execute(
        "SELECT count(DISTINCT ticket_id),count(*),sum(cantidad),sum(importe) "
        "FROM dm.v_ventas_detalle"
    ).fetchone() == (10000, 19175, 23641, Decimal("583177.42"))
    assert model.execute(
        "SELECT sum(ingresos),sum(tickets) FROM dm.v_ventas_mensuales"
    ).fetchone() == (Decimal("583177.42"), 10000)
    # El precio histórico del detalle se conserva, aunque no exista en el catálogo actual.
    assert (
        model.execute(
            "SELECT count(*) FROM olap.fact_ventas WHERE precio_unitario=24.70"
        ).fetchone()[0]
        > 0
    )


def test_conflicto_historico_no_sobrescribe(model, dataset):
    etl.cargar(model, dataset)
    antes = snapshot(model)
    hechos = list(dataset.hechos)
    hechos[0] = (*hechos[0][:-1], hechos[0][-1] + Decimal("1.00"))
    with pytest.raises(etl.ErrorDatos, match="datos diferentes"):
        etl.cargar(model, replace(dataset, hechos=hechos))
    assert snapshot(model) == antes


def test_error_tardio_revierte_todas_las_inserciones(model, dataset):
    # Falta una vista que el SQL de conciliación usa después de insertar los hechos.
    model.execute("DROP VIEW dm.v_sucursales")
    with pytest.raises(psycopg.errors.UndefinedTable):
        etl.cargar(model, dataset)
    for tabla in ("fact_ventas", "dim_producto", "dim_sucursal"):
        assert model.execute(f"SELECT count(*) FROM olap.{tabla}").fetchone() == (0,)
    assert model.execute("SELECT to_regclass('pg_temp.entrada_fact_ventas')").fetchone() == (None,)


def test_conflicto_catalogo_revierte_inserciones(model, dataset):
    model.execute("INSERT INTO olap.dim_producto VALUES (1,'HAB-01','Nombre diferente','bebida')")
    with pytest.raises(etl.ErrorDatos, match="dim_producto"):
        etl.cargar(model, dataset)
    assert model.execute("SELECT count(*) FROM olap.dim_sucursal").fetchone() == (0,)
    assert model.execute("SELECT count(*) FROM olap.dim_producto").fetchone() == (1,)
    assert model.execute("SELECT count(*) FROM olap.fact_ventas").fetchone() == (0,)


def test_datos_adicionales_no_se_borran(model, dataset):
    etl.cargar(model, dataset)
    model.execute(
        "INSERT INTO olap.fact_ventas "
        "(detalle_id,ticket_id,fecha,producto_id,sucursal_id,tipo_venta,cantidad,precio_unitario) "
        "VALUES (999999,999999,'2026-01-01',1,1,'local',1,10)"
    )
    antes = snapshot(model)
    with pytest.raises(etl.ErrorDatos, match="datos diferentes"):
        etl.cargar(model, dataset)
    assert snapshot(model) == antes

from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def test_installation_is_independent_and_empty(model):
    assert model.execute("SELECT count(*) FROM olap.dim_fecha").fetchone() == (365,)
    assert model.execute("SELECT count(*) FROM olap.fact_ventas").fetchone() == (0,)
    assert model.execute("SELECT count(*) FROM dm.v_ventas_detalle").fetchone() == (0,)
    assert model.execute("SELECT to_regclass('public.ventas')").fetchone() == (None,)
    assert model.execute("SELECT tipo_venta FROM olap.dim_tipo_venta ORDER BY 1").fetchall() == [
        ("llevar",),
        ("local",),
    ]


def test_calendar_derives_parts_and_covers_boundaries(model):
    assert model.execute(
        "SELECT dia,mes,trimestre,anio FROM olap.dim_fecha WHERE fecha='2026-10-31'"
    ).fetchone() == (31, 10, 4, 2026)
    assert model.execute(
        "SELECT dia,mes,trimestre,anio FROM olap.dim_fecha WHERE fecha='2025-11-01'"
    ).fetchone() == (1, 11, 4, 2025)
    with pytest.raises(psycopg.errors.CheckViolation):
        model.execute("INSERT INTO olap.dim_fecha(fecha) VALUES ('2026-11-01')")


def test_detail_has_no_join_fanout_and_keeps_historical_price(sales):
    assert sales.execute(
        "SELECT count(*),sum(importe),sum(cantidad),count(DISTINCT ticket_id) "
        "FROM dm.v_ventas_detalle"
    ).fetchone() == (6, Decimal("78.00"), 10, 4)
    assert sales.execute(
        "SELECT precio_unitario FROM dm.v_ventas_detalle WHERE producto_id=11 ORDER BY detalle_id"
    ).fetchall() == [(Decimal(10),), (Decimal(12),), (Decimal(10),)]
    assert sales.execute(
        "SELECT sum(importe)/count(DISTINCT ticket_id) FROM dm.v_ventas_detalle"
    ).fetchone() == (Decimal("19.5"),)


def test_monthly_view_counts_multiline_tickets_once(sales):
    rows = sales.execute(
        "SELECT mes_inicio,codigo_sucursal,tipo_venta,ingresos,tickets,unidades,ticket_promedio "
        "FROM dm.v_ventas_mensuales ORDER BY mes_inicio,codigo_sucursal,tipo_venta"
    ).fetchall()
    assert [(str(r[0]), *r[1:]) for r in rows] == [
        ("2025-11-01", "DEMO-01", "llevar", Decimal(12), 1, 1, Decimal(12)),
        ("2025-11-01", "DEMO-01", "local", Decimal(25), 1, 3, Decimal(25)),
        ("2025-12-01", "DEMO-02", "local", Decimal(25), 1, 4, Decimal(25)),
        ("2026-10-01", "DEMO-02", "llevar", Decimal(16), 1, 2, Decimal(16)),
    ]


def test_product_and_branch_views_include_zero_sales_without_duplicates(sales):
    assert sales.execute(
        "SELECT ingresos,tickets,unidades FROM dm.v_productos WHERE producto_id=11"
    ).fetchone() == (Decimal(42), 3, 4)
    assert sales.execute(
        "SELECT ingresos,tickets,unidades,ticket_promedio FROM dm.v_productos WHERE producto_id=12"
    ).fetchone() == (Decimal(0), 0, 0, None)
    assert sales.execute("SELECT count(*),sum(ingresos) FROM dm.v_productos").fetchone() == (
        12,
        Decimal(78),
    )
    assert sales.execute(
        "SELECT ingresos,tickets,unidades,ticket_promedio FROM dm.v_sucursales ORDER BY sucursal_id"
    ).fetchall() == [
        (Decimal(37), 2, 4, Decimal("18.5")),
        (Decimal(41), 2, 6, Decimal("20.5")),
    ]


def test_category_filter_uses_distinct_tickets(sales):
    assert sales.execute(
        "SELECT sum(importe),count(DISTINCT ticket_id),sum(cantidad) "
        "FROM dm.v_ventas_detalle WHERE categoria='bebida' AND codigo_sucursal='DEMO-01'"
    ).fetchone() == (Decimal(32), 2, 3)
    # Dos tickets contienen bebida y pan: sumar tickets por producto daría 6, no 4.
    assert sales.execute("SELECT sum(tickets) FROM dm.v_productos").fetchone() == (6,)


@pytest.mark.parametrize(
    "column,value,error",
    [
        ("cantidad", 0, psycopg.errors.CheckViolation),
        ("cantidad", -1, psycopg.errors.CheckViolation),
        ("cantidad", None, psycopg.errors.NotNullViolation),
        ("precio_unitario", "0", psycopg.errors.CheckViolation),
        ("precio_unitario", "-2.50", psycopg.errors.CheckViolation),
        ("precio_unitario", "NaN", psycopg.errors.CheckViolation),
        ("precio_unitario", None, psycopg.errors.NotNullViolation),
        ("producto_id", 999, psycopg.errors.ForeignKeyViolation),
        ("sucursal_id", 999, psycopg.errors.ForeignKeyViolation),
        ("fecha", "2025-10-31", psycopg.errors.ForeignKeyViolation),
        ("tipo_venta", "delivery", psycopg.errors.ForeignKeyViolation),
        ("ticket_id", 0, psycopg.errors.CheckViolation),
        ("detalle_id", 0, psycopg.errors.CheckViolation),
    ],
)
def test_reject_invalid_fact_values(sales, column, value, error):
    from psycopg import sql

    data = {
        "detalle_id": 999,
        "ticket_id": 999,
        "fecha": "2026-01-01",
        "producto_id": 11,
        "sucursal_id": 31,
        "tipo_venta": "local",
        "cantidad": 1,
        "precio_unitario": "10.25",
    }
    data[column] = value
    with pytest.raises(error):
        sales.execute(
            sql.SQL("INSERT INTO olap.fact_ventas ({}) VALUES ({})").format(
                sql.SQL(",").join(map(sql.Identifier, data)),
                sql.SQL(",").join(sql.Placeholder() for _ in data),
            ),
            list(data.values()),
        )


def test_reloading_detail_or_same_product_in_ticket_is_rejected(sales):
    for detail_id in (101, 999):
        with pytest.raises(psycopg.errors.UniqueViolation):
            sales.execute(
                "INSERT INTO olap.fact_ventas "
                "(detalle_id,ticket_id,fecha,producto_id,sucursal_id,tipo_venta,cantidad,precio_unitario) "
                "VALUES (%s,1001,'2025-11-01',11,31,'local',1,10)",
                (detail_id,),
            )
    assert sales.execute("SELECT count(*),sum(importe) FROM olap.fact_ventas").fetchone() == (
        6,
        Decimal(78),
    )


def test_importe_is_derived_and_cannot_be_overridden(sales):
    with pytest.raises(psycopg.errors.GeneratedAlways):
        sales.execute("UPDATE olap.fact_ventas SET importe=1 WHERE detalle_id=101")
    assert sales.execute(
        "SELECT importe FROM olap.fact_ventas WHERE detalle_id=101"
    ).fetchone() == (Decimal(20),)


def test_dimension_restrictions_and_referenced_history(sales):
    with pytest.raises(psycopg.errors.CheckViolation):
        sales.execute("UPDATE olap.dim_producto SET categoria='otra' WHERE producto_id=11")
    with pytest.raises(psycopg.errors.CheckViolation):
        sales.execute("UPDATE olap.dim_sucursal SET nombre='   ' WHERE sucursal_id=31")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        sales.execute("DELETE FROM olap.dim_producto WHERE producto_id=11")


def test_reinstall_fails_atomically_without_changing_data(sales):
    with pytest.raises(psycopg.errors.DuplicateSchema):
        sales.execute((SQL_DIR / "01_modelo_estrella.sql").read_text())
    sales.execute("ROLLBACK")
    assert sales.execute("SELECT count(*),sum(importe) FROM olap.fact_ventas").fetchone() == (
        6,
        Decimal(78),
    )


def test_validation_small_dataset_and_default_10000_guard(sales):
    sales.execute("SELECT set_config('habits_olap.tickets_esperados','4',false)")
    sales.execute((SQL_DIR / "03_validaciones.sql").read_text())
    sales.execute("RESET habits_olap.tickets_esperados")
    with pytest.raises(psycopg.errors.RaiseException, match="10000 tickets"):
        sales.execute((SQL_DIR / "03_validaciones.sql").read_text())
    sales.execute("ROLLBACK")


@pytest.mark.parametrize(
    "column,value", [("fecha", "2026-01-01"), ("sucursal_id", 32), ("tipo_venta", "llevar")]
)
def test_validation_rejects_incoherent_ticket(sales, column, value):
    from psycopg import sql

    sales.execute(
        sql.SQL("UPDATE olap.fact_ventas SET {}=%s WHERE detalle_id=102").format(
            sql.Identifier(column)
        ),
        (value,),
    )
    sales.execute("SELECT set_config('habits_olap.tickets_esperados','4',false)")
    with pytest.raises(psycopg.errors.RaiseException, match="incoherentes"):
        sales.execute((SQL_DIR / "03_validaciones.sql").read_text())
    sales.execute("ROLLBACK")


def test_smoke_rolls_back_and_can_repeat(sales):
    for _ in range(2):
        sales.execute((SQL_DIR / "04_prueba_humo.sql").read_text())
    assert sales.execute("SELECT count(*),sum(importe) FROM olap.fact_ventas").fetchone() == (
        6,
        Decimal(78),
    )
    assert sales.execute("SELECT count(*) FROM olap.dim_producto").fetchone() == (12,)


def test_installation_preserves_operational_objects(database):
    database.execute("CREATE TABLE public.ventas(id bigint PRIMARY KEY,total numeric)")
    database.execute("INSERT INTO public.ventas VALUES (1,123.45)")
    before = database.execute(
        "SELECT oid,relowner,relacl FROM pg_class WHERE oid='public.ventas'::regclass"
    ).fetchone()
    database.execute((SQL_DIR / "01_modelo_estrella.sql").read_text())
    database.execute((SQL_DIR / "02_datamart.sql").read_text())
    assert database.execute("SELECT * FROM public.ventas").fetchall() == [(1, Decimal("123.45"))]
    assert (
        database.execute(
            "SELECT oid,relowner,relacl FROM pg_class WHERE oid='public.ventas'::regclass"
        ).fetchone()
        == before
    )


def test_validation_failure_rolls_back_etl_transaction(sales):
    sales.execute("SELECT set_config('habits_olap.tickets_esperados','4',false)")
    with pytest.raises(psycopg.errors.RaiseException, match="4 tickets"), sales.transaction():
        sales.execute(
            "INSERT INTO olap.fact_ventas "
            "(detalle_id,ticket_id,fecha,producto_id,sucursal_id,tipo_venta,cantidad,precio_unitario) "
            "VALUES (999,999,'2026-01-01',11,31,'local',1,10)"
        )
        sales.execute((SQL_DIR / "03_validaciones.sql").read_text())
    assert sales.execute("SELECT count(*),sum(importe) FROM olap.fact_ventas").fetchone() == (
        6,
        Decimal(78),
    )

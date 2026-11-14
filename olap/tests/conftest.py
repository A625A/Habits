import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


@pytest.fixture
def database():
    dsn = os.environ.get("OLAP_TEST_ADMIN_DSN")
    if not dsn:
        pytest.fail("Ejecutar: python olap/tests/ejecutar_pruebas.py")
    if not conninfo_to_dict(dsn).get("dbname", "").endswith("_test"):
        pytest.fail("OLAP_TEST_ADMIN_DSN debe usar una base terminada en _test.")
    name = "olap_" + uuid4().hex + "_test"
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(
            sql.SQL("CREATE DATABASE {} OWNER habits_olap_owner").format(sql.Identifier(name))
        )
        try:
            with psycopg.connect(
                make_conninfo(dsn, dbname=name, user="habits_olap_owner"), autocommit=True
            ) as conn:
                yield conn
        finally:
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture
def model(database):
    assert (SQL_DIR / "01_modelo_estrella.sql").exists(), "Falta el modelo estrella"
    database.execute((SQL_DIR / "01_modelo_estrella.sql").read_text())
    database.execute((SQL_DIR / "02_datamart.sql").read_text())
    return database


@pytest.fixture
def sales(model):
    model.execute("""
        INSERT INTO olap.dim_producto(producto_id,codigo,nombre,categoria) VALUES
        (11,'HAB-01','Latte de cardamomo y miel','bebida'),
        (12,'HAB-02','Mocha de chocolate','bebida'),
        (13,'HAB-03','Cold Brew de panela y naranja','bebida'),
        (14,'HAB-04','Latte helado de vainilla y canela','bebida'),
        (15,'HAB-05','Dirty Chai','bebida'),
        (16,'HAB-06','Chai de vainilla y panela','bebida'),
        (17,'HAB-07','Croissant de guayaba y queso crema','panaderia'),
        (18,'HAB-08','Rollo de canela con glaseado de café','panaderia'),
        (19,'HAB-09','Pan de banano','panaderia'),
        (20,'HAB-10','Croissant de espinaca, queso crema y tomate','panaderia'),
        (21,'HAB-11','Cheesecake de café y panela','postre'),
        (22,'HAB-12','Galletas tipo Ferrero Rocher','postre');
        INSERT INTO olap.dim_sucursal(sucursal_id,codigo,nombre) VALUES
        (31,'DEMO-01','Habits Sucursal 1'),(32,'DEMO-02','Habits Sucursal 2');
        INSERT INTO olap.fact_ventas
            (detalle_id,ticket_id,fecha,producto_id,sucursal_id,tipo_venta,cantidad,precio_unitario)
        VALUES
        (101,1001,'2025-11-01',11,31,'local',2,10),
        (102,1001,'2025-11-01',17,31,'local',1,5),
        (103,1002,'2025-11-30',11,31,'llevar',1,12),
        (104,1003,'2025-12-01',17,32,'local',3,5),
        (105,1003,'2025-12-01',11,32,'local',1,10),
        (106,1004,'2026-10-31',21,32,'llevar',2,8);
    """)
    return model

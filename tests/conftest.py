import os
from uuid import uuid4

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo


@pytest.fixture
def database_url():
    load_dotenv()
    url = os.environ.get("TEST_DATABASE_URL")
    if not url or not conninfo_to_dict(url).get("dbname", "").endswith("_test"):
        pytest.fail("Definir TEST_DATABASE_URL con una base exclusiva terminada en _test.")
    schema = "test_" + uuid4().hex
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            yield make_conninfo(url, options=f"-csearch_path={schema}")
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def app(database_url):
    from app import create_app

    return create_app({"TESTING": True, "DATABASE_URL": database_url})

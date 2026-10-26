from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def test_consulta_pendiente_agrega_por_separado_sin_multiplicar_importes(auth_app, database_url):
    query = Path("sql/pendientes/comparacion_ventas_reservas.sql").read_text()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        branch = conn.execute(
            "SELECT sucursal_id FROM sucursales WHERE codigo = 'DEMO-01'"
        ).fetchone()["sucursal_id"]
        # Dobles del contrato SQL, solo temporales. No implementan tablas de negocio.
        conn.execute(
            "CREATE TEMP TABLE reporte_ventas_confirmadas (venta_id BIGINT, sucursal_id BIGINT, fecha TIMESTAMPTZ, total NUMERIC)"
        )
        conn.execute(
            "CREATE TEMP TABLE reporte_reservas_vigentes (reserva_id BIGINT, sucursal_id BIGINT, inicio TIMESTAMPTZ)"
        )
        conn.execute(
            "INSERT INTO reporte_ventas_confirmadas VALUES (1, %s, '2026-10-26 12:00+00', 10), (2, %s, '2026-10-26 13:00+00', 20), (3, %s, '2026-10-27 06:00+00', 100)",
            (branch, branch, branch),
        )
        for value in (1, 2, 3):
            conn.execute(
                "INSERT INTO reporte_reservas_vigentes VALUES (%s, %s, '2026-10-26 12:00+00')",
                (value, branch),
            )
        params = {
            "desde": datetime(2026, 10, 26, 6, tzinfo=UTC),
            "hasta": datetime(2026, 10, 27, 6, tzinfo=UTC),
            "sucursal_id": None,
        }
        rows = conn.execute(query, params).fetchall()
        assert [(r["codigo"], r["reservas"], r["ventas"], r["importe_ventas"]) for r in rows] == [
            ("DEMO-01", 3, 2, Decimal(30)),
            ("DEMO-02", 0, 0, Decimal(0)),
        ]
        params["sucursal_id"] = branch
        assert len(conn.execute(query, params).fetchall()) == 1

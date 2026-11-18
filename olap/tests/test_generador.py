"""Pruebas independientes de PostgreSQL: python -m unittest discover ..."""

import csv
import importlib.util
import re
import tempfile
import unittest
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

OLAP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('generador', OLAP / 'scripts' / 'generar_datos.py')
generador = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generador)


def leer(base, nombre):
    with (base / nombre).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        generador.generar(cls.base)
        cls.ventas = leer(cls.base, 'ventas.csv')
        cls.detalles = leer(cls.base, 'detalle_ventas.csv')

    def test_catalogo_corresponde_a_fuente(self):
        fuente = (OLAP.parent / 'sql/fase1/cargar_catalogo.sql').read_text(encoding='utf-8')
        esperados = re.findall(r"\('(HAB-\d+)','([^']+)','([^']+)',(\d+)\)", fuente)
        productos = leer(self.base, 'productos.csv')
        self.assertEqual(len(productos), 12)
        self.assertEqual([(p['codigo'], p['nombre'], p['categoria'], Decimal(p['precio']))
                          for p in productos],
                         [(c, n, cat, Decimal(precio)) for c, n, cat, precio in esperados])
        for s in leer(self.base, 'sucursales.csv'):
            self.assertIn(f"('{s['codigo']}','{s['nombre']}')", fuente)

    def test_periodo_tickets_y_referencias(self):
        self.assertEqual(len(self.ventas), 10_000)
        ids = {v['venta_id'] for v in self.ventas}
        self.assertEqual(len(ids), 10_000)
        sucursales = {s['sucursal_id'] for s in leer(self.base, 'sucursales.csv')}
        self.assertEqual(len(sucursales), 2)
        dias = set()
        for venta in self.ventas:
            dia = date.fromisoformat(venta['fecha'])
            self.assertTrue(date(2025, 11, 1) <= dia <= date(2026, 10, 31))
            self.assertGreater(int(venta['venta_id']), 0)
            self.assertIn(venta['sucursal_id'], sucursales)
            self.assertIn(venta['tipo_venta'], ('local', 'llevar'))
            dias.add(dia)
        self.assertEqual(len(dias), 365)
        self.assertEqual({d['venta_id'] for d in self.detalles}, ids)

    def test_detalles_unicos_y_montos_validos(self):
        productos = {p['producto_id'] for p in leer(self.base, 'productos.csv')}
        self.assertEqual(len({d['detalle_id'] for d in self.detalles}), len(self.detalles))
        self.assertEqual(len({(d['venta_id'], d['producto_id']) for d in self.detalles}),
                         len(self.detalles))
        for detalle in self.detalles:
            self.assertGreater(int(detalle['detalle_id']), 0)
            self.assertIn(detalle['producto_id'], productos)
            self.assertGreater(int(detalle['cantidad']), 0)
            precio = Decimal(detalle['precio_unitario'])
            self.assertTrue(precio.is_finite() and precio > 0)
            self.assertEqual(precio, precio.quantize(Decimal('.01')))
        self.assertEqual({d['producto_id'] for d in self.detalles}, productos)
        self.assertTrue(all(1 <= n <= 4 for n in Counter(
            d['venta_id'] for d in self.detalles).values()))

    def test_reproducible_y_csv_publicados(self):
        for nombre in ('productos.csv', 'sucursales.csv', 'ventas.csv', 'detalle_ventas.csv'):
            self.assertEqual((self.base / nombre).read_bytes(),
                             (OLAP / 'data/raw' / nombre).read_bytes())
        otra = self.base / 'otra'
        generador.generar(otra)
        self.assertEqual((self.base / 'detalle_ventas.csv').read_bytes(),
                         (otra / 'detalle_ventas.csv').read_bytes())
        generador.generar(otra, semilla=7)
        self.assertNotEqual((self.base / 'detalle_ventas.csv').read_bytes(),
                            (otra / 'detalle_ventas.csv').read_bytes())


if __name__ == '__main__':
    unittest.main()

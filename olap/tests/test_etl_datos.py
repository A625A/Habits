"""Validación de entrada sin usar PostgreSQL."""

import csv
import importlib.util
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

OLAP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("habits_etl", OLAP / "scripts/etl.py")
etl = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = etl
spec.loader.exec_module(etl)


class ValidacionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / "raw"
        shutil.copytree(OLAP / "data/raw", self.base)

    def cambiar(self, tabla, columna, valor, indice=0, duplicar=False, quitar=False):
        ruta = self.base / f"{tabla}.csv"
        with ruta.open(encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo)
            campos = lector.fieldnames
            filas = list(lector)
        if duplicar:
            filas.append(dict(filas[indice]))
        elif quitar:
            filas = [fila for fila in filas if fila["venta_id"] != valor]
        else:
            filas[indice][columna] = valor
        with ruta.open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=campos)
            escritor.writeheader()
            escritor.writerows(filas)

    def test_totales_y_precio_historico(self):
        dataset = etl.validar(self.base)
        self.assertEqual(
            dataset.resumen,
            {
                "ventas": 10000,
                "detalles": 19175,
                "unidades": 23641,
                "ingresos_gtq": Decimal("583177.42"),
            },
        )
        self.assertTrue(any(f[7] == Decimal("24.70") for f in dataset.hechos))

    def test_normaliza_bom_espacios_y_tipo(self):
        ruta = self.base / "ventas.csv"
        original = ruta.read_text(encoding="utf-8")
        ruta.write_text(
            "\ufeff" + original.replace(",local", ", LOCAL ").replace(",llevar", ", LLEVAR "),
            encoding="utf-8",
        )
        self.assertEqual(etl.validar(self.base).resumen, etl.validar().resumen)

    def test_rechaza_datos_incorrectos(self):
        casos = [
            ("ventas", "fecha", "2026-02-30"),
            ("ventas", "fecha", "2026-11-01"),
            ("ventas", "fecha", "20251101"),
            ("ventas", "sucursal_id", "999"),
            ("ventas", "tipo_venta", "delivery"),
            ("ventas", "venta_id", "0"),
            ("ventas", "venta_id", "9223372036854775808"),
            ("productos", "categoria", "otra"),
            ("productos", "precio", "-2"),
            ("sucursales", "codigo", "AJENA"),
            ("detalle_ventas", "venta_id", "999999"),
            ("detalle_ventas", "producto_id", "999"),
            ("detalle_ventas", "cantidad", "-1"),
            ("detalle_ventas", "cantidad", "0"),
            ("detalle_ventas", "cantidad", "1.5"),
            ("detalle_ventas", "cantidad", "2147483648"),
            ("detalle_ventas", "precio_unitario", "NaN"),
            ("detalle_ventas", "precio_unitario", "Infinity"),
            ("detalle_ventas", "precio_unitario", "0"),
            ("detalle_ventas", "precio_unitario", "-1"),
            ("detalle_ventas", "precio_unitario", "1.001"),
            ("detalle_ventas", "precio_unitario", "10000000000.00"),
            ("detalle_ventas", "precio_unitario", ""),
        ]
        for tabla, columna, valor in casos:
            with self.subTest(tabla=tabla, columna=columna, valor=valor):
                shutil.copytree(OLAP / "data/raw", self.base, dirs_exist_ok=True)
                self.cambiar(tabla, columna, valor)
                with self.assertRaises(etl.ErrorDatos):
                    etl.validar(self.base)

    def test_rechaza_duplicados(self):
        for tabla in etl.ENCABEZADOS:
            with self.subTest(tabla=tabla):
                shutil.copytree(OLAP / "data/raw", self.base, dirs_exist_ok=True)
                self.cambiar(tabla, "", "", duplicar=True)
                with self.assertRaisesRegex(etl.ErrorDatos, "duplicado"):
                    etl.validar(self.base)

    def test_rechaza_producto_repetido_en_ticket(self):
        self.cambiar("detalle_ventas", "detalle_id", "999999")
        self.cambiar("detalle_ventas", "", "", duplicar=True)
        self.cambiar("detalle_ventas", "detalle_id", "999998")
        with self.assertRaisesRegex(etl.ErrorDatos, "producto duplicado"):
            etl.validar(self.base)

    def test_rechaza_venta_sin_detalles(self):
        self.cambiar("detalle_ventas", "", "1", quitar=True)
        with self.assertRaisesRegex(etl.ErrorDatos, "sin detalles"):
            etl.validar(self.base)

    def test_rechaza_numero_incorrecto_de_ventas(self):
        self.cambiar("ventas", "", "1", quitar=True)
        with self.assertRaisesRegex(etl.ErrorDatos, "10000"):
            etl.validar(self.base)

    def test_rechaza_encabezado_y_filas_mal_formadas(self):
        ruta = self.base / "ventas.csv"
        original = ruta.read_text(encoding="utf-8")
        for contenido in (
            original.replace("venta_id", "ticket_id", 1),
            original + "10001,2026-01-01,1,local,extra\n",
            original + "10001,2026-01-01\n",
        ):
            with self.subTest(contenido=contenido[-60:]):
                ruta.write_text(contenido, encoding="utf-8")
                with self.assertRaises(etl.ErrorDatos):
                    etl.validar(self.base)


if __name__ == "__main__":
    unittest.main()

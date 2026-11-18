"""Genera 10,000 tickets simulados sin conectarse a bases operativas."""

import argparse
import csv
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

OLAP = Path(__file__).resolve().parents[1]
INICIO = date(2025, 11, 1)
FIN = date(2026, 10, 31)
SEMILLA = 20251101
TOTAL_VENTAS = 10_000


def leer_catalogo(nombre):
    with (OLAP / 'data' / 'catalogo' / nombre).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def escribir_csv(ruta, columnas, filas):
    with ruta.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columnas, lineterminator='\n')
        writer.writeheader()
        writer.writerows(filas)


def generar(salida=OLAP / 'data' / 'raw', semilla=SEMILLA):
    rng = random.Random(semilla)
    productos = leer_catalogo('productos.csv')
    sucursales = leer_catalogo('sucursales.csv')
    fechas = [INICIO + timedelta(days=i) for i in range((FIN - INICIO).days + 1)]
    pesos_mes = {11: 1.08, 12: 1.35, 1: .85, 2: .92, 3: 1.02, 4: 1.05,
                 5: 1.15, 6: 1.0, 7: 1.03, 8: 1.02, 9: .95, 10: 1.08}
    pesos_fecha = [pesos_mes[d.month] * (0.85, .90, .95, 1, 1.25, 1.40, 1.15)[d.weekday()]
                   for d in fechas]
    dias = sorted(rng.choices(fechas, weights=pesos_fecha, k=TOTAL_VENTAS))
    ventas, detalles = [], []
    popularidad = [1.6, 1.4, 1.2, 1.3, 1.0, .9, 1.1, 1.3, .8, .8, .7, 1.0]
    for venta_id, dia in enumerate(dias, 1):
        sucursal = rng.choices(sucursales, weights=[58, 42])[0]
        llevar = .42 if sucursal['codigo'] == 'DEMO-01' else .62
        ventas.append(dict(venta_id=venta_id, fecha=dia.isoformat(),
                           sucursal_id=sucursal['sucursal_id'],
                           tipo_venta='llevar' if rng.random() < llevar else 'local'))
        disponibles = list(productos)
        pesos = list(popularidad)
        if dia.month in (3, 4, 5):
            pesos[2] *= 1.5
            pesos[3] *= 1.5
        descuento = Decimal('.95') if rng.random() < .12 else Decimal('1')
        ajuste = Decimal('1.04') if dia >= date(2026, 5, 1) else Decimal('1')
        for _ in range(rng.choices([1, 2, 3, 4], weights=[36, 42, 18, 4])[0]):
            indice = rng.choices(range(len(disponibles)), weights=pesos)[0]
            producto = disponibles.pop(indice)
            pesos.pop(indice)
            precio = (Decimal(producto['precio']) * ajuste * descuento).quantize(
                Decimal('.01'), rounding=ROUND_HALF_UP)
            detalles.append(dict(detalle_id=len(detalles) + 1, venta_id=venta_id,
                                 producto_id=producto['producto_id'],
                                 cantidad=rng.choices([1, 2, 3], weights=[80, 17, 3])[0],
                                 precio_unitario=str(precio)))
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    escribir_csv(salida / 'sucursales.csv', ['sucursal_id', 'codigo', 'nombre'], sucursales)
    escribir_csv(salida / 'productos.csv',
                 ['producto_id', 'codigo', 'nombre', 'categoria', 'precio'], productos)
    escribir_csv(salida / 'ventas.csv',
                 ['venta_id', 'fecha', 'sucursal_id', 'tipo_venta'], ventas)
    escribir_csv(salida / 'detalle_ventas.csv',
                 ['detalle_id', 'venta_id', 'producto_id', 'cantidad', 'precio_unitario'], detalles)
    return len(ventas), len(detalles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', type=Path, default=OLAP / 'data' / 'raw')
    parser.add_argument('--semilla', type=int, default=SEMILLA)
    args = parser.parse_args()
    ventas, detalles = generar(args.salida, args.semilla)
    print(f'Generadas {ventas:,} ventas y {detalles:,} detalles en {args.salida}')


if __name__ == '__main__':
    main()

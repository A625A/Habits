"""Valida cuatro CSV y carga exclusivamente el esquema analítico de Habits."""

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

OLAP = Path(__file__).resolve().parents[1]
ENCABEZADOS = {
    "sucursales": ("sucursal_id", "codigo", "nombre"),
    "productos": ("producto_id", "codigo", "nombre", "categoria", "precio"),
    "ventas": ("venta_id", "fecha", "sucursal_id", "tipo_venta"),
    "detalle_ventas": ("detalle_id", "venta_id", "producto_id", "cantidad", "precio_unitario"),
}


class ErrorDatos(ValueError):
    """Entrada inválida; nunca se descartan silenciosamente filas."""


def leer_csv(directorio, tabla):
    ruta = Path(directorio) / f"{tabla}.csv"
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.reader(archivo, strict=True)
        columnas = next(lector, [])
        if tuple(c.strip() for c in columnas) != ENCABEZADOS[tabla]:
            raise ErrorDatos(f"{ruta.name}: encabezados incorrectos")
        for fila in lector:
            if len(fila) != len(columnas):
                raise ErrorDatos(
                    f"{ruta.name}, línea {lector.line_num}: columnas incompletas o extra"
                )
            valores = [v.strip() for v in fila]
            if not all(valores):
                raise ErrorDatos(f"{ruta.name}, línea {lector.line_num}: campo vacío")
            yield dict(zip(ENCABEZADOS[tabla], valores)), f"{ruta.name}, línea {lector.line_num}"


def entero(valor, contexto, limite=9223372036854775807):
    if not re.fullmatch(r"[0-9]+", valor) or not 0 < int(valor) <= limite:
        raise ErrorDatos(f"{contexto}: entero positivo fuera de rango")
    return int(valor)


def precio(valor, contexto):
    try:
        numero = Decimal(valor)
    except InvalidOperation:
        raise ErrorDatos(f"{contexto}: precio inválido") from None
    if (
        not numero.is_finite()
        or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", valor)
        or not Decimal(0) < numero <= Decimal("9999999999.99")
    ):
        raise ErrorDatos(f"{contexto}: precio inválido; usar GTQ positivos con hasta dos decimales")
    return numero


def texto(valor, limite, contexto):
    if len(valor) > limite or "\x00" in valor:
        raise ErrorDatos(f"{contexto}: texto inválido o demasiado largo")
    return valor


def unico(registro, clave, valor, contexto):
    if clave in registro:
        raise ErrorDatos(f"{contexto}: duplicado ({clave})")
    registro[clave] = valor


@dataclass
class Dataset:
    sucursales: list
    productos: list
    hechos: list
    tickets: int

    @property
    def resumen(self):
        return {
            "ventas": self.tickets,
            "detalles": len(self.hechos),
            "unidades": sum(f[6] for f in self.hechos),
            "ingresos_gtq": sum((f[6] * f[7] for f in self.hechos), Decimal("0.00")),
        }


def validar(directorio=OLAP / "data/raw"):
    sucursales, productos, ventas, detalles = {}, {}, {}, {}
    for tabla, destino, id_col in (
        ("sucursales", sucursales, "sucursal_id"),
        ("productos", productos, "producto_id"),
    ):
        codigos = set()
        for fila, ctx in leer_csv(directorio, tabla):
            identificador = entero(fila[id_col], ctx)
            codigo = texto(fila["codigo"], 30, ctx)
            nombre = texto(fila["nombre"], 120, ctx)
            if codigo in codigos:
                raise ErrorDatos(f"{ctx}: código duplicado")
            codigos.add(codigo)
            valores = (identificador, codigo, nombre)
            if tabla == "productos":
                if fila["categoria"] not in ("bebida", "panaderia", "postre"):
                    raise ErrorDatos(f"{ctx}: categoría inválida")
                precio(fila["precio"], ctx)
                valores += (fila["categoria"],)
            unico(destino, identificador, valores, ctx)
        referencia = set()
        for fila, ctx in leer_csv(OLAP / "data/catalogo", tabla):
            valores = (int(fila[id_col]), fila["codigo"], fila["nombre"])
            if tabla == "productos":
                valores += (fila["categoria"],)
            referencia.add(valores)
        if set(destino.values()) != referencia:
            raise ErrorDatos(f"{tabla}.csv: no coincide con el catálogo original de Habits")

    for fila, ctx in leer_csv(directorio, "ventas"):
        venta_id = entero(fila["venta_id"], ctx)
        try:
            fecha = date.fromisoformat(fila["fecha"])
        except ValueError:
            raise ErrorDatos(f"{ctx}: fecha inválida") from None
        if fecha.isoformat() != fila["fecha"] or not date(2025, 11, 1) <= fecha <= date(
            2026, 10, 31
        ):
            raise ErrorDatos(f"{ctx}: fecha fuera del período o formato ISO incorrecto")
        sucursal_id = entero(fila["sucursal_id"], ctx)
        if sucursal_id not in sucursales:
            raise ErrorDatos(f"{ctx}: referencia a sucursal inexistente")
        tipo = fila["tipo_venta"].lower()
        if tipo not in ("local", "llevar"):
            raise ErrorDatos(f"{ctx}: tipo de venta inválido")
        unico(ventas, venta_id, (fecha, sucursal_id, tipo), ctx)
    if len(ventas) != 10_000:
        raise ErrorDatos("ventas.csv: se requieren exactamente 10000 ventas")

    pares, tickets = set(), set()
    for fila, ctx in leer_csv(directorio, "detalle_ventas"):
        detalle_id = entero(fila["detalle_id"], ctx)
        venta_id = entero(fila["venta_id"], ctx)
        producto_id = entero(fila["producto_id"], ctx)
        if venta_id not in ventas or producto_id not in productos:
            raise ErrorDatos(f"{ctx}: referencia a venta o producto inexistente")
        par = (venta_id, producto_id)
        if par in pares:
            raise ErrorDatos(f"{ctx}: producto duplicado dentro de la venta")
        pares.add(par)
        cantidad = entero(fila["cantidad"], ctx, limite=2147483647)
        precio_unitario = precio(fila["precio_unitario"], ctx)
        fecha, sucursal_id, tipo = ventas[venta_id]
        unico(
            detalles,
            detalle_id,
            (
                detalle_id,
                venta_id,
                fecha,
                producto_id,
                sucursal_id,
                tipo,
                cantidad,
                precio_unitario,
            ),
            ctx,
        )
        tickets.add(venta_id)
    if tickets != ventas.keys():
        raise ErrorDatos("detalle_ventas.csv: hay ventas sin detalles")
    return Dataset(
        list(sucursales.values()), list(productos.values()), list(detalles.values()), len(ventas)
    )


def cargar(conexion, dataset):
    """Carga atómica; una recarga idéntica no altera hechos existentes.

    Una conexión debe estar fuera de una transacción previa. Los conflictos
    con datos históricos diferentes abortan, sin sobrescribir ni borrar datos.
    """
    from psycopg.pq import TransactionStatus

    if conexion.info.transaction_status != TransactionStatus.IDLE:
        raise ErrorDatos("La conexión debe estar fuera de una transacción previa")
    columnas_hechos = (
        "detalle_id,ticket_id,fecha,producto_id,sucursal_id,tipo_venta,cantidad,precio_unitario"
    )
    # Solo identificadores constantes del programa; nunca provienen del CSV.
    tablas = (
        ("dim_sucursal", "sucursal_id,codigo,nombre", dataset.sucursales),
        ("dim_producto", "producto_id,codigo,nombre,categoria", dataset.productos),
        ("fact_ventas", columnas_hechos, dataset.hechos),
    )
    with conexion.transaction():
        conexion.execute(
            "LOCK TABLE olap.dim_sucursal, olap.dim_producto, "
            "olap.fact_ventas IN SHARE ROW EXCLUSIVE MODE"
        )
        with conexion.cursor() as cursor:
            for tabla, columnas, filas in tablas:
                temporal = f"entrada_{tabla}"
                cursor.execute(
                    f"CREATE TEMP TABLE {temporal} ON COMMIT DROP AS "
                    f"SELECT {columnas} FROM olap.{tabla} WITH NO DATA"
                )
                with cursor.copy(f"COPY {temporal} ({columnas}) FROM STDIN") as copia:
                    for fila in filas:
                        copia.write_row(fila)
                cursor.execute(
                    f"INSERT INTO olap.{tabla} ({columnas}) "
                    f"SELECT {columnas} FROM {temporal} ON CONFLICT DO NOTHING"
                )
                cursor.execute(
                    f"SELECT EXISTS ((SELECT {columnas} FROM olap.{tabla} "
                    f"EXCEPT SELECT {columnas} FROM {temporal}) UNION ALL "
                    f"(SELECT {columnas} FROM {temporal} "
                    f"EXCEPT SELECT {columnas} FROM olap.{tabla}))"
                )
                if cursor.fetchone()[0]:
                    raise ErrorDatos(
                        f"{tabla}: el destino contiene datos diferentes; carga revertida"
                    )
        conexion.execute((OLAP / "sql/03_validaciones.sql").read_text(encoding="utf-8"))
        resultado = conexion.execute(
            "SELECT count(DISTINCT ticket_id), count(*), sum(cantidad), sum(importe) "
            "FROM olap.fact_ventas"
        ).fetchone()
        resumen = dataset.resumen
        if resultado != (
            resumen["ventas"],
            resumen["detalles"],
            resumen["unidades"],
            resumen["ingresos_gtq"],
        ):
            raise ErrorDatos("Los totales cargados no coinciden con los CSV; carga revertida")
    return dataset.resumen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=OLAP / "data/raw")
    parser.add_argument("--solo-validar", action="store_true", help="No requiere PostgreSQL")
    args = parser.parse_args()
    try:
        dataset = validar(args.datos)
    except (ErrorDatos, OSError, UnicodeError, csv.Error) as exc:
        print(f"Validación fallida: {exc}", file=sys.stderr)
        return 1
    if args.solo_validar:
        print(f"CSV válidos: {dataset.resumen}")
        return 0
    dsn = os.environ.get("OLAP_DATABASE_URL")
    if not dsn:
        parser.error("Definir OLAP_DATABASE_URL para la base analítica de destino")
    import psycopg

    try:
        with psycopg.connect(dsn) as conexion:
            resumen = cargar(conexion, dataset)
    except (ErrorDatos, psycopg.Error):
        # No imprimir el DSN ni mensajes del servidor que puedan contener secretos.
        print(
            "Carga fallida y revertida: comprobar conexión, modelo, permisos y "
            "compatibilidad de los datos existentes.",
            file=sys.stderr,
        )
        return 1
    print(f"Carga completada: {resumen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

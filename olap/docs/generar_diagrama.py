"""Genera el PDF de la estrella; requiere ReportLab solo para regenerarlo."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

OUTPUT = Path(__file__).with_name("modelo_estrella.pdf")
INK = colors.HexColor("#15343A")
TEAL = colors.HexColor("#176D72")
LIGHT = colors.HexColor("#EFF7F6")
MUTED = colors.HexColor("#4A6569")


def table(pdf, x, y, width, title, rows, *, fact=False):
    height = 36 + len(rows) * 22
    pdf.setFillColor(LIGHT if fact else colors.white)
    pdf.setStrokeColor(TEAL)
    pdf.setLineWidth(1.2)
    pdf.roundRect(x, y, width, height, 8, fill=1, stroke=1)
    pdf.setFillColor(TEAL if fact else INK)
    pdf.roundRect(x, y + height - 33, width, 33, 8, fill=1, stroke=0)
    pdf.rect(x, y + height - 33, width, 8, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x + 12, y + height - 22, title)
    for index, row in enumerate(rows):
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x + 12, y + height - 51 - index * 22, row)
    return height


def relation(pdf, points):
    pdf.setStrokeColor(TEAL)
    pdf.setLineWidth(1.4)
    path = pdf.beginPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    pdf.drawPath(path)
    start_x, start_y = points[0]
    end_x, end_y = points[-1]
    pdf.setFillColor(TEAL)
    pdf.circle(start_x, start_y, 2.5, fill=1, stroke=0)
    pdf.circle(end_x, end_y, 2.5, fill=1, stroke=0)
    direction = 1 if end_x > start_x else -1
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(start_x + 12 * direction, start_y + 7, "1")
    pdf.drawCentredString(end_x - 12 * direction, end_y + 7, "N")


def main():
    pdf = canvas.Canvas(str(OUTPUT), pagesize=landscape(A4))
    pdf.setTitle("Habits - Modelo estrella OLAP")
    pdf.setAuthor("Andrew - Proyecto 3, Base de Datos 1")
    width, height = landscape(A4)
    pdf.setFillColor(colors.HexColor("#FAFCFB"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawString(35, height - 48, "Habits | Modelo estrella")
    pdf.setFont("Helvetica", 11)
    pdf.setFillColor(MUTED)
    pdf.drawString(
        35, height - 71, "Proyecto 3 - Andrew  |  PostgreSQL  |  Nov. 2025 a oct. 2026  |  GTQ"
    )

    table(
        pdf,
        35,
        328,
        210,
        "olap.dim_fecha",
        [
            "PK  fecha : DATE",
            "dia : SMALLINT",
            "mes : SMALLINT",
            "trimestre : SMALLINT",
            "anio : SMALLINT",
        ],
    )
    table(
        pdf,
        35,
        117,
        210,
        "olap.dim_producto",
        [
            "PK  producto_id : BIGINT",
            "UK  codigo : VARCHAR(30)",
            "nombre : VARCHAR(120)",
            "categoria : VARCHAR(20)",
        ],
    )
    table(
        pdf,
        285,
        194,
        270,
        "olap.fact_ventas",
        [
            "PK  detalle_id : BIGINT",
            "ticket_id : BIGINT",
            "FK  fecha : DATE",
            "FK  producto_id : BIGINT",
            "FK  sucursal_id : BIGINT",
            "FK  tipo_venta : VARCHAR(10)",
            "cantidad : INTEGER",
            "precio_unitario : NUMERIC(12,2)",
            "importe : NUMERIC(22,2) [generado]",
        ],
        fact=True,
    )
    table(
        pdf,
        595,
        350,
        210,
        "olap.dim_sucursal",
        [
            "PK  sucursal_id : BIGINT",
            "UK  codigo : VARCHAR(30)",
            "nombre : VARCHAR(120)",
        ],
    )
    table(
        pdf,
        595,
        173,
        210,
        "olap.dim_tipo_venta",
        [
            "PK  tipo_venta : VARCHAR(10)",
            "Valores: local, llevar",
        ],
    )

    relation(pdf, [(245, 423), (265, 423), (265, 333), (285, 333)])
    relation(pdf, [(245, 190), (265, 190), (265, 311), (285, 311)])
    relation(pdf, [(595, 401), (575, 401), (575, 289), (555, 289)])
    relation(pdf, [(595, 202), (575, 202), (575, 267), (555, 267)])

    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(35, 87, "Grano: un producto vendido dentro de un ticket. Cuatro relaciones 1:N.")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(MUTED)
    pdf.drawString(
        35, 67, "UNIQUE(ticket_id, producto_id)  |  importe = cantidad x precio_unitario histórico"
    )
    pdf.drawString(
        35,
        49,
        "Ingresos: SUM(importe)  |  Tickets: COUNT(DISTINCT ticket_id)  |  Promedio: ingresos / tickets",
    )
    pdf.drawRightString(width - 35, 23, "PK: primaria   FK: foránea   UK: única  |  1 / 1")
    pdf.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()

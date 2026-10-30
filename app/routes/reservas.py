"""Chris: mesas y reservas. Blueprint reservado, sin funcionalidades implementadas."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
import psycopg
from psycopg.errors import ExclusionViolation
from app.db import get_db

bp = Blueprint("reservas", __name__, url_prefix="/reservas")


@bp.route("/", methods=["GET"])
def index():
    sucursal_id = request.args.get("sucursal_id", type=int)
    fecha = request.args.get("fecha", "").strip()

    db = get_db()

    # Catálogos auxiliares
    sucursales = db.execute("SELECT sucursal_id, nombre FROM sucursales ORDER BY nombre;").fetchall()
    clientes = db.execute("SELECT cliente_id, nombre FROM clientes ORDER BY nombre;").fetchall()
    mesas = db.execute(
        "SELECT mesa_id, sucursal_id, numero_mesa, capacidad FROM mesas ORDER BY numero_mesa;"
    ).fetchall()

    # Listado con filtros
    query = """
        SELECT r.reserva_id, s.nombre AS sucursal, m.numero_mesa, c.nombre AS cliente,
               r.fecha_inicio, r.fecha_fin, r.personas, r.estado
        FROM reservas r
        JOIN sucursales s ON r.sucursal_id = s.sucursal_id
        JOIN mesas m ON r.mesa_id = m.mesa_id
        JOIN clientes c ON r.cliente_id = c.cliente_id
        WHERE 1=1
    """
    params = []
    if sucursal_id:
        query += " AND r.sucursal_id = %s"
        params.append(sucursal_id)
    if fecha:
        query += " AND DATE(r.fecha_inicio) = %s"
        params.append(fecha)

    query += " ORDER BY r.fecha_inicio DESC LIMIT 100;"
    reservas = db.execute(query, tuple(params)).fetchall()

    return render_template(
        "reservas.html",
        reservas=reservas,
        sucursales=sucursales,
        clientes=clientes,
        mesas=mesas,
        f_sucursal=sucursal_id,
        f_fecha=fecha,
    )


@bp.route("/crear", methods=["POST"])
def crear():
    sucursal_id = request.form.get("sucursal_id", type=int)
    mesa_id = request.form.get("mesa_id", type=int)
    cliente_id = request.form.get("cliente_id", type=int)
    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin = request.form.get("fecha_fin")
    personas = request.form.get("personas", type=int)

    db = get_db()
    try:
        with db.transaction():
            # Validar que la mesa pertenezca a la sucursal
            mesa_valida = db.execute(
                "SELECT 1 FROM mesas WHERE mesa_id = %s AND sucursal_id = %s;",
                (mesa_id, sucursal_id),
            ).fetchone()

            if not mesa_valida:
                flash("La mesa seleccionada no pertenece a la sucursal indicada.", "danger")
                return redirect(url_for("reservas.index"))

            # Insertar reserva
            db.execute(
                """
                INSERT INTO reservas (sucursal_id, mesa_id, cliente_id, fecha_inicio, fecha_fin, personas, estado)
                VALUES (%s, %s, %s, %s, %s, %s, 'confirmada');
                """,
                (sucursal_id, mesa_id, cliente_id, fecha_inicio, fecha_fin, personas),
            )

        flash("Reserva confirmada con éxito.", "success")
    except ExclusionViolation:
        flash("Conflicto de horario: la mesa ya se encuentra reservada en ese rango.", "warning")
    except psycopg.Error as e:
        flash(f"Error de base de datos: {e}", "danger")
    except Exception as e:
        flash(f"Error inesperado: {e}", "danger")

    return redirect(url_for("reservas.index"))


@bp.route("/<int:reserva_id>/cancelar", methods=["POST"])
def cancelar(reserva_id: int):
    db = get_db()
    try:
        with db.transaction():
            db.execute(
                """
                UPDATE reservas
                SET estado = 'cancelada'
                WHERE reserva_id = %s AND estado IN ('pendiente', 'confirmada');
                """,
                (reserva_id,),
            )
        flash("Reserva cancelada. La mesa quedó disponible.", "info")
    except psycopg.Error as e:
        flash(f"Error al cancelar reserva: {e}", "danger")

    return redirect(url_for("reservas.index"))
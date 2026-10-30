"""Chris: clientes e historial. Blueprint reservado, sin funcionalidades implementadas."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
import psycopg
from app.db import get_db

bp = Blueprint("clientes", __name__, url_prefix="/clientes")


@bp.route("/", methods=["GET"])
def index():
    query = request.args.get("q", "").strip()
    db = get_db()

    if query:
        clientes = db.execute(
            """
            SELECT cliente_id, nombre, telefono, email, fecha_registro
            FROM clientes
            WHERE nombre ILIKE %s OR email ILIKE %s
            ORDER BY nombre;
            """,
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        clientes = db.execute(
            """
            SELECT cliente_id, nombre, telefono, email, fecha_registro
            FROM clientes 
            ORDER BY cliente_id DESC 
            LIMIT 50;
            """
        ).fetchall()

    return render_template("clientes.html", clientes=clientes, query=query)


@bp.route("/crear", methods=["POST"])
def crear():
    nombre = request.form.get("nombre", "").strip()
    telefono = request.form.get("telefono", "").strip() or None
    email = request.form.get("email", "").strip() or None

    if not nombre:
        flash("El nombre del cliente es obligatorio.", "danger")
        return redirect(url_for("clientes.index"))

    db = get_db()
    try:
        with db.transaction():
            db.execute(
                """
                INSERT INTO clientes (nombre, telefono, email)
                VALUES (%s, %s, %s);
                """,
                (nombre, telefono, email),
            )
        flash("Cliente registrado exitosamente.", "success")
    except psycopg.Error as e:
        flash(f"Error al registrar cliente: {e}", "danger")
    except Exception as e:
        flash(f"Error inesperado: {e}", "danger")

    return redirect(url_for("clientes.index"))


@bp.route("/<int:cliente_id>/historial", methods=["GET"])
def historial(cliente_id: int):
    db = get_db()

    cliente = db.execute(
        "SELECT cliente_id, nombre, telefono, email, fecha_registro FROM clientes WHERE cliente_id = %s;",
        (cliente_id,),
    ).fetchone()

    if not cliente:
        flash("Cliente no encontrado.", "warning")
        return redirect(url_for("clientes.index"))

    # Historial de reservas
    reservas = db.execute(
        """
        SELECT r.reserva_id, s.nombre AS sucursal, m.numero_mesa, r.fecha_inicio, r.fecha_fin, r.personas, r.estado
        FROM reservas r
        JOIN sucursales s ON r.sucursal_id = s.sucursal_id
        JOIN mesas m ON r.mesa_id = m.mesa_id
        WHERE r.cliente_id = %s
        ORDER BY r.fecha_inicio DESC;
        """,
        (cliente_id,),
    ).fetchall()

    # Preferencias de productos
    preferencias = db.execute(
        """
        SELECT p.nombre AS producto, pref.nota_preferencia
        FROM preferencias_cliente pref
        LEFT JOIN productos p ON pref.producto_id = p.producto_id
        WHERE pref.cliente_id = %s;
        """,
        (cliente_id,),
    ).fetchall()

    # Observaciones registradas
    observaciones = db.execute(
        """
        SELECT observacion, fecha_creacion
        FROM observaciones_cliente
        WHERE cliente_id = %s
        ORDER BY fecha_creacion DESC;
        """,
        (cliente_id,),
    ).fetchall()

    return render_template(
        "cliente_historial.html",
        cliente=cliente,
        reservas=reservas,
        preferencias=preferencias,
        observaciones=observaciones,
    )
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import Usuario
from extensions import db
from sqlalchemy import text

routes = Blueprint('routes', __name__)

# Diccionario de claves primarias
primary_keys = {
    'payments': ['payment_id'],
    'customers': ['customer_id'],
    'products': ['product_id'],
    'orders': ['order_id'],
    'categories': ['category_id'],
    'order_details': ['order_id', 'product_id'],
    'log_auditoria': ['id'],
    'usuarios': ['id'],
    'auditoria_completa_ordenes': ['order_id'],
    'auditoria_ordenes_recientes': ['order_id'],
    'auditoria_pagos_altos': ['payment_id', 'order_id'],
    'historial_compras_clientes': ['customer_id'],
    'vista_log_auditoria': ['id']
}

def obtener_claves_primarias(nombre_tabla):
    return primary_keys.get(nombre_tabla, ['id'])

@routes.route('/')
def index():
    return render_template('index.html')

@routes.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contraseña = generate_password_hash(request.form['contraseña'])

        usuario_existente = Usuario.query.filter_by(correo=correo).first()
        if usuario_existente:
            flash("El correo ya está registrado", "danger")
            return redirect(url_for('routes.registro'))

        rol = 'admin' if nombre.lower() == 'admin' else 'auditor' if nombre.lower() == 'auditor' else 'usuario'
        nuevo_usuario = Usuario(nombre=nombre, correo=correo, contraseña=contraseña, rol=rol)

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash("Registro exitoso", "success")
            return redirect(url_for('routes.login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al registrar: {str(e)}", "danger")
            return redirect(url_for('routes.registro'))

    return render_template('registro.html')

@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        usuario = Usuario.query.filter_by(correo=correo).first()

        if usuario and check_password_hash(usuario.contraseña, contraseña):
            session['usuario_id'] = usuario.id
            session['usuario'] = usuario.nombre
            session['usuario_rol'] = usuario.rol
            return redirect(url_for('routes.index'))
        else:
            flash("Credenciales inválidas", "danger")
    return render_template('login.html')

@routes.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente.', 'info')
    return redirect(url_for('routes.index'))

@routes.route('/ver_tabla/<nombre_tabla>', methods=['GET'])
def ver_tabla(nombre_tabla):
    rol = session.get('usuario_rol')
    tablas_usuario = ['categories', 'customers', 'orders', 'payments', 'products', 'order_details']

    if rol == 'admin':
        solo_lectura = False
    elif rol == 'auditor':
        flash("Los auditores solo pueden ver vistas", "warning")
        return redirect(url_for('routes.index'))
    elif rol == 'usuario':
        if nombre_tabla not in tablas_usuario:
            flash("No tienes permiso para ver esta tabla", "danger")
            return redirect(url_for('routes.index'))
        solo_lectura = True
    else:
        flash("Rol no autorizado", "danger")
        return redirect(url_for('routes.index'))

    try:
        claves = obtener_claves_primarias(nombre_tabla)
        filtros = []
        valores = {}

        for clave, valor in request.args.items():
            if valor.strip():
                filtros.append(f"{clave}::TEXT ILIKE :{clave}")
                valores[clave] = f"%{valor}%"

        where_clause = " AND ".join(filtros)
        query = f"SELECT * FROM {nombre_tabla}"
        if where_clause:
            query += f" WHERE {where_clause}"

        result = db.session.execute(text(query), valores)
        columnas = result.keys()
        datos = result.fetchall()

        return render_template(
            'ver_tabla.html',
            nombre_tabla=nombre_tabla,
            columnas=columnas,
            datos=datos,
            claves=claves,
            solo_lectura=solo_lectura
        )

    except Exception as e:
        flash(f"Error al consultar la tabla: {e}", "danger")
        return redirect(url_for('routes.index'))

@routes.route('/crear/<nombre_tabla>', methods=['POST'])
def crear_registro(nombre_tabla):
    rol = session.get('usuario_rol')
    tablas_usuario = ['categories', 'customers', 'orders', 'payments', 'products', 'order_details']

    if rol not in ['admin', 'usuario'] or (rol == 'usuario' and nombre_tabla not in tablas_usuario):
        flash("No tienes permiso para crear registros en esta tabla", "danger")
        return redirect(url_for('routes.index'))

    datos = request.form.to_dict()
    claves_pk = obtener_claves_primarias(nombre_tabla)

    for clave in claves_pk:
        datos.pop(clave, None)

    if not datos:
        flash("No se proporcionaron datos válidos para insertar", "warning")
        return redirect(url_for('routes.ver_tabla', nombre_tabla=nombre_tabla))

    keys = ', '.join(datos.keys())
    values = ', '.join([f":{k}" for k in datos.keys()])

    try:
        query = text(f"INSERT INTO {nombre_tabla} ({keys}) VALUES ({values})")
        db.session.execute(query, datos)
        db.session.commit()
        flash("Registro creado con éxito", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear registro: {e}", "danger")

    return redirect(url_for('routes.ver_tabla', nombre_tabla=nombre_tabla))

@routes.route('/actualizar/<nombre_tabla>/<id>', methods=['POST'])
def actualizar_registro(nombre_tabla, id):
    if session.get('usuario_rol') != 'admin':
        flash("No tienes permiso para actualizar registros", "danger")
        return redirect(url_for('routes.index'))

    datos = request.form.to_dict()
    claves_columnas = obtener_claves_primarias(nombre_tabla)

    for clave in claves_columnas:
        datos.pop(clave, None)

    if not datos:
        flash("No se proporcionaron datos para actualizar", "warning")
        return redirect(url_for('routes.ver_tabla', nombre_tabla=nombre_tabla))

    set_clause = ', '.join([f"{k} = :{k}" for k in datos.keys()])
    claves = id.split(',')
    condicion = ' AND '.join([f"{col} = :{col}" for col in claves_columnas])
    for i, col in enumerate(claves_columnas):
        datos[col] = claves[i]

    try:
        query = text(f"UPDATE {nombre_tabla} SET {set_clause} WHERE {condicion}")
        db.session.execute(query, datos)
        db.session.commit()
        flash("Registro actualizado con éxito", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar: {e}", "danger")

    return redirect(url_for('routes.ver_tabla', nombre_tabla=nombre_tabla))

@routes.route('/eliminar/<nombre_tabla>/<id>', methods=['POST'])
def eliminar_registro(nombre_tabla, id):
    if session.get('usuario_rol') != 'admin':
        flash("No tienes permiso para eliminar registros", "danger")
        return redirect(url_for('routes.index'))

    claves = id.split(',')
    claves_columnas = obtener_claves_primarias(nombre_tabla)
    condicion = ' AND '.join([f"{col} = :{col}" for col in claves_columnas])
    datos = {col: claves[i] for i, col in enumerate(claves_columnas)}

    try:
        query = text(f"DELETE FROM {nombre_tabla} WHERE {condicion}")
        db.session.execute(query, datos)
        db.session.commit()
        flash("Registro eliminado con éxito", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar: {e}", "danger")

    return redirect(url_for('routes.ver_tabla', nombre_tabla=nombre_tabla))

@routes.route('/ver_vista/<nombre_vista>')
def ver_vista(nombre_vista):
    if session.get('usuario_rol') not in ['auditor', 'admin']:
        flash("No tienes permiso para ver esta vista", "danger")
        return redirect(url_for('routes.index'))

    try:
        filtros = []
        valores = {}

        for clave, valor in request.args.items():
            if valor.strip():
                filtros.append(f"{clave}::TEXT ILIKE :{clave}")
                valores[clave] = f"%{valor}%"

        where_clause = " AND ".join(filtros)
        query = f"SELECT * FROM {nombre_vista}"
        if where_clause:
            query += f" WHERE {where_clause}"

        result = db.session.execute(text(query), valores)
        columnas = result.keys()
        datos = result.fetchall()

        claves = obtener_claves_primarias(nombre_vista)

        return render_template(
            'ver_tabla.html',
            nombre_tabla=nombre_vista,
            columnas=columnas,
            datos=datos,
            claves=claves,
            solo_lectura=True
        )
    except Exception as e:
        flash(f"Error al consultar la vista: {e}", "danger")
        return redirect(url_for('routes.index'))

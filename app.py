from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import database

app = Flask(__name__, static_folder='static', template_folder='templates')

# Inicializar BD al arrancar
database.init_db()
database.seed_data()

# ----------------- RUTAS DE PÁGINA -----------------
@app.route('/')
def index():
    return render_template('index.html')

# ----------------- ENDPOINTS DASHBOARD -----------------
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    conn = database.get_db()
    cursor = conn.cursor()

    # Métricas generales
    cursor.execute("SELECT COUNT(*) FROM clientes")
    total_clientes = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(total), 0), COUNT(*) FROM ventas")
    ventas_total_row = cursor.fetchone()
    total_ingresos = float(ventas_total_row[0])
    total_pedidos = ventas_total_row[1]
    ticket_medio = round(total_ingresos / total_pedidos, 2) if total_pedidos > 0 else 0.0

    # Ventas de los últimos 30 días
    cursor.execute("""
        SELECT COALESCE(SUM(total), 0) FROM ventas
        WHERE fecha_venta >= datetime('now', '-30 day')
    """)
    ventas_mes = float(cursor.fetchone()[0])

    # Distribución por segmento RFM
    cursor.execute("""
        SELECT categoria_cliente, COUNT(*) as cantidad
        FROM clientes
        GROUP BY categoria_cliente
    """)
    segmentos = {row['categoria_cliente']: row['cantidad'] for row in cursor.fetchall()}

    # Alertas de stock bajo (< 3 pares)
    cursor.execute("""
        SELECT v.id_variante, p.nombre_modelo, p.marca, v.talla, v.color, v.stock_actual, v.sku
        FROM variantes_stock v
        JOIN productos p ON v.id_producto = p.id_producto
        WHERE v.stock_actual <= 2
        ORDER BY v.stock_actual ASC
        LIMIT 6
    """)
    stock_bajo = [dict(row) for row in cursor.fetchall()]

    # Últimas 5 ventas
    cursor.execute("""
        SELECT v.id_venta, v.fecha_venta, v.total, v.metodo_pago, c.nombre as cliente_nombre, c.categoria_cliente
        FROM ventas v
        JOIN clientes c ON v.id_cliente = c.id_cliente
        ORDER BY v.fecha_venta DESC
        LIMIT 5
    """)
    ultimas_ventas = [dict(row) for row in cursor.fetchall()]

    # Próximos cumpleaños (próximos 30 días o activos)
    cursor.execute("""
        SELECT id_cliente, nombre, fecha_nacimiento, telefono, email, categoria_cliente
        FROM clientes
        WHERE fecha_nacimiento IS NOT NULL
        ORDER BY strftime('%m-%d', fecha_nacimiento) ASC
        LIMIT 5
    """)
    cumpleanos = [dict(row) for row in cursor.fetchall()]

    # Últimas interacciones
    cursor.execute("""
        SELECT i.id_interaccion, i.tipo, i.comentarios, i.fecha, c.nombre as cliente_nombre, c.id_cliente
        FROM interacciones i
        JOIN clientes c ON i.id_cliente = c.id_cliente
        ORDER BY i.fecha DESC
        LIMIT 5
    """)
    ultimas_interacciones = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return jsonify({
        "total_clientes": total_clientes,
        "total_ingresos": total_ingresos,
        "total_pedidos": total_pedidos,
        "ticket_medio": ticket_medio,
        "ventas_mes": ventas_mes,
        "segmentos": segmentos,
        "stock_bajo": stock_bajo,
        "ultimas_ventas": ultimas_ventas,
        "cumpleanos": cumpleanos,
        "ultimas_interacciones": ultimas_interacciones
    })

# ----------------- ENDPOINTS CLIENTES -----------------
@app.route('/api/clientes', methods=['GET'])
def get_clientes():
    search = request.args.get('q', '').strip()
    categoria = request.args.get('categoria', '').strip()
    talla = request.args.get('talla', '').strip()
    marca = request.args.get('marca', '').strip()

    conn = database.get_db()
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT c.*
        FROM clientes c
        LEFT JOIN preferencias_cliente p ON c.id_cliente = p.id_cliente
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (c.nombre LIKE ? OR c.telefono LIKE ? OR c.email LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if categoria:
        query += " AND c.categoria_cliente = ?"
        params.append(categoria)

    if talla:
        query += " AND p.talla_habitual = ?"
        params.append(talla)

    if marca:
        query += " AND p.marca_favorita LIKE ?"
        params.append(f"%{marca}%")

    query += " ORDER BY c.score_total DESC, c.nombre ASC"

    cursor.execute(query, params)
    clientes_raw = cursor.fetchall()

    clientes_list = []
    for c in clientes_raw:
        c_dict = dict(c)
        # Buscar preferencias asociadas
        cursor.execute("SELECT * FROM preferencias_cliente WHERE id_cliente = ?", (c['id_cliente'],))
        c_dict['preferencias'] = [dict(p) for p in cursor.fetchall()]
        clientes_list.append(c_dict)

    conn.close()
    return jsonify(clientes_list)

@app.route('/api/clientes/<int:id_cliente>', methods=['GET'])
def get_cliente_detalle(id_cliente):
    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clientes WHERE id_cliente = ?", (id_cliente,))
    cliente = cursor.fetchone()
    if not cliente:
        conn.close()
        return jsonify({"error": "Cliente no encontrado"}), 404

    cliente_dict = dict(cliente)

    # Preferencias
    cursor.execute("SELECT * FROM preferencias_cliente WHERE id_cliente = ?", (id_cliente,))
    cliente_dict['preferencias'] = [dict(p) for p in cursor.fetchall()]

    # Historial de compras
    cursor.execute("""
        SELECT v.*, COUNT(dv.id_detalle) as total_articulos
        FROM ventas v
        LEFT JOIN detalles_venta dv ON v.id_venta = dv.id_venta
        WHERE v.id_cliente = ?
        GROUP BY v.id_venta
        ORDER BY v.fecha_venta DESC
    """, (id_cliente,))
    ventas = []
    for v in cursor.fetchall():
        v_dict = dict(v)
        cursor.execute("""
            SELECT dv.*, vs.talla, vs.color, p.nombre_modelo, p.marca
            FROM detalles_venta dv
            JOIN variantes_stock vs ON dv.id_variante = vs.id_variante
            JOIN productos p ON vs.id_producto = p.id_producto
            WHERE dv.id_venta = ?
        """, (v['id_venta'],))
        v_dict['detalles'] = [dict(d) for d in cursor.fetchall()]
        ventas.append(v_dict)
    cliente_dict['ventas'] = ventas

    # Historial de interacciones
    cursor.execute("""
        SELECT * FROM interacciones
        WHERE id_cliente = ?
        ORDER BY fecha DESC
    """, (id_cliente,))
    cliente_dict['interacciones'] = [dict(i) for i in cursor.fetchall()]

    # Estrategia comercial según el documento
    estrategias = {
        'VIP / Cliente TOP': {
            'estrategia': 'Venta privada anticipada, eventos exclusivos y atención prioritaria.',
            'accion_sugerida': 'Invitar a preventa exclusiva de nueva colección o reservar modelo preferido sin coste.',
            'plantilla_whatsapp': f"¡Hola {cliente_dict['nombre'].split()[0]}! 🌟 Como cliente VIP en nuestra zapatería, queremos invitarte en primicia antes que a nadie a ver la nueva colección con una copa de bienvenida."
        },
        'Cliente Frecuente': {
            'estrategia': 'Avisos automatizados al recibir stock nuevo de su marca y talla preferida.',
            'accion_sugerida': 'Notificar llegada de calzado nuevo afín a sus tallas y marcas favoritas.',
            'plantilla_whatsapp': f"Hola {cliente_dict['nombre'].split()[0]}, ¡acaban de llegar nuevos modelos en tu talla habitual a nuestra zapatería! Pásate a probártelos cuando quieras."
        },
        'Cliente Dormido': {
            'estrategia': 'Notificaciones al inicio de temporada (primavera/otoño) con incentivo suave.',
            'accion_sugerida': 'Enviar recordatorio de cambio de estación con un 10% de cortesía en calzado de temporada.',
            'plantilla_whatsapp': f"¡Hola {cliente_dict['nombre'].split()[0]}! 👞 Te echamos de menos. Ha llegado el cambio de temporada a la zapatería y tenemos un detalle especial reservado para ti."
        },
        'En Riesgo / Ocasional': {
            'estrategia': 'Cupón directo de descuento para fomentar el retorno a la tienda.',
            'accion_sugerida': 'Cupón directo 15% de reactivación válido durante los próximos 10 días.',
            'plantilla_whatsapp': f"Hola {cliente_dict['nombre'].split()[0]}, tenemos un cupón exclusivo de 15% de descuento en tu próximo par de calzado. ¡Ven a renovar tus zapatos favoritos!"
        }
    }
    cliente_dict['estrategia_comercial'] = estrategias.get(cliente_dict['categoria_cliente'], estrategias['En Riesgo / Ocasional'])

    conn.close()
    return jsonify(cliente_dict)

@app.route('/api/clientes', methods=['POST'])
def create_cliente():
    data = request.json or {}
    nombre = data.get('nombre', '').strip()
    telefono = data.get('telefono', '').strip()
    email = data.get('email', '').strip()
    fecha_nacimiento = data.get('fecha_nacimiento', None)
    observaciones = data.get('observaciones', '').strip()
    preferencias = data.get('preferencias', [])

    if not nombre:
        return jsonify({"error": "El nombre del cliente es obligatorio"}), 400

    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO clientes (nombre, telefono, email, fecha_nacimiento, observaciones)
        VALUES (?, ?, ?, ?, ?)
    """, (nombre, telefono, email, fecha_nacimiento, observaciones))
    id_cliente = cursor.lastrowid

    for pref in preferencias:
        cursor.execute("""
            INSERT INTO preferencias_cliente (id_cliente, categoria_calzado, talla_habitual, marca_favorita)
            VALUES (?, ?, ?, ?)
        """, (id_cliente, pref.get('categoria_calzado'), pref.get('talla_habitual'), pref.get('marca_favorita')))

    conn.commit()

    # Recalcular score inicial
    database.calcular_scoring_cliente(conn, id_cliente)
    conn.close()

    return jsonify({"message": "Cliente creado exitosamente", "id_cliente": id_cliente}), 201

@app.route('/api/clientes/<int:id_cliente>', methods=['PUT'])
def update_cliente(id_cliente):
    data = request.json or {}
    nombre = data.get('nombre', '').strip()
    telefono = data.get('telefono', '').strip()
    email = data.get('email', '').strip()
    fecha_nacimiento = data.get('fecha_nacimiento', None)
    observaciones = data.get('observaciones', '').strip()

    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE clientes
        SET nombre = ?, telefono = ?, email = ?, fecha_nacimiento = ?, observaciones = ?
        WHERE id_cliente = ?
    """, (nombre, telefono, email, fecha_nacimiento, observaciones, id_cliente))
    conn.commit()
    conn.close()

    return jsonify({"message": "Cliente actualizado con éxito"})

@app.route('/api/clientes/<int:id_cliente>', methods=['DELETE'])
def delete_cliente(id_cliente):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clientes WHERE id_cliente = ?", (id_cliente,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Cliente eliminado con éxito"})

# Preferencias individuales
@app.route('/api/clientes/<int:id_cliente>/preferencias', methods=['POST'])
def add_preferencia(id_cliente):
    data = request.json or {}
    categoria_calzado = data.get('categoria_calzado', '').strip()
    talla_habitual = data.get('talla_habitual', '').strip()
    marca_favorita = data.get('marca_favorita', '').strip()

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO preferencias_cliente (id_cliente, categoria_calzado, talla_habitual, marca_favorita)
        VALUES (?, ?, ?, ?)
    """, (id_cliente, categoria_calzado, talla_habitual, marca_favorita))
    id_pref = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"message": "Preferencia guardada", "id_preferencia": id_pref}), 201

@app.route('/api/preferencias/<int:id_preferencia>', methods=['DELETE'])
def delete_preferencia(id_preferencia):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM preferencias_cliente WHERE id_preferencia = ?", (id_preferencia,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Preferencia eliminada"})

# Recalcular score individual o masivo
@app.route('/api/clientes/<int:id_cliente>/recalcular-score', methods=['POST'])
def recalcular_cliente_api(id_cliente):
    conn = database.get_db()
    resultado = database.calcular_scoring_cliente(conn, id_cliente)
    conn.close()
    return jsonify(resultado)

@app.route('/api/clientes/recalcular-todos', methods=['POST'])
def recalcular_todos_api():
    conn = database.get_db()
    resultados = database.recalcular_todos(conn)
    conn.close()
    return jsonify({"message": f"Se ha recalculado el scoring de {len(resultados)} clientes", "resultados": resultados})

# ----------------- ENDPOINTS PRODUCTOS & VARIANTES -----------------
@app.route('/api/productos', methods=['GET'])
def get_productos():
    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*,
               COUNT(v.id_variante) as total_variantes,
               COALESCE(SUM(v.stock_actual), 0) as stock_total
        FROM productos p
        LEFT JOIN variantes_stock v ON p.id_producto = v.id_producto
        GROUP BY p.id_producto
        ORDER BY p.nombre_modelo ASC
    """)
    productos = []
    for p in cursor.fetchall():
        p_dict = dict(p)
        cursor.execute("SELECT * FROM variantes_stock WHERE id_producto = ? ORDER BY talla ASC, color ASC", (p['id_producto'],))
        p_dict['variantes'] = [dict(v) for v in cursor.fetchall()]
        productos.append(p_dict)

    conn.close()
    return jsonify(productos)

@app.route('/api/productos', methods=['POST'])
def create_producto():
    data = request.json or {}
    nombre = data.get('nombre_modelo', '').strip()
    marca = data.get('marca', '').strip()
    categoria = data.get('categoria', 'Unisex').strip()
    precio = float(data.get('precio_base', 0.0))
    variantes = data.get('variantes', [])

    if not nombre or not marca or precio <= 0:
        return jsonify({"error": "Nombre, marca y precio válido son obligatorios"}), 400

    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO productos (nombre_modelo, marca, categoria, precio_base)
        VALUES (?, ?, ?, ?)
    """, (nombre, marca, categoria, precio))
    id_producto = cursor.lastrowid

    for v in variantes:
        talla = str(v.get('talla', '')).strip()
        color = v.get('color', 'Estándar').strip()
        stock = int(v.get('stock_actual', 0))
        sku = v.get('sku') or f"ZAP-{id_producto}-{talla}-{color[:3].upper()}-{datetime.now().strftime('%f')[:4]}"
        cursor.execute("""
            INSERT INTO variantes_stock (id_producto, talla, color, stock_actual, sku)
            VALUES (?, ?, ?, ?, ?)
        """, (id_producto, talla, color, stock, sku))

    conn.commit()
    conn.close()
    return jsonify({"message": "Producto creado con éxito", "id_producto": id_producto}), 201

@app.route('/api/productos/<int:id_producto>', methods=['PUT'])
def update_producto(id_producto):
    data = request.json or {}
    nombre = data.get('nombre_modelo', '').strip()
    marca = data.get('marca', '').strip()
    categoria = data.get('categoria', 'Unisex').strip()
    precio = float(data.get('precio_base', 0.0))

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE productos
        SET nombre_modelo = ?, marca = ?, categoria = ?, precio_base = ?
        WHERE id_producto = ?
    """, (nombre, marca, categoria, precio, id_producto))
    conn.commit()
    conn.close()
    return jsonify({"message": "Producto actualizado"})

@app.route('/api/productos/<int:id_producto>', methods=['DELETE'])
def delete_producto(id_producto):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id_producto = ?", (id_producto,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Producto eliminado"})

@app.route('/api/variantes', methods=['GET'])
def get_variantes():
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.*, p.nombre_modelo, p.marca, p.categoria, p.precio_base
        FROM variantes_stock v
        JOIN productos p ON v.id_producto = p.id_producto
        ORDER BY p.nombre_modelo ASC, v.talla ASC
    """)
    variantes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(variantes)

@app.route('/api/variantes', methods=['POST'])
def add_variante():
    data = request.json or {}
    id_producto = data.get('id_producto')
    talla = str(data.get('talla', '')).strip()
    color = data.get('color', '').strip()
    stock = int(data.get('stock_actual', 0))
    sku = data.get('sku') or f"ZAP-{id_producto}-{talla}-{color[:3].upper()}-{datetime.now().strftime('%f')[:4]}"

    if not id_producto or not talla or not color:
        return jsonify({"error": "Faltan campos obligatorios para la variante"}), 400

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO variantes_stock (id_producto, talla, color, stock_actual, sku)
        VALUES (?, ?, ?, ?, ?)
    """, (id_producto, talla, color, stock, sku))
    id_var = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"message": "Variante agregada", "id_variante": id_var}), 201

@app.route('/api/variantes/<int:id_variante>/stock', methods=['PUT'])
def update_stock_variante(id_variante):
    data = request.json or {}
    nuevo_stock = int(data.get('stock_actual', 0))

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE variantes_stock SET stock_actual = ? WHERE id_variante = ?", (nuevo_stock, id_variante))
    conn.commit()
    conn.close()
    return jsonify({"message": "Stock actualizado"})

# ----------------- ENDPOINTS VENTAS / TPV -----------------
@app.route('/api/ventas', methods=['GET'])
def get_ventas():
    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT v.*, c.nombre as cliente_nombre, c.telefono, c.categoria_cliente
        FROM ventas v
        JOIN clientes c ON v.id_cliente = c.id_cliente
        ORDER BY v.fecha_venta DESC
    """)
    ventas = []
    for v in cursor.fetchall():
        v_dict = dict(v)
        cursor.execute("""
            SELECT dv.*, vs.talla, vs.color, p.nombre_modelo, p.marca
            FROM detalles_venta dv
            JOIN variantes_stock vs ON dv.id_variante = vs.id_variante
            JOIN productos p ON vs.id_producto = p.id_producto
            WHERE dv.id_venta = ?
        """, (v['id_venta'],))
        v_dict['items'] = [dict(d) for d in cursor.fetchall()]
        ventas.append(v_dict)

    conn.close()
    return jsonify(ventas)

@app.route('/api/ventas', methods=['POST'])
def create_venta():
    data = request.json or {}
    id_cliente = data.get('id_cliente')
    metodo_pago = data.get('metodo_pago', 'Tarjeta')
    items = data.get('items', []) # lista de {id_variante, cantidad, precio_unitario}

    if not id_cliente or not items:
        return jsonify({"error": "Cliente e ítems requeridos para la venta"}), 400

    conn = database.get_db()
    cursor = conn.cursor()

    # Validar stock disponible
    total_venta = 0.0
    for item in items:
        cursor.execute("SELECT stock_actual, p.precio_base FROM variantes_stock v JOIN productos p ON v.id_producto = p.id_producto WHERE v.id_variante = ?", (item['id_variante'],))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": f"Variante ID {item['id_variante']} no existe"}), 400
        if row['stock_actual'] < item['cantidad']:
            conn.close()
            return jsonify({"error": f"Stock insuficiente para la variante seleccionada (Disponibles: {row['stock_actual']})"}), 400

        pu = float(item.get('precio_unitario', row['precio_base']))
        total_venta += pu * item['cantidad']

    total_venta = round(total_venta, 2)
    ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insertar Venta
    cursor.execute("""
        INSERT INTO ventas (id_cliente, fecha_venta, total, metodo_pago)
        VALUES (?, ?, ?, ?)
    """, (id_cliente, ahora_str, total_venta, metodo_pago))
    id_venta = cursor.lastrowid

    # Insertar Detalles y descontar stock
    for item in items:
        pu = float(item.get('precio_unitario', 0.0))
        cursor.execute("""
            INSERT INTO detalles_venta (id_venta, id_variante, cantidad, precio_unitario)
            VALUES (?, ?, ?, ?)
        """, (id_venta, item['id_variante'], item['cantidad'], pu))

        cursor.execute("""
            UPDATE variantes_stock
            SET stock_actual = stock_actual - ?
            WHERE id_variante = ?
        """, (item['cantidad'], item['id_variante']))

    conn.commit()

    # Recalcular automáticamente el scoring del cliente
    score_actualizado = database.calcular_scoring_cliente(conn, id_cliente)
    conn.close()

    return jsonify({
        "message": "Venta registrada con éxito",
        "id_venta": id_venta,
        "total": total_venta,
        "nuevo_score": score_actualizado
    }), 201

# ----------------- ENDPOINTS INTERACCIONES -----------------
@app.route('/api/interacciones', methods=['GET'])
def get_interacciones():
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.*, c.nombre as cliente_nombre, c.telefono, c.categoria_cliente
        FROM interacciones i
        JOIN clientes c ON i.id_cliente = c.id_cliente
        ORDER BY i.fecha DESC
    """)
    interacciones = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(interacciones)

@app.route('/api/interacciones', methods=['POST'])
def create_interaccion():
    data = request.json or {}
    id_cliente = data.get('id_cliente')
    tipo = data.get('tipo', 'WhatsApp Comercial')
    comentarios = data.get('comentarios', '').strip()
    fecha = data.get('fecha') or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not id_cliente:
        return jsonify({"error": "id_cliente es obligatorio"}), 400

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interacciones (id_cliente, tipo, comentarios, fecha)
        VALUES (?, ?, ?, ?)
    """, (id_cliente, tipo, comentarios, fecha))
    id_interaccion = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"message": "Interacción registrada", "id_interaccion": id_interaccion}), 201

# ----------------- RECOMENDADOR INTELIGENTE (MATCHING CALZADO) -----------------
@app.route('/api/matching/calzado', methods=['GET'])
def matching_calzado():
    talla = request.args.get('talla', '').strip()
    marca = request.args.get('marca', '').strip()
    categoria = request.args.get('categoria', '').strip()

    conn = database.get_db()
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT c.id_cliente, c.nombre, c.telefono, c.email, c.categoria_cliente, c.score_total,
                        p.talla_habitual, p.marca_favorita, p.categoria_calzado
        FROM clientes c
        JOIN preferencias_cliente p ON c.id_cliente = p.id_cliente
        WHERE 1=1
    """
    params = []
    if talla:
        query += " AND p.talla_habitual = ?"
        params.append(talla)
    if marca:
        query += " AND (p.marca_favorita LIKE ? OR ? LIKE '%' || p.marca_favorita || '%')"
        params.extend([f"%{marca}%", marca])
    if categoria:
        query += " AND (p.categoria_calzado LIKE ?)"
        params.append(f"%{categoria}%")

    query += " ORDER BY c.score_total DESC, c.nombre ASC"

    cursor.execute(query, params)
    matches = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(matches)

# ----------------- REGLAS DE SCORING -----------------
@app.route('/api/scoring/reglas', methods=['GET'])
def get_reglas_scoring():
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reglas_scoring ORDER BY criterio ASC, puntos_asignados DESC")
    reglas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(reglas)

@app.route('/api/scoring/reglas/<int:id_regla>', methods=['PUT'])
def update_regla_scoring(id_regla):
    data = request.json or {}
    rango_min = float(data.get('rango_min', 0))
    rango_max = float(data.get('rango_max', 0))
    puntos = int(data.get('puntos_asignados', 1))
    descripcion = data.get('descripcion', '')

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE reglas_scoring
        SET rango_min = ?, rango_max = ?, puntos_asignados = ?, descripcion = ?
        WHERE id_regla = ?
    """, (rango_min, rango_max, puntos, descripcion, id_regla))
    conn.commit()
    conn.close()
    return jsonify({"message": "Regla actualizada con éxito"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)

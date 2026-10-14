import sqlite3
import os
import tempfile
from datetime import datetime, timedelta
import random

# En Vercel (serverless) el directorio del proyecto es de solo lectura,
# solo /tmp es escribible. Usamos una ruta configurable para poder desplegar.
_default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crm_zapateria.db")
if os.environ.get("VERCEL"):
    _default_db = os.path.join(tempfile.gettempdir(), "crm_zapateria.db")
DB_FILE = os.environ.get("CRM_DB_FILE", _default_db)

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Tabla clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre VARCHAR(100) NOT NULL,
        telefono VARCHAR(20),
        email VARCHAR(100),
        fecha_nacimiento DATE,
        observaciones TEXT,
        puntos_recencia INTEGER DEFAULT 1,
        puntos_frecuencia INTEGER DEFAULT 1,
        puntos_monto INTEGER DEFAULT 1,
        score_total INTEGER DEFAULT 3,
        categoria_cliente VARCHAR(30) DEFAULT 'En Riesgo / Ocasional',
        ultima_actualizacion_score DATE,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabla preferencias_cliente
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS preferencias_cliente (
        id_preferencia INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente INTEGER NOT NULL,
        categoria_calzado VARCHAR(50),
        talla_habitual VARCHAR(10),
        marca_favorita VARCHAR(50),
        FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE
    )
    """)

    # Tabla productos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_modelo VARCHAR(100) NOT NULL,
        marca VARCHAR(50) NOT NULL,
        categoria VARCHAR(50) NOT NULL,
        precio_base DECIMAL(8,2) NOT NULL
    )
    """)

    # Tabla variantes_stock
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS variantes_stock (
        id_variante INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto INTEGER NOT NULL,
        talla VARCHAR(10) NOT NULL,
        color VARCHAR(30) NOT NULL,
        stock_actual INTEGER NOT NULL DEFAULT 0,
        sku VARCHAR(50) UNIQUE,
        FOREIGN KEY (id_producto) REFERENCES productos(id_producto) ON DELETE CASCADE
    )
    """)

    # Tabla ventas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente INTEGER NOT NULL,
        fecha_venta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total DECIMAL(8,2) NOT NULL,
        metodo_pago VARCHAR(30) NOT NULL,
        FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
    )
    """)

    # Tabla detalles_venta
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detalles_venta (
        id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
        id_venta INTEGER NOT NULL,
        id_variante INTEGER NOT NULL,
        cantidad INTEGER NOT NULL DEFAULT 1,
        precio_unitario DECIMAL(8,2) NOT NULL,
        FOREIGN KEY (id_venta) REFERENCES ventas(id_venta) ON DELETE CASCADE,
        FOREIGN KEY (id_variante) REFERENCES variantes_stock(id_variante)
    )
    """)

    # Tabla interacciones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interacciones (
        id_interaccion INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente INTEGER NOT NULL,
        tipo VARCHAR(50) NOT NULL,
        comentarios TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE
    )
    """)

    # Tabla reglas_scoring
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reglas_scoring (
        id_regla INTEGER PRIMARY KEY AUTOINCREMENT,
        criterio VARCHAR(50) NOT NULL,
        rango_min DECIMAL(10,2),
        rango_max DECIMAL(10,2),
        puntos_asignados INTEGER NOT NULL,
        descripcion VARCHAR(100)
    )
    """)

    conn.commit()
    conn.close()

def seed_reglas_scoring(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reglas_scoring")
    count = cursor.fetchone()[0]
    if count == 0:
        reglas = [
            # RECENCIA (Días desde última compra)
            ('RECENCIA', 0, 90, 5, 'Últimos 90 días (Cliente Activo)'),
            ('RECENCIA', 91, 180, 4, 'De 91 a 180 días'),
            ('RECENCIA', 181, 365, 3, 'De 181 a 365 días (Cambio de temporada)'),
            ('RECENCIA', 366, 999999, 1, 'Más de 365 días (Cliente en Riesgo)'),

            # FRECUENCIA (Compras en último año)
            ('FRECUENCIA', 6, 999999, 5, 'Más de 6 compras'),
            ('FRECUENCIA', 3, 5, 4, 'De 3 a 5 compras'),
            ('FRECUENCIA', 2, 2, 2, '2 compras'),
            ('FRECUENCIA', 1, 1, 1, '1 compra'),
            ('FRECUENCIA', 0, 0, 1, '0 compras'),

            # MONTO (Gasto acumulado total)
            ('MONTO', 400.0, 999999.0, 5, 'Más de 400 €'),
            ('MONTO', 200.0, 399.99, 4, 'De 200 € a 399 €'),
            ('MONTO', 100.0, 199.99, 2, 'De 100 € a 199 €'),
            ('MONTO', 0.0, 99.99, 1, 'Menos de 100 €')
        ]
        cursor.executemany("""
            INSERT INTO reglas_scoring (criterio, rango_min, rango_max, puntos_asignados, descripcion)
            VALUES (?, ?, ?, ?, ?)
        """, reglas)
        conn.commit()

def calcular_scoring_cliente(conn, id_cliente):
    cursor = conn.cursor()
    today = datetime.now()

    # 1. Obtener métricas de compras del cliente
    cursor.execute("""
        SELECT COUNT(id_venta) as total_compras,
               COALESCE(SUM(total), 0) as gasto_total,
               MAX(fecha_venta) as ultima_fecha
        FROM ventas
        WHERE id_cliente = ?
    """, (id_cliente,))
    row = cursor.fetchone()

    total_compras = row['total_compras'] or 0
    gasto_total = float(row['gasto_total'] or 0.0)
    ultima_fecha = row['ultima_fecha']

    if ultima_fecha:
        try:
            if 'T' in ultima_fecha:
                dt_venta = datetime.fromisoformat(ultima_fecha.replace('Z', ''))
            elif len(ultima_fecha) == 10:
                dt_venta = datetime.strptime(ultima_fecha, "%Y-%m-%d")
            else:
                dt_venta = datetime.strptime(ultima_fecha, "%Y-%m-%d %H:%M:%S")
            dias_recencia = (today - dt_venta).days
            if dias_recencia < 0:
                dias_recencia = 0
        except Exception:
            dias_recencia = 999
    else:
        dias_recencia = 999

    # Cargar reglas activas
    cursor.execute("SELECT * FROM reglas_scoring ORDER BY puntos_asignados DESC")
    todas_reglas = cursor.fetchall()

    reglas_recencia = [r for r in todas_reglas if r['criterio'] == 'RECENCIA']
    reglas_frecuencia = [r for r in todas_reglas if r['criterio'] == 'FRECUENCIA']
    reglas_monto = [r for r in todas_reglas if r['criterio'] == 'MONTO']

    # Evaluar Recencia
    puntos_recencia = 1
    for r in reglas_recencia:
        if r['rango_min'] <= dias_recencia <= r['rango_max']:
            puntos_recencia = r['puntos_asignados']
            break

    # Evaluar Frecuencia
    puntos_frecuencia = 1
    for r in reglas_frecuencia:
        if r['rango_min'] <= total_compras <= r['rango_max']:
            puntos_frecuencia = r['puntos_asignados']
            break

    # Evaluar Monto
    puntos_monto = 1
    for r in reglas_monto:
        if r['rango_min'] <= gasto_total <= r['rango_max']:
            puntos_monto = r['puntos_asignados']
            break

    score_total = puntos_recencia + puntos_frecuencia + puntos_monto

    # Categoría según baremo del documento
    # 13 a 15 pts: VIP / Cliente TOP
    # 10 a 12 pts: Cliente Frecuente
    # 7 a 9 pts: Cliente Dormido
    # 3 a 6 pts: En Riesgo / Ocasional
    if score_total >= 13:
        categoria = 'VIP / Cliente TOP'
    elif score_total >= 10:
        categoria = 'Cliente Frecuente'
    elif score_total >= 7:
        categoria = 'Cliente Dormido'
    else:
        categoria = 'En Riesgo / Ocasional'

    hoy_str = today.strftime("%Y-%m-%d")

    cursor.execute("""
        UPDATE clientes
        SET puntos_recencia = ?,
            puntos_frecuencia = ?,
            puntos_monto = ?,
            score_total = ?,
            categoria_cliente = ?,
            ultima_actualizacion_score = ?
        WHERE id_cliente = ?
    """, (puntos_recencia, puntos_frecuencia, puntos_monto, score_total, categoria, hoy_str, id_cliente))
    conn.commit()

    return {
        "id_cliente": id_cliente,
        "dias_recencia": dias_recencia,
        "total_compras": total_compras,
        "gasto_total": gasto_total,
        "puntos_recencia": puntos_recencia,
        "puntos_frecuencia": puntos_frecuencia,
        "puntos_monto": puntos_monto,
        "score_total": score_total,
        "categoria_cliente": categoria,
        "ultima_actualizacion_score": hoy_str
    }

def recalcular_todos(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id_cliente FROM clientes")
    clientes = cursor.fetchall()
    resultados = []
    for c in clientes:
        res = calcular_scoring_cliente(conn, c['id_cliente'])
        resultados.append(res)
    return resultados

def seed_data():
    conn = get_db()
    cursor = conn.cursor()

    seed_reglas_scoring(conn)

    # Si ya hay clientes, omitimos seed para no duplicar
    cursor.execute("SELECT COUNT(*) FROM clientes")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # 1. Catálogo de Productos de Calzado
    productos_data = [
        ("Mocasín Cuero Artesanal Fuencarral", "Pikolinos", "Hombre", 119.95),
        ("Botín Desert Boot Ante Clásico", "Clarks", "Hombre", 139.90),
        ("Zapatilla Deportiva Air Zoom Pegasus", "Nike", "Unisex", 129.99),
        ("Sneaker Beetle Anatómica Cuero", "Camper", "Unisex", 145.00),
        ("Zapato Confort Transpirable Nebula", "Geox", "Mujer", 110.00),
        ("Zapato Tacón Elegance Salón", "Lodi", "Mujer", 125.50),
        ("Bota Montaña Cuero Impermeable", "Panama Jack", "Hombre", 179.00),
        ("Sandalia Bio Confort Piel", "Birkenstock", "Mujer", 85.00),
        ("Zapatilla Deportiva Infantil velcro", "Puma", "Infantil", 45.00),
        ("Blucher Piel Formal Oxford", "Martinelli", "Hombre", 135.00)
    ]

    prod_ids = []
    for p in productos_data:
        cursor.execute("""
            INSERT INTO productos (nombre_modelo, marca, categoria, precio_base)
            VALUES (?, ?, ?, ?)
        """, p)
        prod_ids.append(cursor.lastrowid)

    # 2. Variantes de Stock por Tallas y Colores
    # Para cada producto, generamos tallas habituales y stock
    tallas_hombre = ["40", "41", "42", "43", "44", "45"]
    tallas_mujer = ["36", "37", "38", "39", "40", "41"]
    tallas_infantil = ["28", "30", "32", "34"]
    colores = ["Negro", "Marrón", "Cuero Natural", "Azul Marino", "Blanco", "Burdeos"]

    variante_ids = []
    sku_counter = 1000

    for i, pid in enumerate(prod_ids):
        p_cat = productos_data[i][2]
        if p_cat == "Hombre":
            tallas = tallas_hombre
        elif p_cat == "Mujer":
            tallas = tallas_mujer
        elif p_cat == "Infantil":
            tallas = tallas_infantil
        else:
            tallas = ["38", "39", "40", "41", "42", "43"]

        # 2 colores por producto
        selected_colores = [colores[i % len(colores)], colores[(i + 2) % len(colores)]]
        for col in selected_colores:
            for t in tallas:
                sku_counter += 1
                sku = f"ZAP-{pid}-{t}-{col[:3].upper()}-{sku_counter}"
                stock = random.choice([0, 1, 2, 4, 6, 8, 12]) # Algunos en 0 o 1 para alertas
                cursor.execute("""
                    INSERT INTO variantes_stock (id_producto, talla, color, stock_actual, sku)
                    VALUES (?, ?, ?, ?, ?)
                """, (pid, t, col, stock, sku))
                variante_ids.append((cursor.lastrowid, pid, productos_data[i][3]))

    # 3. Clientes Realistas
    clientes_data = [
        ("Elena Gómez Montero", "612345678", "elena.gomez@email.com", "1988-04-12", "Horma ancha en pie derecho. Prefiere piel suave y tacón bajo/medio."),
        ("Carlos Navarro Gil", "623456789", "carlos.navarro@email.com", "1979-11-25", "Empeine pronunciado. Cliente muy fiel a Clarks y Pikolinos."),
        ("Lucía Martín Velasco", "634567890", "lucia.martin@email.com", "1994-07-03", "Busca siempre novedades en sneakers y sandalias bio."),
        ("David Serrano Ramos", "645678901", "david.serrano@email.com", "1985-02-18", "Comprador habitual para él y sus hijos pequeños."),
        ("Carmen Ruiz Alarcón", "656789012", "carmen.ruiz@email.com", "1968-09-30", "Exige máxima comodidad y plantillas extraíbles."),
        ("Javier Morales Ortiz", "667890123", "javier.morales@email.com", "1991-12-14", "Deportista aficionado. Fanático de calzado running."),
        ("Marta Delgado Pons", "678901234", "marta.delgado@email.com", "2000-05-22", "Le gusta recibir avisos por WhatsApp de eventos especiales y fiestas."),
        ("Antonio Prieto Soto", "689012345", "antonio.prieto@email.com", "1975-08-09", "Compra un par cada cambio de estación sin falta.")
    ]

    cliente_ids = []
    now = datetime.now()
    for c in clientes_data:
        dias_alta = random.randint(180, 500)
        fecha_alta = (now - timedelta(days=dias_alta)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO clientes (nombre, telefono, email, fecha_nacimiento, observaciones, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (*c, fecha_alta))
        cliente_ids.append(cursor.lastrowid)

    # 4. Preferencias de Cliente
    # (id_cliente, categoria_calzado, talla_habitual, marca_favorita)
    preferencias_data = [
        (cliente_ids[0], "Casual", "38", "Pikolinos"),
        (cliente_ids[0], "Fiesta", "38", "Lodi"),
        (cliente_ids[1], "Casual", "43", "Clarks"),
        (cliente_ids[1], "Formal", "43", "Martinelli"),
        (cliente_ids[2], "Deportivo", "37", "Nike"),
        (cliente_ids[2], "Casual", "37", "Birkenstock"),
        (cliente_ids[3], "Deportivo", "42", "Nike"),
        (cliente_ids[3], "Infantil", "30", "Puma"),
        (cliente_ids[4], "Confort", "39", "Geox"),
        (cliente_ids[4], "Botas", "39", "Panama Jack"),
        (cliente_ids[5], "Deportivo", "44", "Nike"),
        (cliente_ids[5], "Casual", "44", "Camper"),
        (cliente_ids[6], "Fiesta", "36", "Lodi"),
        (cliente_ids[7], "Casual", "42", "Pikolinos")
    ]
    cursor.executemany("""
        INSERT INTO preferencias_cliente (id_cliente, categoria_calzado, talla_habitual, marca_favorita)
        VALUES (?, ?, ?, ?)
    """, preferencias_data)

    # 5. Ventas Simuladas con Diferentes Días para Generar Diversidad de Scoring RFM
    # Cliente 0 (Elena): VIP (compras recientes, alta frecuencia y monto alto)
    # Cliente 1 (Carlos): VIP (compras recientes, monto alto)
    # Cliente 2 (Lucía): Frecuente (reciente, 3 compras, monto medio)
    # Cliente 3 (David): Frecuente
    # Cliente 4 (Carmen): Dormido (última compra hace ~220 días, cambio temporada)
    # Cliente 5 (Javier): Dormido (última compra hace ~190 días)
    # Cliente 6 (Marta): En Riesgo (1 compra hace 380 días, monto bajo)
    # Cliente 7 (Antonio): En Riesgo (1 compra hace 400 días)

    historial_ventas = [
        # Elena (VIP)
        (cliente_ids[0], 15, ["Tarjeta", "Bizum", "Tarjeta"], 7),
        # Carlos (VIP)
        (cliente_ids[1], 25, ["Tarjeta", "Efectivo"], 5),
        # Lucía (Frecuente)
        (cliente_ids[2], 30, ["Bizum", "Tarjeta"], 4),
        # David (Frecuente)
        (cliente_ids[3], 45, ["Tarjeta"], 3),
        # Carmen (Dormido - > 180 días)
        (cliente_ids[4], 210, ["Tarjeta"], 2),
        # Javier (Dormido - > 190 días)
        (cliente_ids[5], 230, ["Bizum"], 2),
        # Marta (En Riesgo - > 370 días)
        (cliente_ids[6], 390, ["Efectivo"], 1),
        # Antonio (En Riesgo - > 410 días)
        (cliente_ids[7], 410, ["Efectivo"], 1)
    ]

    for cid, dias_min, metodos, num_ventas in historial_ventas:
        # Generamos las ventas distribuidas en el tiempo
        for v_idx in range(num_ventas):
            dias_atras = dias_min + (v_idx * 40)
            fecha_v = (now - timedelta(days=dias_atras)).strftime("%Y-%m-%d %H:%M:%S")
            metodo = random.choice(metodos)

            # Tomar 1 o 2 variantes al azar
            vars_compradas = random.sample(variante_ids, k=random.randint(1, 2))
            total_v = sum(v[2] for v in vars_compradas)

            cursor.execute("""
                INSERT INTO ventas (id_cliente, fecha_venta, total, metodo_pago)
                VALUES (?, ?, ?, ?)
            """, (cid, fecha_v, round(total_v, 2), metodo))
            vid = cursor.lastrowid

            for v in vars_compradas:
                cursor.execute("""
                    INSERT INTO detalles_venta (id_venta, id_variante, cantidad, precio_unitario)
                    VALUES (?, ?, ?, ?)
                """, (vid, v[0], 1, v[2]))

    # 6. Interacciones iniciales
    interacciones_seed = [
        (cliente_ids[0], "WhatsApp Comercial", "Aviso de llegada de la nueva colección primavera de Lodi. Muy interesada.", 10),
        (cliente_ids[1], "Aviso Talla Agotada", "Encargo de Blucher Martinelli Oxford talla 43 reservado para prueba.", 18),
        (cliente_ids[2], "Consulta Stock", "Preguntó por disponibilidad de sandalias Birkenstock en tono marrón.", 28),
        (cliente_ids[4], "WhatsApp Comercial", "Campaña de reactivación cambio de temporada enviada.", 5),
        (cliente_ids[6], "WhatsApp Comercial", "Cupón de bienvenida/retorno del 10% enviado.", 12)
    ]

    for cid, tipo, coment, d_atras in interacciones_seed:
        fecha_int = (now - timedelta(days=d_atras)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO interacciones (id_cliente, tipo, comentarios, fecha)
            VALUES (?, ?, ?, ?)
        """, (cid, tipo, coment, fecha_int))

    conn.commit()

    # 7. Ejecutar cálculo inicial de scoring para todos los clientes
    recalcular_todos(conn)
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_data()
    print("Base de datos y scoring inicializados correctamente.")

import urllib.request
import json

BASE = 'http://127.0.0.1:5000'

def post_json(path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get_json(path):
    with urllib.request.urlopen(BASE + path) as resp:
        return json.loads(resp.read().decode('utf-8'))

# 1. Crear nuevo cliente con preferencias
nuevo_cliente = {
    'nombre': 'Marina Soler Vidal',
    'telefono': '699112233',
    'email': 'marina.soler@email.com',
    'fecha_nacimiento': '1992-03-15',
    'observaciones': 'Horma ancha, talla 38 siempre',
    'preferencias': [
        {'categoria_calzado': 'Casual', 'talla_habitual': '38', 'marca_favorita': 'Pikolinos'},
        {'categoria_calzado': 'Deportivo', 'talla_habitual': '38', 'marca_favorita': 'Nike'}
    ]
}
res_cli = post_json('/api/clientes', nuevo_cliente)
print('1. Cliente creado:', res_cli)
id_cliente = res_cli['id_cliente']

# 2. Consultar detalle de cliente recién creado
cli_detalle = get_json(f'/api/clientes/{id_cliente}')
print(f"2. Score inicial de Marina: {cli_detalle['score_total']} pts ({cli_detalle['categoria_cliente']})")
assert len(cli_detalle['preferencias']) == 2

# 3. Obtener variantes para comprar
vars = get_json('/api/variantes')
var_disp = next(v for v in vars if v['stock_actual'] > 0 and v['talla'] == '38')
print(f"3. Variante seleccionada: {var_disp['nombre_modelo']} (Talla {var_disp['talla']}, Color {var_disp['color']}, Stock antes: {var_disp['stock_actual']})")

# 4. Registrar una venta para Marina
venta_data = {
    'id_cliente': id_cliente,
    'metodo_pago': 'Tarjeta',
    'items': [
        {'id_variante': var_disp['id_variante'], 'cantidad': 1, 'precio_unitario': var_disp['precio_base']}
    ]
}
res_venta = post_json('/api/ventas', venta_data)
print('4. Venta registrada con éxito:', res_venta)
assert res_venta['nuevo_score']['score_total'] >= 7, 'Scoring recalculado tras compra'

# 5. Probar matching inteligente de calzado
match_res = get_json('/api/matching/calzado?talla=38&marca=Pikolinos')
print(f"5. Matching calzado talla 38 Pikolinos encontró {len(match_res)} clientes!")
assert any(c['id_cliente'] == id_cliente for c in match_res), 'Marina debe aparecer en matching'

# 6. Registrar interacción
inter_data = {
    'id_cliente': id_cliente,
    'tipo': 'WhatsApp Comercial',
    'comentarios': 'Avisada de llegada de sandalias Pikolinos talla 38.'
}
res_inter = post_json('/api/interacciones', inter_data)
print('6. Interacción registrada:', res_inter)

print('\n>>> TODOS LOS TESTS DE INTEGRACIÓN FUNCIONAN AL 100% <<<')

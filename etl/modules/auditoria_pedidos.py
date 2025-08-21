"""
Script de auditoría para comparar la colección 'pedidos' de Firestore con los pedidos originales de Jumpseller.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import requests

# Inicializar Firebase
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Configuración Jumpseller
JUMPSELLER_API_URL = 'https://api.jumpseller.com/v1/orders/'
JUMPSELLER_API_KEY = 'TU_API_KEY_AQUI'  # Reemplaza por tu API Key


def get_pedidos_firestore():
    """Lee todos los documentos de la colección 'pedidos' en Firestore."""
    pedidos_ref = db.collection('pedidos')
    docs = pedidos_ref.stream()
    pedidos = [doc.to_dict() for doc in docs]
    return pedidos


def get_jumpseller_order(order_id):
    """Obtiene el pedido original de Jumpseller usando el ID."""
    url = f"{JUMPSELLER_API_URL}{order_id}.json?api_key={JUMPSELLER_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None


def comparar_pedidos(pedido_firestore, pedido_jumpseller):
    """Compara los campos clave entre Firestore y Jumpseller."""
    diferencias = {}
    # Campos clave para comparar
    campos = [
        'id', 'userId', 'addressId', 'total', 'status', 'createdAt', 'updatedAt',
        'items', 'paymentDetails', 'serviceAddress', 'contactOnSite', 'statusHistory',
        'customer', 'shipping_address', 'billing_address', 'products', 'payment_method'
    ]
    for campo in campos:
        valor_fs = pedido_firestore.get(campo)
        valor_js = pedido_jumpseller.get(campo) if pedido_jumpseller else None
        if valor_fs != valor_js:
            diferencias[campo] = {'firestore': valor_fs, 'jumpseller': valor_js}
    # Comparación avanzada para listas de productos/servicios
    if 'items' in pedido_firestore and pedido_jumpseller:
        productos_fs = pedido_firestore.get('items', [])
        productos_js = pedido_jumpseller.get('products', [])
        if productos_fs != productos_js:
            diferencias['productos_detalle'] = {'firestore': productos_fs, 'jumpseller': productos_js}
    return diferencias


def auditoria_pedidos():
    pedidos = get_pedidos_firestore()
    resumen = []
    for pedido in pedidos:
        order_id = pedido.get('id')
        pedido_js = get_jumpseller_order(order_id)
        diferencias = comparar_pedidos(pedido, pedido_js)
        resumen.append({'id': order_id, 'diferencias': diferencias})
    # Mostrar resumen
    for r in resumen:
        print(f"Pedido ID: {r['id']}")
        if r['diferencias']:
            print("  Diferencias:")
            for campo, vals in r['diferencias'].items():
                print(f"    {campo}: Firestore={vals['firestore']} | Jumpseller={vals['jumpseller']}")
        else:
            print("  Sin diferencias relevantes.")
        print()

if __name__ == "__main__":
    auditoria_pedidos()

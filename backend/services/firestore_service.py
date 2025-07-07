# Archivo: backend/services/firestore_service.py
from firebase_admin import firestore
from typing import List, Dict, Any

def get_valid_users_data() -> List[Dict[str, Any]]:
    """
    Obtiene los datos de los primeros 50 usuarios con validUser = true.
    La consulta está limitada a 50 resultados para proteger el rendimiento.

    Returns:
        List[Dict[str, Any]]: Una lista de hasta 50 usuarios.
    """
    db = firestore.client()
    users_ref = db.collection('users')

    # 1. Crea una consulta para filtrar por validUser == True
    query = users_ref.where('validUser', '==', True)

    # --- ¡AÑADE ESTA LÍNEA! ---
    # 2. Limita el número de documentos a devolver a 50
    query = query.limit(50)
    # ---------------------------

    # 3. Ejecuta la consulta y obtén los documentos
    docs = query.stream()

    user_data_list = []
    for doc in docs:
        data = doc.to_dict()
        user_info = {
            "id": doc.id,
            "accountHolderName": data.get("accountHolderName", "N/A"),
            "rut": data.get("rut", "N/A"),
            "role": data.get("role", "N/A"),
            "email": data.get("email", "N/A")
        }
        user_data_list.append(user_info)
    
    print(f"Datos de {len(user_data_list)} usuarios válidos obtenidos (límite 50).")
    return user_data_list


def calculate_average_order_value() -> float:
    """
    Calcula el ticket promedio (AOV) de todas las órdenes completadas.

    Returns:
        float: El valor del ticket promedio en CLP. Retorna 0.0 si no hay órdenes.
    """
    db = firestore.client()
    orders_ref = db.collection('orders')

    # Consulta para obtener solo las órdenes completadas
    # Usamos .select(["total"]) para traer solo el campo que necesitamos,
    # lo cual es mucho más eficiente y barato que traer el documento completo.
    query = orders_ref.where('status', '==', 'completed').select(["total"])
    completed_orders = query.stream()

    total_revenue = 0.0
    order_count = 0

    for order in completed_orders:
        order_data = order.to_dict()
        if "total" in order_data:
            total_revenue += order_data["total"]
            order_count += 1
            
    if order_count == 0:
        return 0.0

    return total_revenue / order_count
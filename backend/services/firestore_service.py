# backend/services/firestore_service.py

from firebase_admin import firestore
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any


def get_db_client():
    """
    Función para obtener el cliente de Firestore.
    Esto asegura que firestore.client() solo se llame DESPUÉS
    de que firebase_admin.initialize_app() se haya ejecutado.
    """
    return firestore.client()


def get_user_role(uid: str) -> str:
    """Obtiene el rol (accountType) de un usuario desde su documento en Firestore."""
    db = get_db_client()
    try:
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            return user_doc.to_dict().get('accountType', 'customer') # 'customer' como rol por defecto
    except Exception as e:
        print(f"Error al obtener el rol del usuario {uid}: {e}")
    return 'customer' # Devuelve un rol por defecto en caso de error

def get_summary_kpis(start_date: datetime, end_date: datetime):
    """
    Calcula los KPIs principales para el resumen ejecutivo.
    - Nuevos Usuarios
    - Ticket Promedio (AOV)
    - Tasa de Conversión de Carrito
    - Serie de tiempo de ventas
    """
    # 1. KPI: Nuevos Usuarios
    users_ref = db.collection('users').where('createdAt', '>=', start_date).where('createdAt', '<=', end_date)
    new_users_count = len(list(users_ref.stream()))

    # 2. KPI: Ticket Promedio (AOV)
    orders_ref = db.collection('orders').where('status', '==', 'completed').where('createdAt', '>=', start_date).where('createdAt', '<=', end_date)
    orders_docs = list(orders_ref.stream())
    
    total_revenue = sum(doc.to_dict().get('total', 0) for doc in orders_docs)
    completed_orders_count = len(orders_docs)
    aov_clp = total_revenue / completed_orders_count if completed_orders_count > 0 else 0

    # 3. KPI: Tasa de Conversión de Carrito
    carts_ref = db.collection('carts').where('createdAt', '>=', start_date).where('createdAt', '<=', end_date)
    all_carts = list(carts_ref.stream())
    total_carts_count = len(all_carts)
    converted_carts_count = sum(1 for doc in all_carts if doc.to_dict().get('status') == 'converted')
    conversion_rate = (converted_carts_count / total_carts_count) * 100 if total_carts_count > 0 else 0

    # 4. Datos para el Gráfico de Series de Tiempo
    sales_data = []
    if orders_docs:
        for doc in orders_docs:
            order_data = doc.to_dict()
            sales_data.append({
                'date': order_data['createdAt'],
                'sales': order_data['total']
            })
    
    # Usamos Pandas para agrupar las ventas por día
    if sales_data:
        df = pd.DataFrame(sales_data)
        df['date'] = pd.to_datetime(df['date']).dt.date
        daily_sales = df.groupby('date')['sales'].sum().reset_index()
        time_series = {
            "dates": daily_sales['date'].tolist(),
            "sales": daily_sales['sales'].tolist()
        }
    else:
        time_series = {"dates": [], "sales": []}

    return {
        "new_users": new_users_count,
        "aov_clp": aov_clp,
        "conversion_rate": round(conversion_rate, 2),
        "time_series_data": time_series
    }

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
    """
    orders_ref = db.collection('orders')
    query = orders_ref.where('status', '==', 'completed').select(["total"])
    completed_orders_docs = list(query.stream()) # Convertimos a lista para manejar el caso de 0 órdenes
    
    if not completed_orders_docs:
        return 0.0

    # Usamos una expresión generadora, más eficiente en memoria
    total_revenue = sum(doc.to_dict().get('total', 0) for doc in completed_orders_docs)
    order_count = len(completed_orders_docs)

    return total_revenue / order_count


# --- Funciones para la página de Adquisición ---
def get_acquisition_kpis(start_date, end_date):
    db = get_db_client()
    # Lógica para Nuevos Usuarios, Tasa de Onboarding, Canales, etc.
    # Esta es una implementación de ejemplo. Deberás completarla.
    return {
        "new_users": db.collection('users').where('createdAt', '>=', start_date).where('createdAt', '<=', end_date).stream(),
        "onboarding_completed": db.collection('users').where('onboardingCompleted', '==', True).stream(),
        "acquisition_channels": {"google": 120, "facebook": 80, "referral": 50} # Mock data
    }

# --- Funciones para la página de Conversión ---
def get_conversion_kpis(start_date, end_date):
    db = get_db_client()
    # Lógica para AOV, Tasa de Abandono, etc.
    return {
        "aov_clp": calculate_average_order_value(), # Reutilizamos la función
        "abandonment_rate": 42.5, # Mock data
        "top_services": [{"name": "Gasfitería", "sales": 1500000}, {"name": "Electricidad", "sales": 950000}] # Mock
    }
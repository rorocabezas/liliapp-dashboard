# backend/services/firestore_service.py
import pandas as pd
import traceback
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any


# ===================================================================
# ===               HELPER & UTILITY FUNCTIONS                    ===
# ===================================================================
COMMUNE_COORDS = {
    # Coordenadas aproximadas para algunas comunas de la RM.
    # En un sistema de producción, esto podría venir de una base de datos o un archivo de configuración.
    "Santiago": [-33.4372, -70.6506],
    "Providencia": [-33.4216, -70.6083],
    "Las Condes": [-33.4167, -70.5667],
    "Vitacura": [-33.3916, -70.5542],
    "La Reina": [-33.4478, -70.5367],
    "Ñuñoa": [-33.4542, -70.6022],
    "Huechuraba": [-33.3667, -70.65],
    "No especificada": [-33.45, -70.6667] # Coordenada genérica para Santiago
}

def get_db_client():
    """Obtiene el cliente de Firestore de forma segura después de la inicialización."""
    return firestore.client()

def _get_completed_orders_in_range(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """Función de ayuda para obtener todas las órdenes completadas en un rango de fechas."""
    db = get_db_client()
    orders_query = db.collection('orders').where(filter=FieldFilter('status', '==', 'completed')).where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    return [doc.to_dict() for doc in orders_query.stream()]

def get_user_role(uid: str) -> str:
    """Obtiene el rol (accountType) de un usuario desde su documento en Firestore."""
    db = get_db_client()
    try:
        # Asumiendo que aún se necesita una colección 'users' para la autenticación
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            return user_doc.to_dict().get('accountType', 'customer')
    except Exception as e:
        print(f"Error al obtener el rol del usuario {uid}: {e}")
    return 'customer'
    
# ===================================================================
# ===                   FUNCIONES DE CÁLCULO DE KPIs              ===
# ===================================================================

def get_acquisition_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """
    Calcula KPIs de adquisición, incluyendo una serie de tiempo diaria robusta y
    datos enriquecidos por comuna para el mapa de calor.
    """
    db = get_db_client()
    try:
        customers_query = db.collection('customers').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
        customers_docs = [doc.to_dict() for doc in customers_query.stream()]
        
        # --- Inicializar la estructura de respuesta ---
        result = {
            "new_customers": 0,
            "onboarding_rate": 0,
            "acquisition_by_commune": [],
            "daily_new_users": {"dates": [], "counts": []}
        }
        
        # Si no hay nuevos clientes en el período, devolvemos la estructura vacía
        if not customers_docs:
            return result

        df_customers = pd.DataFrame(customers_docs)
        new_customers_count = len(df_customers)
        result["new_customers"] = new_customers_count

        # --- Cálculo de Tasa de Onboarding ---
        if 'onboardingCompleted' in df_customers.columns:
            completed_onboarding = df_customers['onboardingCompleted'].fillna(False).sum()
            onboarding_rate = (completed_onboarding / new_customers_count) * 100 if new_customers_count > 0 else 0
            result["onboarding_rate"] = round(onboarding_rate, 2)

        # --- Cálculo de Adquisición por Comuna (para el mapa) ---
        if 'addresses' in df_customers.columns:
            df_customers['primaryCommune'] = df_customers['addresses'].apply(
                lambda addrs: addrs[0].get('commune') if isinstance(addrs, list) and len(addrs) > 0 and addrs[0].get('commune') else 'No especificada'
            )
            acquisition_by_commune_counts = df_customers['primaryCommune'].value_counts().reset_index()
            acquisition_by_commune_counts.columns = ['commune', 'count']

            # Enriquecer con coordenadas geográficas
            acquisition_by_commune_counts['lat'] = acquisition_by_commune_counts['commune'].map(lambda x: COMMUNE_COORDS.get(x, COMMUNE_COORDS["No especificada"])[0])
            acquisition_by_commune_counts['lon'] = acquisition_by_commune_counts['commune'].map(lambda x: COMMUNE_COORDS.get(x, COMMUNE_COORDS["No especificada"])[1])
            
            result["acquisition_by_commune"] = acquisition_by_commune_counts.to_dict('records')

        # --- Cálculo de Serie de Tiempo Diaria ---
        if 'createdAt' in df_customers.columns:
            df_customers['signup_date'] = pd.to_datetime(df_customers['createdAt'], utc=True).dt.date
            daily_counts = df_customers.groupby('signup_date').size()
            
            # Crear un rango de fechas completo para rellenar los días sin registros
            full_date_range = pd.date_range(start=start_date.date(), end=end_date.date())
            daily_counts = daily_counts.reindex(full_date_range.date, fill_value=0)
            
            datetime_index = pd.to_datetime(daily_counts.index)
            result["daily_new_users"] = {
                "dates": datetime_index.strftime('%Y-%m-%d').tolist(),
                "counts": daily_counts.values.tolist()
            }
            
        return result
        
    except Exception as e:
        print(f"!!! ERROR en get_acquisition_kpis: {repr(e)}")
        traceback.print_exc()
        return {} # Devolvemos un diccionario vacío en caso de error catastrófico

def get_engagement_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """
    Calcula KPIs de engagement, con un análisis de Top Categorías en lugar de Top Servicios.
    """
    db = get_db_client()
    completed_orders_docs = _get_completed_orders_in_range(start_date, end_date)
    
    # ... (la lógica de abandono de carrito no cambia)
    carts_ref = db.collection('carts').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    all_carts = [doc.to_dict() for doc in carts_ref.stream()]
    total_carts, converted_carts = len(all_carts), sum(1 for cart in all_carts if cart.get('status') == 'converted')
    abandonment_rate = ((total_carts - converted_carts) / total_carts) * 100 if total_carts > 0 else 0
    
    if not completed_orders_docs:
        return {"aov_clp": 0, "purchase_frequency": 0, "payment_method_distribution": {}, "abandonment_rate": round(abandonment_rate, 2), "top_categories": []}

    df_orders = pd.DataFrame(completed_orders_docs)
    
    # --- KPIs que no cambian ---
    aov_clp = df_orders['total'].mean()
    purchase_frequency = len(df_orders) / df_orders['customerId'].nunique() if df_orders['customerId'].nunique() > 0 else 0
    df_orders['payment_type'] = df_orders['paymentDetails'].apply(lambda x: x.get('type', 'Desconocido') if isinstance(x, dict) else 'Desconocido')
    payment_distribution = df_orders['payment_type'].value_counts().to_dict()

    # --- NUEVA LÓGICA: Top 5 Categorías por Monto Vendido ---
    top_categories = []
    if 'items' in df_orders.columns:
        # 1. Obtenemos una lista de todos los serviceId únicos vendidos en el período
        all_items = df_orders.explode('items').dropna(subset=['items'])
        all_items['serviceId'] = all_items['items'].apply(lambda x: x.get('serviceId') if isinstance(x, dict) else None)
        unique_service_ids = all_items['serviceId'].dropna().unique().tolist()
        
        if unique_service_ids:
            # 2. Hacemos una única consulta para obtener los detalles de esos servicios
            services_docs = {doc.id: doc.to_dict() for doc in db.collection('services').where(filter=FieldFilter('id', 'in', unique_service_ids)).stream()}
            
            # 3. Mapeamos cada serviceId a su nombre de categoría
            all_items['category_info'] = all_items['serviceId'].map(lambda sid: services_docs.get(sid, {}).get('category'))
            all_items['category_name'] = all_items['category_info'].apply(lambda c: c.get('name') if isinstance(c, dict) else 'Sin Categoría')
            all_items['item_price'] = all_items['items'].apply(lambda i: i.get('price', 0) if isinstance(i, dict) else 0)
            
            # 4. Agrupamos por nombre de categoría y sumamos el total vendido
            category_sales = all_items.groupby('category_name')['item_price'].sum().nlargest(5)
            top_categories = [{"name": index, "sales": value} for index, value in category_sales.items()]

    return {
        "aov_clp": round(aov_clp, 2),
        "purchase_frequency": round(purchase_frequency, 2),
        "payment_method_distribution": payment_distribution,
        "abandonment_rate": round(abandonment_rate, 2),
        "top_categories": top_categories # <-- Devolvemos las categorías en lugar de los servicios
    }

def get_operations_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """
    Calcula KPIs de operaciones y calidad de forma robusta.
    """
    db = get_db_client()
    orders_query = db.collection('orders').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    all_orders = [doc.to_dict() for doc in orders_query.stream()]
    
    if not all_orders:
        return {"cancellation_rate": 0, "avg_rating": 0, "orders_by_commune": {}, "orders_by_hour": {}}

    df_all_orders = pd.DataFrame(all_orders)

    # --- Cálculo Robusto de Tasa de Cancelación ---
    if 'status' in df_all_orders.columns:
        total_orders = len(df_all_orders)
        cancellation_rate = (df_all_orders['status'] == 'cancelled').sum() / total_orders * 100 if total_orders > 0 else 0
    else:
        cancellation_rate = 0

    df_completed = df_all_orders[df_all_orders['status'] == 'completed'].copy() if 'status' in df_all_orders.columns else pd.DataFrame()
    
    # --- Cálculo Robusto de Calificación Promedio ---
    if not df_completed.empty and 'rating' in df_completed.columns:
        # Usamos .dropna() para ignorar órdenes sin calificación
        ratings = df_completed['rating'].dropna().apply(lambda r: r.get('stars') if isinstance(r, dict) else None)
        avg_rating = ratings.mean()
    else:
        avg_rating = 0

    # --- Cálculo Robusto de Órdenes por Comuna ---
    if not df_completed.empty and 'serviceAddress' in df_completed.columns:
        orders_by_commune = df_completed['serviceAddress'].apply(lambda sa: sa.get('commune', 'Desconocida') if isinstance(sa, dict) else 'Desconocida').value_counts().to_dict()
    else:
        orders_by_commune = {}
    
    # --- Cálculo Robusto de Órdenes por Hora ---
    if 'createdAt' in df_all_orders.columns:
        # Usamos errors='coerce' para manejar fechas malformadas
        df_all_orders['hour'] = pd.to_datetime(df_all_orders['createdAt'], errors='coerce', utc=True).dt.hour
        # Usamos .dropna() para ignorar filas donde la fecha no se pudo convertir
        orders_by_hour = df_all_orders.dropna(subset=['hour'])['hour'].astype(int).value_counts().sort_index().reindex(range(24), fill_value=0).tolist()
    else:
        orders_by_hour = [0] * 24
    
    # Nota: El cálculo de avg_cycle_time_days se omite por ahora hasta que se valide la existencia y formato de 'statusHistory'.
    
    return {
        "cancellation_rate": round(cancellation_rate, 2),
        "avg_rating": round(avg_rating, 2) if pd.notna(avg_rating) else 0,
        "orders_by_commune": orders_by_commune,
        "orders_by_hour": orders_by_hour
    }

def get_retention_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Calcula KPIs de retención."""
    all_orders_docs = _get_completed_orders_in_range(start_date, end_date)
    if not all_orders_docs: return {"ltv_clp": 0, "repurchase_rate": 0}
    
    df_orders = pd.DataFrame(all_orders_docs)
    total_revenue = df_orders['total'].sum()
    distinct_customers_who_purchased = df_orders['customerId'].nunique()
    ltv_clp = total_revenue / distinct_customers_who_purchased if distinct_customers_who_purchased > 0 else 0
    
    customer_order_counts = df_orders.groupby('customerId').size()
    repeat_customers = (customer_order_counts > 1).sum()
    repurchase_rate = (repeat_customers / distinct_customers_who_purchased) * 100 if distinct_customers_who_purchased > 0 else 0

    return {"ltv_clp": round(ltv_clp, 2), "repurchase_rate": round(repurchase_rate, 2)}


def get_rfm_segmentation(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Realiza un análisis RFM para segmentar a los clientes en un período de tiempo."""
    all_orders_docs = _get_completed_orders_in_range(start_date, end_date)

    if not all_orders_docs:
        return {"segment_distribution": {}, "sample_customers": {}}

    orders_df = pd.DataFrame(all_orders_docs)
    orders_df['createdAt'] = pd.to_datetime(orders_df['createdAt'], utc=True)
    snapshot_date = end_date # Usamos el fin del rango como fecha de referencia
    
    rfm_df = orders_df.groupby('customerId').agg(
        recency=('createdAt', lambda date: (snapshot_date - date.max()).days),
        frequency=('id', 'count'),
        monetary=('total', 'sum')
    ).reset_index() # reset_index para tener customerId como columna
    
    # Manejo de qcut con posibles valores duplicados y pocos datos
    try:
        rfm_df['R_score'] = pd.qcut(rfm_df['recency'], 4, labels=[4, 3, 2, 1], duplicates='drop')
        rfm_df['F_score'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
        rfm_df['M_score'] = pd.qcut(rfm_df['monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
    except ValueError:
        rfm_df['R_score'] = 1; rfm_df['F_score'] = 1; rfm_df['M_score'] = 1

    # Asegurarnos de que las columnas de score existan antes de convertirlas a string
    for score in ['R_score', 'F_score', 'M_score']:
        if score not in rfm_df.columns: rfm_df[score] = 1
            
    rfm_df['RFM_score'] = rfm_df['R_score'].astype(str) + rfm_df['F_score'].astype(str) + rfm_df['M_score'].astype(str)
    
    segment_map = {
        r'[3-4][3-4][3-4]': '🏆 Campeones',
        r'[3-4][1-2][1-4]': '💖 Leales',
        r'[1-2][3-4][3-4]': '😮 En Riesgo',
        r'[1-2][1-2][1-2]': '❄️ Hibernando'
    }
    rfm_df['segment'] = rfm_df['RFM_score'].replace(segment_map, regex=True)
    # Si un score no coincide con los patrones, se clasifica como 'Otros'
    rfm_df.loc[~rfm_df['segment'].isin(segment_map.values()), 'segment'] = 'Otros'
    
    segment_distribution = rfm_df['segment'].value_counts().to_dict()
    
    # Para la muestra, enriquecemos con el email desde la colección 'customers'
    db = get_db_client()
    customers_docs = {doc.id: doc.to_dict() for doc in db.collection('customers').stream()}
    rfm_df['email'] = rfm_df['customerId'].map(lambda cid: customers_docs.get(cid, {}).get('email', 'N/A'))

    sample_customers = {
        segment: rfm_df[rfm_df['segment'] == segment].head(5)[['customerId', 'email', 'recency', 'frequency', 'monetary']].to_dict('records') 
        for segment in rfm_df['segment'].unique()
    }
    
    return {"segment_distribution": segment_distribution, "sample_customers": sample_customers}

# ===================================================================
# ===             FUNCIONES GENÉRICAS DE CRUD (ADMIN)             ===
# ===================================================================

def get_all_documents(collection_name: str) -> List[Dict[str, Any]]:
    db = get_db_client()
    docs = db.collection(collection_name).stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]

def update_document(collection_name: str, doc_id: str, data: Dict[str, Any]):
    get_db_client().collection(collection_name).document(doc_id).update(data)

def create_document(collection_name: str, data: Dict[str, Any], doc_id: str = None) -> str:
    db = get_db_client()
    doc_ref = db.collection(collection_name).document(doc_id) if doc_id else db.collection(collection_name).document()
    doc_ref.set(data)
    return doc_ref.id

# --- CRUD para Colección 'customers' (Modelo Nuevo) ---
def get_all_customers() -> List[Dict[str, Any]]:
    return get_all_documents("customers")

def get_customer(customer_id: str) -> Dict[str, Any]:
    db = get_db_client()
    doc = db.collection("customers").document(customer_id).get()
    return {**doc.to_dict(), "id": doc.id} if doc.exists else None

def update_customer_main_fields(customer_id: str, data: Dict[str, Any]):
    update_document("customers", customer_id, data)

def add_address_to_customer(customer_id: str, address_data: Dict[str, Any]):
    customer_ref = get_db_client().collection('customers').document(customer_id)
    customer_ref.update({"addresses": firestore.ArrayUnion([address_data])})

def update_address_in_customer_array(customer_id: str, address_data: Dict[str, Any]):
    db = get_db_client()
    customer_ref = db.collection('customers').document(customer_id)
    customer_doc = customer_ref.get()
    if not customer_doc.exists: raise ValueError(f"Cliente {customer_id} no encontrado.")
    customer_data = customer_doc.to_dict()
    addresses = customer_data.get('addresses', [])
    address_id_to_update = address_data.get("id")
    address_found = False
    for i, addr in enumerate(addresses):
        if addr.get("id") == address_id_to_update:
            addresses[i] = address_data; address_found = True; break
    if not address_found: raise ValueError(f"Dirección {address_id_to_update} no encontrada.")
    customer_ref.update({"addresses": addresses})

# --- CRUD para Colección 'services' (Modelo Híbrido Nuevo) ---
def add_item_to_service_array(service_id: str, array_name: str, item_data: dict):
    db = get_db_client()
    service_ref = db.collection('services').document(service_id)
    service_ref.update({array_name: firestore.ArrayUnion([item_data])})
    
# ===================================================================
# ===        FUNCIONES DE SOPORTE (AUDITORÍA, SALUD, ETC.)        ===
# ===================================================================

def get_firestore_data_health_summary() -> dict:
    db = get_db_client()
    summary = {"collection_counts": {}, "user_health": {}}
    main_collections = ["users", "orders", "services", "categories", "customers"]
    for col in main_collections:
        docs = db.collection(col).stream()
        summary["collection_counts"][col] = sum(1 for _ in docs)
    
    customers_ref = db.collection("customers").stream()
    all_customers = list(customers_ref)
    total_customers = len(all_customers)
    
    if total_customers > 0:
        customers_dicts = [doc.to_dict() for doc in all_customers]
        with_rut = sum(1 for c in customers_dicts if c.get("rut"))
        with_addresses = sum(1 for c in customers_dicts if c.get("addresses"))
        addresses_counts = [len(c.get("addresses", [])) for c in customers_dicts]
        
        summary["user_health"] = {
            "total_customers": total_customers,
            "with_rut_percent": (with_rut / total_customers) * 100,
            "with_addresses_percent": (with_addresses / total_customers) * 100,
            "avg_addresses_per_customer": sum(addresses_counts) / len(addresses_counts) if addresses_counts else 0,
            "max_addresses_in_one_customer": max(addresses_counts) if addresses_counts else 0
        }
    return summary

def get_all_documents_from_subcollection(main_collection_name: str, subcollection_name: str) -> list:
    db = get_db_client()
    all_docs = []
    for doc in db.collection(main_collection_name).stream():
        parent_id = doc.id
        for sub_doc in doc.reference.collection(subcollection_name).stream():
            sub_doc_data = sub_doc.to_dict(); sub_doc_data['userId'] = parent_id; all_docs.append(sub_doc_data)
    return all_docs

def get_firestore_data_for_audit(order_id: str) -> dict:
    db = get_db_client()
    audit_data = {"order": None, "user": None, "profile": None, "address": None}
    order_doc = db.collection("orders").document(order_id).get()
    if not order_doc.exists: return {"error": f"Orden {order_id} no encontrada."}
    order_data = order_doc.to_dict(); audit_data["order"] = order_data
    user_id = order_data.get("userId")
    if user_id:
        user_doc = db.collection("users").document(user_id).get()
        if user_doc.exists: audit_data["user"] = user_doc.to_dict()
        profile_doc = db.collection("users").document(user_id).collection("customer_profiles").document(user_id).get()
        if profile_doc.exists: audit_data["profile"] = profile_doc.to_dict()
    address_id = order_data.get("addressId")
    if user_id and address_id:
        address_doc = db.collection("users").document(user_id).collection("customer_profiles").document(user_id).collection("addresses").document(address_id).get()
        if address_doc.exists: audit_data["address"] = address_doc.to_dict()
    return audit_data

def get_firestore_service_data_for_audit(service_id: str) -> dict:
    db = get_db_client()
    audit_data = {"service": None, "category": None, "variants": [], "subcategories": []}
    service_ref = db.collection("services").document(service_id)
    service_doc = service_ref.get()
    if not service_doc.exists: return {"error": f"Servicio {service_id} no encontrado."}
    service_data = service_doc.to_dict(); audit_data["service"] = service_data
    category_id = service_data.get("categoryId")
    if category_id:
        category_doc = db.collection("categories").document(str(category_id)).get()
        if category_doc.exists: audit_data["category"] = category_doc.to_dict()
    audit_data["variants"] = [doc.to_dict() for doc in service_ref.collection("variants").stream()]
    audit_data["subcategories"] = [doc.to_dict() for doc in service_ref.collection("subcategories").stream()]
    return audit_data
import pandas as pd
import traceback
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from firebase_admin.firestore import Query
from datetime import datetime, timedelta
from typing import List, Dict, Any

# ===================================================================
# ===               HELPER & UTILITY FUNCTIONS                    ===
# ===================================================================

def get_db_client():
    """Obtiene el cliente de Firestore de forma segura después de la inicialización."""
    return firestore.client()

def get_user_role(uid: str) -> str:
    """Obtiene el rol (accountType) de un usuario desde su documento en Firestore."""
    db = get_db_client()
    try:
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            return user_doc.to_dict().get('accountType', 'customer')
    except Exception as e:
        print(f"Error al obtener el rol del usuario {uid}: {e}")
    return 'customer'

# ===================================================================
# ===        FUNCIONES PARA LA PÁGINA 'RESUMEN EJECUTIVO'         ===
# ===================================================================

def get_summary_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Calcula los KPIs principales para el resumen ejecutivo."""
    db = get_db_client()
    
    users_query = db.collection('users').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    new_users_count = len(list(users_query.stream()))

    orders_query = db.collection('orders').where(filter=FieldFilter('status', '==', 'completed')).where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    orders_docs = list(orders_query.stream())
    
    total_revenue = sum(doc.to_dict().get('total', 0) for doc in orders_docs)
    aov_clp = total_revenue / len(orders_docs) if orders_docs else 0
    conversion_rate = get_cart_abandonment_rate(start_date, end_date, return_conversion=True)

    if orders_docs:
        sales_data = [{'date': doc.to_dict()['createdAt'], 'sales': doc.to_dict()['total']} for doc in orders_docs]
        df = pd.DataFrame(sales_data)
        df['date'] = pd.to_datetime(df['date']).dt.date
        daily_sales = df.groupby('date')['sales'].sum().reset_index()
        time_series = {"dates": [d.strftime('%Y-%m-%d') for d in daily_sales['date']], "sales": daily_sales['sales'].tolist()}
    else:
        time_series = {"dates": [], "sales": []}

    return {
        "new_users": new_users_count, "aov_clp": aov_clp,
        "conversion_rate": round(conversion_rate, 2), "time_series_data": time_series
    }

# ===================================================================
# ===         FUNCIONES PARA LA PÁGINA DE ADQUISICIÓN             ===
# ===================================================================

def get_all_documents_from_subcollection(main_collection_name: str, subcollection_name: str) -> list:
    """
    Obtiene todos los docs de una subcolección y enriquece cada uno
    con el ID de su documento padre como 'userId'.
    """
    db = get_db_client()
    all_docs = []
    main_collection_ref = db.collection(main_collection_name)
    for doc in main_collection_ref.stream():
        # Obtenemos el ID del documento padre (ej: el ID del usuario)
        parent_id = doc.id
        subcollection_ref = doc.reference.collection(subcollection_name)
        for sub_doc in subcollection_ref.stream():
            # Convertimos el subdocumento a diccionario
            sub_doc_data = sub_doc.to_dict()
            # Agregamos el ID del documento padre
            sub_doc_data['userId'] = parent_id
            all_docs.append(sub_doc_data)
    return all_docs

def get_acquisition_kpis(date_range_start: datetime, date_range_end: datetime) -> dict:
    """
    Calcula KPIs de adquisición, incluyendo una serie de tiempo diaria de nuevos usuarios.
    """
    print("\n--- Iniciando cálculo de KPIs de Adquisición (con series de tiempo) ---")
    try:
        print("Paso 1: Obteniendo documentos de 'users' y 'customer_profiles'...")
        users_docs = get_all_documents("users")
        profiles_docs = get_all_documents_from_subcollection("users", "customer_profiles")

        if not users_docs:
            print("  -> Advertencia: No se encontraron documentos en 'users'.")
            return {"new_users": 0, "onboarding_rate": 0, "acquisition_by_region": {}, "daily_new_users": {}}
        print(f"  -> Obtenidos {len(users_docs)} users y {len(profiles_docs)} profiles.")

        print("Paso 3: Creando DataFrames de Pandas...")
        df_users = pd.DataFrame(users_docs)
        df_profiles = pd.DataFrame(profiles_docs) if profiles_docs else pd.DataFrame(columns=['userId', 'primaryAddressRegion'])
        print("  -> DataFrames creados exitosamente.")

        print(f"Paso 4: Filtrando usuarios por rango de fechas: {date_range_start.date()} a {date_range_end.date()}")
        if 'createdAt' not in df_users.columns:
            raise ValueError("La columna 'createdAt' no existe en los documentos de 'users'.")
            
        df_users['createdAt'] = pd.to_datetime(df_users['createdAt'], errors='coerce').dt.tz_convert('UTC')
        df_users.dropna(subset=['createdAt'], inplace=True)

        mask = (df_users['createdAt'] >= date_range_start) & (df_users['createdAt'] <= date_range_end)
        df_filtered_users = df_users.loc[mask].copy()
        new_users_count = len(df_filtered_users)
        
        if new_users_count == 0:
            print("--- Cálculo finalizado: No hay nuevos usuarios en el período. ---")
            return {"new_users": 0, "onboarding_rate": 0, "acquisition_by_region": {}, "daily_new_users": {"dates": [], "counts": []}}
        
        print(f"  -> {new_users_count} usuarios encontrados en el rango de fechas.")

        print("Paso 5: Calculando serie de tiempo diaria...")
        df_filtered_users['signup_date'] = pd.to_datetime(df_filtered_users['createdAt']).dt.date
        daily_counts = df_filtered_users.groupby('signup_date').size()
        
        full_date_range = pd.date_range(start=date_range_start.date(), end=date_range_end.date())
        daily_counts = daily_counts.reindex(full_date_range.date, fill_value=0)

        
        datetime_index = pd.to_datetime(daily_counts.index)
        daily_new_users_series = {
            "dates": datetime_index.strftime('%Y-%m-%d').tolist(), 
            "counts": daily_counts.values.tolist()
        }
        print("  -> Serie de tiempo calculada.")
        
        print("Paso 6: Calculando KPIs restantes...")
        if 'onboardingCompleted' not in df_filtered_users.columns:
            df_filtered_users['onboardingCompleted'] = False
        df_filtered_users['onboardingCompleted'] = df_filtered_users['onboardingCompleted'].fillna(False)
        completed_onboarding = df_filtered_users['onboardingCompleted'].sum()
        onboarding_rate = (completed_onboarding / new_users_count) * 100
        print(f"  -> Tasa de Onboarding: {onboarding_rate:.2f}%")
            
        if not df_profiles.empty:
            df_merged = pd.merge(df_filtered_users, df_profiles, left_on='id', right_on='userId', how='left')
            acquisition_by_region = df_merged['primaryAddressRegion'].fillna('No especificada').value_counts().to_dict()
        else:
            acquisition_by_region = {}
        print(f"  -> Adquisición por Región: {acquisition_by_region}")

        result = {
            "new_users": new_users_count,
            "onboarding_rate": round(onboarding_rate, 2),
            "acquisition_by_region": acquisition_by_region,
            "daily_new_users": daily_new_users_series
        }
        print("--- Cálculo de KPIs finalizado con éxito. ---")
        return result

    except Exception as e:
        print(f"!!! ERROR CATASTRÓFICO en get_acquisition_kpis: {repr(e)}")
        traceback.print_exc()
        return {}

# ===================================================================
# ===       FUNCIONES PARA LA PÁGINA DE ENGAGEMENT Y CONVERSIÓN   ===
# ===================================================================

def get_engagement_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Calcula todos los KPIs relacionados con el engagement y la conversión."""
    db = get_db_client()
    orders_query = db.collection('orders').where(filter=FieldFilter('status', '==', 'completed')).where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    completed_orders_docs = list(orders_query.stream())
    
    abandonment_rate = get_cart_abandonment_rate(start_date, end_date)

    if not completed_orders_docs:
        return {"aov_clp": 0, "purchase_frequency": 0, "payment_method_distribution": {}, "abandonment_rate": abandonment_rate, "service_performance": []}

    total_revenue = sum(doc.to_dict().get('total', 0) for doc in completed_orders_docs)
    order_count = len(completed_orders_docs)
    distinct_customers = len(set(doc.to_dict().get('customerId') for doc in completed_orders_docs))

    aov_clp = total_revenue / order_count if order_count > 0 else 0
    purchase_frequency = order_count / distinct_customers if distinct_customers > 0 else 0

    payment_counts = {}
    for doc in completed_orders_docs:
        payment_type = doc.to_dict().get('paymentDetails', {}).get('type', 'Desconocido')
        payment_counts[payment_type] = payment_counts.get(payment_type, 0) + 1
    
    services_ref = db.collection('services').order_by('stats.purchaseCount', direction=Query.DESCENDING).limit(5)
    top_services = [{"name": doc.to_dict().get('name'), "purchases": doc.to_dict().get('stats', {}).get('purchaseCount', 0)} for doc in services_ref.stream()]

    return {"aov_clp": aov_clp, "purchase_frequency": purchase_frequency, "payment_method_distribution": payment_counts, "abandonment_rate": abandonment_rate, "service_performance": top_services}

def get_cart_abandonment_rate(start_date, end_date, return_conversion=False):
    """Calcula la tasa de abandono o conversión de carritos."""
    db = get_db_client()
    carts_ref = db.collection('carts').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    all_carts = list(carts_ref.stream())
    
    if not all_carts: return 0
    total_carts = len(all_carts)
    converted_carts = sum(1 for doc in all_carts if doc.to_dict().get('status') == 'converted')
    
    if return_conversion:
        return (converted_carts / total_carts) * 100 if total_carts > 0 else 0
    else:
        abandoned_carts = total_carts - converted_carts
        return (abandoned_carts / total_carts) * 100 if total_carts > 0 else 0

# ===================================================================
# ===       FUNCIONES PARA LA PÁGINA DE OPERACIONES Y CALIDAD   ===
# ===================================================================

def get_operations_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Calcula todos los KPIs relacionados con las operaciones y la calidad del servicio."""
    db = get_db_client()
    orders_query = db.collection('orders').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    all_orders_docs = list(orders_query.stream())
    
    if not all_orders_docs:
        return {"cancellation_rate": 0, "avg_cycle_time_days": 0, "avg_rating": 0, "orders_by_commune": {}, "orders_by_hour": {}}

    total_orders = len(all_orders_docs)
    cancelled_orders = sum(1 for doc in all_orders_docs if doc.to_dict().get('status') == 'cancelled')
    cancellation_rate = (cancelled_orders / total_orders) * 100 if total_orders > 0 else 0

    completed_orders_docs = [doc for doc in all_orders_docs if doc.to_dict().get('status') == 'completed']
    
    cycle_times_in_seconds = []
    for doc in completed_orders_docs:
        history = doc.to_dict().get('statusHistory', [])
        timestamps = {item['status']: item['timestamp'] for item in history if 'status' in item and 'timestamp' in item}
        if 'paid' in timestamps and 'completed' in timestamps:
            cycle_times_in_seconds.append((timestamps['completed'] - timestamps['paid']).total_seconds())
    
    avg_cycle_time_days = (sum(cycle_times_in_seconds) / len(cycle_times_in_seconds)) / (24 * 3600) if cycle_times_in_seconds else 0
    ratings = [doc.to_dict().get('rating', {}).get('stars', 0) for doc in completed_orders_docs if doc.to_dict().get('rating')]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0

    commune_counts = {}
    for doc in completed_orders_docs:
        commune = doc.to_dict().get('serviceAddress', {}).get('commune', 'Desconocida')
        commune_counts[commune] = commune_counts.get(commune, 0) + 1

    orders_by_hour = [0] * 24
    for doc in all_orders_docs:
        if created_at := doc.to_dict().get('createdAt'): orders_by_hour[created_at.hour] += 1
            
    return {
        "cancellation_rate": cancellation_rate, "avg_cycle_time_days": avg_cycle_time_days,
        "avg_rating": avg_rating, "orders_by_commune": commune_counts, "orders_by_hour": orders_by_hour
    }

# ===================================================================
# ===       FUNCIONES PARA LA PÁGINA DE RETENCIÓN Y LEALTAD       ===
# ===================================================================

def get_retention_kpis(period_end_date: datetime) -> Dict[str, Any]:
    """Calcula KPIs clave de retención y lealtad."""
    db = get_db_client()
    all_users_docs = list(db.collection('users').where(filter=FieldFilter('createdAt', '<=', period_end_date)).stream())
    all_orders_docs = list(db.collection('orders').where(filter=FieldFilter('status', '==', 'completed')).where(filter=FieldFilter('createdAt', '<=', period_end_date)).stream())

    if not all_users_docs:
        return {"mau": 0, "ltv_clp": 0, "repurchase_rate": 0, "cohort_data": None}

    thirty_days_ago = period_end_date - timedelta(days=30)
    mau_query = db.collection('users').where(filter=FieldFilter('lastLoginAt', '>=', thirty_days_ago)).where(filter=FieldFilter('lastLoginAt', '<=', period_end_date))
    mau_count = len(list(mau_query.stream()))

    ltv_clp, repurchase_rate, cohort_data_for_frontend = 0, 0, None
    if all_orders_docs:
        orders_df = pd.DataFrame([doc.to_dict() for doc in all_orders_docs])
        total_revenue, distinct_customers = orders_df['total'].sum(), orders_df['customerId'].nunique()
        ltv_clp = total_revenue / distinct_customers if distinct_customers > 0 else 0
        customer_order_counts = orders_df.groupby('customerId').size()
        repeat_customers, total_customers_with_orders = (customer_order_counts > 1).sum(), len(customer_order_counts)
        repurchase_rate = (repeat_customers / total_customers_with_orders) * 100 if total_customers_with_orders > 0 else 0
        
        users_df = pd.DataFrame([{'userId': doc.id, 'signup_month': pd.to_datetime(doc.to_dict()['createdAt']).to_period('M')} for doc in all_users_docs])
        orders_df['order_month'] = pd.to_datetime(orders_df['createdAt']).to_period('M')
        df_merged = pd.merge(orders_df, users_df, left_on='customerId', right_on='userId', how='left').dropna(subset=['signup_month'])
        
        get_month_diff = lambda start, end: (end.year - start.year) * 12 + (end.month - start.month)
        df_merged['cohort_index'] = df_merged.apply(lambda row: get_month_diff(row['signup_month'], row['order_month']), axis=1)
        
        cohort_data = df_merged.groupby(['signup_month', 'cohort_index'])['customerId'].nunique().reset_index()
        cohort_counts = cohort_data.pivot_table(index='signup_month', columns='cohort_index', values='customerId')
        retention_matrix = cohort_counts.divide(cohort_counts.iloc[:, 0], axis=0) * 100
        retention_matrix.index = retention_matrix.index.strftime('%Y-%m')
        cohort_data_for_frontend = retention_matrix.round(2).fillna(0).to_dict('split')

    return {"mau": mau_count, "ltv_clp": ltv_clp, "repurchase_rate": repurchase_rate, "cohort_data": cohort_data_for_frontend}

# ===================================================================
# ===       FUNCIONES PARA LA PÁGINA DE SEGMENTACIÓN              ===
# ===================================================================

def get_rfm_segmentation(period_end_date: datetime) -> Dict[str, Any]:
    """Realiza un análisis RFM completo para segmentar a los clientes."""
    db = get_db_client()
    orders_query = db.collection('orders').where(filter=FieldFilter('status', '==', 'completed')).where(filter=FieldFilter('createdAt', '<=', period_end_date))
    all_orders_docs = list(orders_query.stream())

    if not all_orders_docs:
        return {"segment_distribution": {}, "sample_customers": {}}

    orders_df = pd.DataFrame([{**doc.to_dict(), 'id': doc.id} for doc in all_orders_docs])
    orders_df['createdAt'] = pd.to_datetime(orders_df['createdAt'])
    snapshot_date = period_end_date + timedelta(days=1)
    
    rfm_df = orders_df.groupby('customerId').agg(recency=('createdAt', lambda date: (snapshot_date - date.max()).days), frequency=('id', 'count'), monetary=('total', 'sum'))
    rfm_df['R_score'] = pd.qcut(rfm_df['recency'], 4, labels=[4, 3, 2, 1], duplicates='drop')
    rfm_df['F_score'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
    rfm_df['M_score'] = pd.qcut(rfm_df['monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
    rfm_df['RFM_score'] = rfm_df['R_score'].astype(str) + rfm_df['F_score'].astype(str) + rfm_df['M_score'].astype(str)
    
    segment_map = {r'[3-4][3-4][3-4]': '🏆 Campeones', r'[3-4][1-2][1-4]': '💖 Clientes Leales', r'[1-2][3-4][3-4]': '😮 En Riesgo', r'[1-2][1-2][1-2]': '❄️ Hibernando'}
    rfm_df['segment'] = rfm_df['RFM_score'].replace(segment_map, regex=True)
    rfm_df['segment'] = rfm_df.apply(lambda row: 'Otros' if row['segment'].startswith(('1','2','3','4')) else row['segment'], axis=1)
    
    segment_distribution = rfm_df['segment'].value_counts().to_dict()
    sample_customers = {segment: rfm_df[rfm_df['segment'] == segment].head(5).reset_index().to_dict('records') for segment in rfm_df['segment'].unique()}
    
    return {"segment_distribution": segment_distribution, "sample_customers": sample_customers}

# ===================================================================
# ===             FUNCIONES GENÉRICAS DE CRUD (ADMIN)             ===
# ===================================================================

def get_all_documents(collection_name: str) -> List[Dict[str, Any]]:
    """Obtiene todos los documentos de una colección de nivel superior."""
    db = get_db_client()
    docs = db.collection(collection_name).stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]

def update_document(collection_name: str, doc_id: str, data: Dict[str, Any]):
    """Actualiza un documento en una colección de nivel superior."""
    db = get_db_client()
    db.collection(collection_name).document(doc_id).update(data)

def create_document(collection_name: str, data: Dict[str, Any]) -> str:
    """Crea un documento en una colección de nivel superior y devuelve su ID."""
    db = get_db_client()
    doc_ref = db.collection(collection_name).document()
    doc_ref.set(data)
    return doc_ref.id

def get_subcollection_document(parent_collection: str, parent_doc_id: str, subcollection_name: str, sub_doc_id: str) -> Dict[str, Any]:
    """Obtiene un único documento de una subcolección."""
    db = get_db_client()
    doc_ref = db.collection(parent_collection).document(parent_doc_id).collection(subcollection_name).document(sub_doc_id)
    doc = doc_ref.get()
    if doc.exists:
        return {**doc.to_dict(), "id": doc.id}
    return None

def list_subcollection_documents(parent_collection: str, parent_doc_id: str, subcollection_name: str) -> List[Dict[str, Any]]:
    """Obtiene todos los documentos de una subcolección."""
    db = get_db_client()
    docs = db.collection(parent_collection).document(parent_doc_id).collection(subcollection_name).stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]

def update_document_in_subcollection(parent_collection: str, parent_doc_id: str, subcollection_name: str, doc_id: str, data: Dict[str, Any]):
    """Actualiza un documento en una subcolección."""
    db = get_db_client()
    db.collection(parent_collection).document(parent_doc_id).collection(subcollection_name).document(doc_id).update(data)

def create_subcollection_document(parent_collection: str, parent_doc_id: str, subcollection_name: str, data: Dict[str, Any]) -> str:
    """Crea un documento en una subcolección y devuelve su ID."""
    db = get_db_client()
    doc_ref = db.collection(parent_collection).document(parent_doc_id).collection(subcollection_name).document()
    doc_ref.set(data)
    return doc_ref.id
    
def delete_document_in_subcollection(parent_collection: str, parent_doc_id: str, subcollection_name: str, doc_id: str):
    """Elimina un documento de una subcolección."""
    db = get_db_client()
    db.collection(parent_collection).document(parent_doc_id).collection(subcollection_name).document(doc_id).delete()

def list_nested_subcollection_documents(p_coll: str, p_doc: str, sub_coll1: str, sub_doc1: str, sub_coll2: str) -> List[Dict[str, Any]]:
    """Obtiene todos los documentos de una subcolección anidada (ej: addresses)."""
    db = get_db_client()
    docs = db.collection(p_coll).document(p_doc).collection(sub_coll1).document(sub_doc1).collection(sub_coll2).stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]

def update_document_in_nested_subcollection(p_coll: str, p_doc: str, sub_coll1: str, sub_doc1: str, sub_coll2: str, doc_id: str, data: Dict[str, Any]):
    """Actualiza un documento en una subcolección anidada."""
    db = get_db_client()
    doc_ref = db.collection(p_coll).document(p_doc).collection(sub_coll1).document(sub_doc1).collection(sub_coll2).document(doc_id)
    doc_ref.update(data)


def get_firestore_data_for_audit(order_id: str) -> dict:
    """
    Recopila todos los documentos de Firestore relacionados con un ID de orden.
    """
    db = get_db_client()
    audit_data = {
        "order": None,
        "user": None,
        "profile": None,
        "address": None
    }

    # 1. Obtener la orden
    order_ref = db.collection("orders").document(order_id)
    order_doc = order_ref.get()
    if not order_doc.exists:
        return {"error": f"Orden con ID {order_id} no encontrada en Firestore."}
    
    order_data = order_doc.to_dict()
    audit_data["order"] = order_data

    # 2. Obtener el usuario
    user_id = order_data.get("userId")
    if user_id:
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            audit_data["user"] = user_doc.to_dict()

    # 3. Obtener el perfil
    if user_id:
        # Asumiendo que el profileId es el mismo que el userId
        profile_ref = db.collection("users").document(user_id).collection("customer_profiles").document(user_id)
        profile_doc = profile_ref.get()
        if profile_doc.exists:
            audit_data["profile"] = profile_doc.to_dict()

    # 4. Obtener la dirección
    address_id = order_data.get("addressId")
    if user_id and address_id:
        # Asumiendo la estructura de subcolección anidada
        address_ref = db.collection("users").document(user_id).collection("customer_profiles").document(user_id).collection("addresses").document(address_id)
        address_doc = address_ref.get()
        if address_doc.exists:
            audit_data["address"] = address_doc.to_dict()

    return audit_data

def get_firestore_service_data_for_audit(service_id: str) -> dict:
    """
    Recopila todos los documentos de Firestore relacionados con un ID de servicio.
    """
    db = get_db_client()
    audit_data = {
        "service": None,
        "category": None,
        "variants": [],
        "subcategories": []
    }

    # 1. Obtener el servicio
    service_ref = db.collection("services").document(service_id)
    service_doc = service_ref.get()
    if not service_doc.exists:
        return {"error": f"Servicio con ID {service_id} no encontrado en Firestore."}
    
    service_data = service_doc.to_dict()
    audit_data["service"] = service_data

    # 2. Obtener la categoría
    category_id = service_data.get("categoryId")
    if category_id:
        category_ref = db.collection("categories").document(str(category_id))
        category_doc = category_ref.get()
        if category_doc.exists:
            audit_data["category"] = category_doc.to_dict()

    # 3. Obtener las variantes
    variants_ref = service_ref.collection("variants").stream()
    audit_data["variants"] = [doc.to_dict() for doc in variants_ref]

    # 4. Obtener las subcategorías
    subcategories_ref = service_ref.collection("subcategories").stream()
    audit_data["subcategories"] = [doc.to_dict() for doc in subcategories_ref]

    return audit_data

# ... (al final del archivo, en una nueva sección)

def get_firestore_data_health_summary() -> dict:
    """
    Realiza un análisis completo de la salud y completitud de los datos en Firestore.
    """
    db = get_db_client()
    summary = {
        "collection_counts": {},
        "user_health": {},
        "service_health": {}
    }

    # 1. Conteos de Colecciones Principales
    main_collections = ["users", "orders", "services", "categories"]
    for col in main_collections:
        # stream() es costoso para solo contar, pero es la forma más directa sin índices de conteo
        docs = db.collection(col).stream()
        summary["collection_counts"][col] = sum(1 for _ in docs)

    # 2. Análisis de Salud de la Colección 'users'
    users_ref = db.collection("users").stream()
    all_users = list(users_ref)
    total_users = len(all_users)
    
    if total_users > 0:
        profiles_count = 0
        profiles_with_rut = 0
        addresses_subcollection_count = 0
        total_addresses = 0
        addresses_per_user = []

        for user_doc in all_users:
            profile_ref = user_doc.reference.collection("customer_profiles").limit(1).get()
            if profile_ref:
                profiles_count += 1
                # Suponiendo que el profileId es el mismo que el userId
                profile_data = user_doc.reference.collection("customer_profiles").document(user_doc.id).get()
                if profile_data.exists and profile_data.to_dict().get("rut"):
                    profiles_with_rut += 1

                addresses_ref = user_doc.reference.collection("customer_profiles").document(user_doc.id).collection("addresses").stream()
                user_addresses = list(addresses_ref)
                if user_addresses:
                    addresses_subcollection_count += 1
                    num_addresses = len(user_addresses)
                    total_addresses += num_addresses
                    addresses_per_user.append(num_addresses)

        summary["user_health"] = {
            "total_users": total_users,
            "with_customer_profile_percent": (profiles_count / total_users) * 100 if total_users > 0 else 0,
            "profiles_with_rut_percent": (profiles_with_rut / profiles_count) * 100 if profiles_count > 0 else 0,
            "with_addresses_subcollection_percent": (addresses_subcollection_count / profiles_count) * 100 if profiles_count > 0 else 0,
            "avg_addresses_per_user": sum(addresses_per_user) / len(addresses_per_user) if addresses_per_user else 0,
            "max_addresses_in_one_user": max(addresses_per_user) if addresses_per_user else 0
        }

    # 3. Análisis de Salud de la Colección 'services'
    # (Se puede añadir una lógica similar para servicios, variantes, etc. si es necesario)
    
    return summary
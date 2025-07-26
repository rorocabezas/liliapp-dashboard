# backend/services/firestore_service.py

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import pandas as pd
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

def get_acquisition_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Calcula todos los KPIs relacionados con la adquisición de usuarios."""
    db = get_db_client()
    users_ref = db.collection('users')
    
    query = users_ref.where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    user_docs = list(query.stream())
    
    if not user_docs:
        return {"new_users_count": 0, "onboarding_rate": 0, "rut_validation_rate": 0, "channel_distribution": {}, "region_distribution": {}}

    total_new_users = len(user_docs)
    onboarding_completed_count = sum(1 for doc in user_docs if doc.to_dict().get('onboardingCompleted'))
    
    channel_counts = {}
    for doc in user_docs:
        source = doc.to_dict().get('acquisitionInfo', {}).get('source', 'Desconocido')
        channel_counts[source] = channel_counts.get(source, 0) + 1
    
    user_ids = [doc.id for doc in user_docs]
    rut_validated_count, region_counts = 0, {}
    for i in range(0, len(user_ids), 30):
        batch_ids, profile_paths = user_ids[i:i+30], []
        profile_paths = [f'users/{uid}/customer_profiles/main' for uid in batch_ids]
        profiles_query = db.collection_group('customer_profiles').where(filter=FieldFilter('__name__', 'in', profile_paths))
        for profile in profiles_query.stream():
            profile_data = profile.to_dict()
            if profile_data.get('rutVerified'): rut_validated_count += 1
            region = profile_data.get('primaryAddressRegion', 'Sin Región')
            region_counts[region] = region_counts.get(region, 0) + 1
            
    return {
        "new_users_count": total_new_users,
        "onboarding_rate": (onboarding_completed_count / total_new_users) * 100 if total_new_users > 0 else 0,
        "rut_validation_rate": (rut_validated_count / total_new_users) * 100 if total_new_users > 0 else 0,
        "channel_distribution": channel_counts, "region_distribution": region_counts
    }

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
    
    services_ref = db.collection('services').order_by('stats.purchaseCount', direction=firestore.Query.DESCENDING).limit(5)
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

    orders_df = pd.DataFrame([doc.to_dict() for doc in all_orders_docs])
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
# ===             FUNCIONES GENÉRICAS DE CRUD                     ===
# ===================================================================

def get_all_documents(collection_name: str) -> List[Dict[str, Any]]:
    """Obtiene todos los documentos de una colección."""
    db = get_db_client()
    docs = db.collection(collection_name).stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]

def get_document_by_id(collection_name: str, doc_id: str) -> Dict[str, Any]:
    """Obtiene un único documento por su ID."""
    db = get_db_client()
    doc_ref = db.collection(collection_name).document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        return {**doc.to_dict(), "id": doc.id}
    return None

def update_document(collection_name: str, doc_id: str, data: Dict[str, Any]):
    """Actualiza un documento en una colección."""
    db = get_db_client()
    db.collection(collection_name).document(doc_id).update(data)

def create_document(collection_name: str, data: Dict[str, Any]) -> str:
    """Crea un nuevo documento en una colección y devuelve su ID."""
    db = get_db_client()
    # Firestore genera un ID automático si no se especifica
    doc_ref = db.collection(collection_name).document()
    doc_ref.set(data)
    return doc_ref.id
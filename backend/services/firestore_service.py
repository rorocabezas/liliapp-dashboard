# backend/services/firestore_service.py

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from firebase_admin import firestore 
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

# ===================================================================
# ===               HELPER & UTILITY FUNCTIONS                    ===
# ===================================================================

def get_db_client():
    """
    Obtiene el cliente de Firestore de forma segura después de la inicialización.
    """
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
    
    # KPI: Nuevos Usuarios
    users_query = db.collection('users').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    new_users_count = len(list(users_query.stream()))

    # KPI: Ticket Promedio (AOV) y Datos de Ventas
    orders_query = db.collection('orders').where(filter=FieldFilter('status', '==', 'completed')).where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    orders_docs = list(orders_query.stream())
    
    total_revenue = sum(doc.to_dict().get('total', 0) for doc in orders_docs)
    completed_orders_count = len(orders_docs)
    aov_clp = total_revenue / completed_orders_count if completed_orders_count > 0 else 0

    # KPI: Tasa de Conversión de Carrito
    conversion_rate = get_cart_abandonment_rate(start_date, end_date, return_conversion=True)

    # Datos para el Gráfico de Series de Tiempo
    if orders_docs:
        sales_data = [{'date': doc.to_dict()['createdAt'], 'sales': doc.to_dict()['total']} for doc in orders_docs]
        df = pd.DataFrame(sales_data)
        df['date'] = pd.to_datetime(df['date']).dt.date
        daily_sales = df.groupby('date')['sales'].sum().reset_index()
        time_series = {"dates": [d.strftime('%Y-%m-%d') for d in daily_sales['date']], "sales": daily_sales['sales'].tolist()}
    else:
        time_series = {"dates": [], "sales": []}

    return {
        "new_users": new_users_count,
        "aov_clp": aov_clp,
        "conversion_rate": round(conversion_rate, 2),
        "time_series_data": time_series
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
    
    # Consulta de perfiles en lotes para KPIs de RUT y Región
    user_ids = [doc.id for doc in user_docs]
    rut_validated_count = 0
    region_counts = {}
    
    for i in range(0, len(user_ids), 30):
        batch_ids = user_ids[i:i+30]
        profile_paths = [f'users/{uid}/customer_profiles/main' for uid in batch_ids]
        profiles_query = db.collection_group('customer_profiles').where(filter=FieldFilter('__name__', 'in', profile_paths))
        
        for profile in profiles_query.stream():
            profile_data = profile.to_dict()
            if profile_data.get('rutVerified'):
                rut_validated_count += 1
            region = profile_data.get('primaryAddressRegion', 'Sin Región')
            region_counts[region] = region_counts.get(region, 0) + 1
            
    return {
        "new_users_count": total_new_users,
        "onboarding_rate": (onboarding_completed_count / total_new_users) * 100 if total_new_users > 0 else 0,
        "rut_validation_rate": (rut_validated_count / total_new_users) * 100 if total_new_users > 0 else 0,
        "channel_distribution": channel_counts,
        "region_distribution": region_counts
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
    
    # Lógica de servicios más vendidos (depende de un contador denormalizado)
    services_ref = db.collection('services').order_by('stats.purchaseCount', direction=firestore.Query.DESCENDING).limit(5)
    top_services = [{"name": doc.to_dict().get('name'), "purchases": doc.to_dict().get('stats', {}).get('purchaseCount', 0)} for doc in services_ref.stream()]

    return {
        "aov_clp": aov_clp,
        "purchase_frequency": purchase_frequency,
        "payment_method_distribution": payment_counts,
        "abandonment_rate": abandonment_rate,
        "service_performance": top_services
    }


def get_cart_abandonment_rate(start_date, end_date, return_conversion=False):
    """Calcula la tasa de abandono o conversión de carritos."""
    db = get_db_client()
    carts_ref = db.collection('carts').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    all_carts = list(carts_ref.stream())
    
    if not all_carts:
        return 0
        
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

    # --- 1. OBTENER TODAS LAS ÓRDENES DEL PERÍODO ---
    # Necesitamos todas, no solo las completadas, para calcular la tasa de cancelación.
    orders_query = db.collection('orders').where(
        filter=FieldFilter('createdAt', '>=', start_date)
    ).where(
        filter=FieldFilter('createdAt', '<=', end_date)
    )
    all_orders_docs = list(orders_query.stream())
    
    if not all_orders_docs:
        return {
            "cancellation_rate": 0, "avg_cycle_time_days": 0, "avg_rating": 0,
            "orders_by_commune": {}, "orders_by_hour": {}
        }

    # --- 2. CÁLCULO DE KPIS GENERALES ---
    total_orders = len(all_orders_docs)
    cancelled_orders = sum(1 for doc in all_orders_docs if doc.to_dict().get('status') == 'cancelled')
    cancellation_rate = (cancelled_orders / total_orders) * 100 if total_orders > 0 else 0

    # --- 3. PROCESAMIENTO DE ÓRDENES COMPLETADAS ---
    completed_orders_docs = [doc for doc in all_orders_docs if doc.to_dict().get('status') == 'completed']
    
    # Tiempo Promedio de Ciclo (de pagado a completado)
    cycle_times_in_seconds = []
    for doc in completed_orders_docs:
        history = doc.to_dict().get('statusHistory', [])
        timestamps = {item['status']: item['timestamp'] for item in history}
        if 'paid' in timestamps and 'completed' in timestamps:
            duration = timestamps['completed'] - timestamps['paid']
            cycle_times_in_seconds.append(duration.total_seconds())
    
    avg_cycle_time_seconds = sum(cycle_times_in_seconds) / len(cycle_times_in_seconds) if cycle_times_in_seconds else 0
    avg_cycle_time_days = avg_cycle_time_seconds / (24 * 3600)

    # Satisfacción Promedio
    ratings = [doc.to_dict().get('rating', {}).get('stars', 0) for doc in completed_orders_docs if doc.to_dict().get('rating')]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0

    # Distribución por Comuna (de órdenes completadas)
    commune_counts = {}
    for doc in completed_orders_docs:
        commune = doc.to_dict().get('serviceAddress', {}).get('commune', 'Desconocida')
        commune_counts[commune] = commune_counts.get(commune, 0) + 1

    # --- 4. HORARIOS PREFERIDOS (basado en todas las órdenes) ---
    orders_by_hour = [0] * 24 # Una lista para contar órdenes en cada hora del día
    for doc in all_orders_docs:
        created_at = doc.to_dict().get('createdAt')
        if created_at:
            hour = created_at.hour
            orders_by_hour[hour] += 1
            
    return {
        "cancellation_rate": cancellation_rate,
        "avg_cycle_time_days": avg_cycle_time_days,
        "avg_rating": avg_rating,
        "orders_by_commune": commune_counts,
        "orders_by_hour": orders_by_hour
    }


# ===================================================================
# ===       FUNCIONES PARA LA PÁGINA DE RETENCION Y LEALTAD   ===
# ===================================================================


def get_retention_kpis(period_end_date: datetime) -> Dict[str, Any]:
    """
    Calcula KPIs clave de retención y lealtad.
    El análisis de cohortes y LTV se basa en todos los datos hasta la fecha de fin.
    """
    db = get_db_client()

    # --- 1. OBTENER TODOS LOS USUARIOS Y ÓRDENES ---
    # Para estos KPIs, necesitamos todos los datos históricos hasta la fecha de fin.
    all_users_docs = list(db.collection('users').where(filter=FieldFilter('createdAt', '<=', period_end_date)).stream())
    all_orders_docs = list(db.collection('orders').where(filter=FieldFilter('status', '==', 'completed')).where(filter=FieldFilter('createdAt', '<=', period_end_date)).stream())

    if not all_users_docs:
        return {"mau": 0, "ltv_clp": 0, "repurchase_rate": 0, "cohort_data": None}

    # --- 2. USUARIOS ACTIVOS MENSUALES (MAU) ---
    # Usuarios que han iniciado sesión en los últimos 30 días desde period_end_date
    thirty_days_ago = period_end_date - timedelta(days=30)
    mau_query = db.collection('users').where(filter=FieldFilter('lastLoginAt', '>=', thirty_days_ago)).where(filter=FieldFilter('lastLoginAt', '<=', period_end_date))
    mau_count = len(list(mau_query.stream()))

    # --- 3. LTV Y TASA DE RECOMPRA ---
    if all_orders_docs:
        orders_df = pd.DataFrame([doc.to_dict() for doc in all_orders_docs])
        
        # LTV Simplificado: Gasto total / número de clientes únicos
        total_revenue = orders_df['total'].sum()
        distinct_customers = orders_df['customerId'].nunique()
        ltv_clp = total_revenue / distinct_customers if distinct_customers > 0 else 0
        
        # Tasa de Recompra
        customer_order_counts = orders_df.groupby('customerId').size()
        repeat_customers = (customer_order_counts > 1).sum()
        total_customers_with_orders = len(customer_order_counts)
        repurchase_rate = (repeat_customers / total_customers_with_orders) * 100 if total_customers_with_orders > 0 else 0
    else:
        ltv_clp = 0
        repurchase_rate = 0

    # --- 4. ANÁLISIS DE COHORTES DE RETENCIÓN ---
    # Necesitamos las fechas de registro de los usuarios y las fechas de sus órdenes
    users_df = pd.DataFrame([{'userId': doc.id, 'signup_month': pd.to_datetime(doc.to_dict()['createdAt']).to_period('M')} for doc in all_users_docs])
    if all_orders_docs:
        orders_df['order_month'] = pd.to_datetime(orders_df['createdAt']).to_period('M')
        
        # Unimos los dataframes para tener la fecha de registro y la fecha de cada orden en la misma fila
        df_merged = pd.merge(orders_df, users_df, left_on='customerId', right_on='userId', how='left')
        df_merged.dropna(subset=['signup_month'], inplace=True) # Eliminar órdenes de usuarios sin fecha de registro
        
        # Creamos la matriz de cohortes
        def get_month_diff(start, end):
            return (end.year - start.year) * 12 + (end.month - start.month)
            
        df_merged['cohort_index'] = df_merged.apply(lambda row: get_month_diff(row['signup_month'], row['order_month']), axis=1)
        cohort_data = df_merged.groupby(['signup_month', 'cohort_index'])['customerId'].nunique().reset_index()
        cohort_counts = cohort_data.pivot_table(index='signup_month', columns='cohort_index', values='customerId')
        
        # Calculamos los porcentajes de retención
        cohort_sizes = cohort_counts.iloc[:, 0]
        retention_matrix = cohort_counts.divide(cohort_sizes, axis=0) * 100
        
        # Formateamos para el frontend
        retention_matrix.index = retention_matrix.index.strftime('%Y-%m')
        cohort_data_for_frontend = retention_matrix.round(2).fillna(0).to_dict('split')
    else:
        cohort_data_for_frontend = None

    return {
        "mau": mau_count,
        "ltv_clp": ltv_clp,
        "repurchase_rate": repurchase_rate,
        "cohort_data": cohort_data_for_frontend
    }


# ===================================================================
# ===       FUNCIONES PARA LA PÁGINA DE SEGMENTACION Y MARKETING   ===
# ===================================================================

def get_rfm_segmentation(period_end_date: datetime) -> Dict[str, Any]:
    """
    Realiza un análisis RFM completo para segmentar a los clientes.
    """
    db = get_db_client()

    # --- 1. OBTENER TODAS LAS ÓRDENES COMPLETADAS HASTA LA FECHA ---
    orders_query = db.collection('orders').where(
        filter=FieldFilter('status', '==', 'completed')
    ).where(
        filter=FieldFilter('createdAt', '<=', period_end_date)
    )
    all_orders_docs = list(orders_query.stream())

    if not all_orders_docs:
        return {"segment_distribution": {}, "sample_customers": {}}

    orders_df = pd.DataFrame([doc.to_dict() for doc in all_orders_docs])
    orders_df['createdAt'] = pd.to_datetime(orders_df['createdAt'])

    # --- 2. CALCULAR RECENCIA, FRECUENCIA Y VALOR MONETARIO ---
    snapshot_date = period_end_date + timedelta(days=1)
    
    rfm_df = orders_df.groupby('customerId').agg({
        'createdAt': lambda date: (snapshot_date - date.max()).days, # Recencia
        'id': 'count', # Frecuencia
        'total': 'sum' # Monetario
    })
    
    rfm_df.rename(columns={'createdAt': 'recency', 'id': 'frequency', 'total': 'monetary'}, inplace=True)

    # --- 3. ASIGNAR PUNTAJES RFM (QUANTILES) ---
    # Dividimos a los clientes en 4 grupos (cuartiles) para cada métrica
    # Para Recencia, menos días es mejor (puntaje más alto)
    rfm_df['R_score'] = pd.qcut(rfm_df['recency'], 4, labels=[4, 3, 2, 1])
    # Para Frecuencia y Monetario, más es mejor
    rfm_df['F_score'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4])
    rfm_df['M_score'] = pd.qcut(rfm_df['monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4])

    # --- 4. CREAR SEGMENTOS BASADOS EN PUNTAJES ---
    rfm_df['RFM_score'] = rfm_df['R_score'].astype(str) + rfm_df['F_score'].astype(str) + rfm_df['M_score'].astype(str)
    
    # Definimos los segmentos basados en patrones de puntajes RFM
    segment_map = {
        r'[3-4][3-4][3-4]': '🏆 Campeones',
        r'[3-4][1-2][1-4]': '💖 Clientes Leales',
        r'[1-2][3-4][3-4]': '😮 En Riesgo',
        r'[1-2][1-2][1-2]': '❄️ Hibernando',
        r'4[1-4][1-4]': '✨ Nuevos Clientes',
        r'[1-2][1-4][3-4]': '💸 Grandes Gastadores (Inactivos)'
    }
    
    rfm_df['segment'] = rfm_df['RFM_score'].replace(segment_map, regex=True)
    rfm_df['segment'] = rfm_df.apply(lambda row: 'Otros' if row['segment'].startswith(('1','2','3','4')) else row['segment'], axis=1)

    # --- 5. PREPARAR DATOS PARA EL FRONTEND ---
    segment_distribution = rfm_df['segment'].value_counts().to_dict()
    
    # Obtenemos una muestra de 5 clientes para cada segmento
    sample_customers = {}
    for segment in rfm_df['segment'].unique():
        sample_df = rfm_df[rfm_df['segment'] == segment].head(5)
        sample_customers[segment] = sample_df.reset_index().to_dict('records')

    return {
        "segment_distribution": segment_distribution,
        "sample_customers": sample_customers
    }

# ===================================================================
# ===        PLACEHOLDERS PARA FUTURAS PÁGINAS                   ===
# ===================================================================



def get_retention_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    # TODO: Implementar la lógica para KPIs de retención
    # (Tasa de recompra, LTV, análisis de cohortes)
    return {"message": "Datos de retención no implementados"}
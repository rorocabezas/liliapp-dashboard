# backend/services/firestore_service.py
import pandas as pd
import traceback
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from concurrent.futures import ThreadPoolExecutor
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
    orders_query = db.collection('pedidos').where(filter=FieldFilter('status', '==', 'completed')).where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
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
def get_basic_pedidos_kpis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """
    KPIs básicos para la colección 'pedidos':
    - Total de pedidos
    - Pedidos por estado
    - Monto total vendido
    - Pedidos por cliente
    - Métodos de pago
    - Pedidos por comuna
    - Calificación promedio
    """
    db = get_db_client()
    pedidos_query = db.collection('pedidos').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
    pedidos_docs = [doc.to_dict() for doc in pedidos_query.stream()]
    result = {
        "total_pedidos": len(pedidos_docs),
        "pedidos_por_estado": {},
        "monto_total": 0,
        "pedidos_por_cliente": {},
        "metodos_pago": {},
        "pedidos_por_comuna": {},
        "calificacion_promedio": 0
    }
    if not pedidos_docs:
        return result
    import pandas as pd
    df = pd.DataFrame(pedidos_docs)
    # Pedidos por estado
    if 'status' in df.columns:
        result["pedidos_por_estado"] = df['status'].value_counts().to_dict()
    # Monto total vendido
    if 'total' in df.columns:
        result["monto_total"] = df['total'].sum()
    # Pedidos por cliente
    if 'customerId' in df.columns:
        result["pedidos_por_cliente"] = df['customerId'].value_counts().to_dict()
    # Métodos de pago
    if 'paymentDetails' in df.columns:
        def get_tipo_pago(x):
            if isinstance(x, dict):
                return x.get('type', 'Desconocido')
            return 'Desconocido'
        df['metodo_pago'] = df['paymentDetails'].apply(get_tipo_pago)
        result["metodos_pago"] = df['metodo_pago'].value_counts().to_dict()
    # Pedidos por comuna
    if 'serviceAddress' in df.columns:
        def get_comuna(sa):
            if isinstance(sa, dict):
                return sa.get('commune', 'Desconocida')
            return 'Desconocida'
        df['comuna'] = df['serviceAddress'].apply(get_comuna)
        result["pedidos_por_comuna"] = df['comuna'].value_counts().to_dict()
    # Calificación promedio
    if 'rating' in df.columns:
        def get_stars(r):
            if isinstance(r, dict):
                return r.get('stars')
            return None
        ratings = df['rating'].dropna().apply(get_stars)
        ratings = ratings.dropna().astype(float)
        if not ratings.empty:
            result["calificacion_promedio"] = ratings.mean()
    return result
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
    orders_query = db.collection('pedidos').where(filter=FieldFilter('createdAt', '>=', start_date)).where(filter=FieldFilter('createdAt', '<=', end_date))
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
    try:
        # --- Obtener pedidos completados en el rango ---
        all_orders_docs = _get_completed_orders_in_range(start_date, end_date)
        if not all_orders_docs:
            return {
                "retention_30d": 0,
                "clv": 0,
                "mau": 0,
                "repurchase_rate": 0,
                "avg_orders_by_commune": {},
                "retention_cohorts": pd.DataFrame(),
                "rfm_segments": pd.DataFrame(),
                "referred_pct": 0
            }

        df_orders = pd.DataFrame(all_orders_docs)
        # --- CLV ---
        total_revenue = df_orders['total'].sum() if 'total' in df_orders.columns else 0
        distinct_customers = df_orders['customerId'].nunique() if 'customerId' in df_orders.columns else 0
        clv = total_revenue / distinct_customers if distinct_customers > 0 else 0

        # --- Tasa de Recompra ---
        customer_order_counts = df_orders.groupby('customerId').size() if 'customerId' in df_orders.columns else pd.Series()
        repeat_customers = (customer_order_counts > 1).sum() if not customer_order_counts.empty else 0
        repurchase_rate = (repeat_customers / distinct_customers) * 100 if distinct_customers > 0 else 0

        # --- Retención 30 días ---
        db = get_db_client()
        users_query = db.collection('users').stream()
        users = {doc.id: doc.to_dict() for doc in users_query}
        retention_30d = 0
        if 'customerId' in df_orders.columns and 'createdAt' in df_orders.columns:
            user_first_order = df_orders.groupby('customerId')['createdAt'].min()
            user_signup = pd.Series({uid: u.get('createdAt') for uid, u in users.items()})
            user_signup = pd.to_datetime(user_signup, utc=True, errors='coerce')
            user_first_order = pd.to_datetime(user_first_order, utc=True, errors='coerce')
            retention_mask = (user_first_order - user_signup).dt.days <= 30
            retention_30d = retention_mask.sum() / len(user_signup) * 100 if len(user_signup) > 0 else 0

        # --- MAU (Usuarios Activos Mensuales) ---
        mau = 0
        user_last_login = pd.Series({uid: u.get('lastLoginAt') for uid, u in users.items()})
        user_last_login = pd.to_datetime(user_last_login, utc=True, errors='coerce')
        if not user_last_login.empty:
            month_start = pd.Timestamp(end_date.year, end_date.month, 1, tz='UTC')
            mau = (user_last_login >= month_start).sum()

        # --- Pedidos promedio por cliente por comuna ---
        avg_orders_by_commune = {}
        if 'customerId' in df_orders.columns and 'serviceAddress' in df_orders.columns:
            df_orders['commune'] = df_orders['serviceAddress'].apply(lambda sa: sa.get('commune', 'Desconocida') if isinstance(sa, dict) else 'Desconocida')
            commune_group = df_orders.groupby('commune')['customerId'].nunique()
            orders_group = df_orders.groupby('commune').size()
            avg_orders_by_commune = {commune: round(orders_group[commune] / commune_group[commune], 2) if commune_group[commune] > 0 else 0 for commune in commune_group.index}

        # --- Cohortes de Retención (simplificado) ---
        retention_cohorts = pd.DataFrame()
        if 'customerId' in df_orders.columns and 'createdAt' in df_orders.columns:
            df_orders['order_month'] = pd.to_datetime(df_orders['createdAt'], utc=True, errors='coerce').dt.to_period('M')
            cohort_table = df_orders.groupby(['customerId', 'order_month']).size().unstack(fill_value=0)
            retention_cohorts = cohort_table.apply(lambda x: x.gt(0).astype(int)).groupby(level=0).cumsum().groupby(level=0).max().value_counts().sort_index().to_frame('Clientes Retenidos')

        # --- Segmentación RFM (simplificado) ---
        rfm_segments = pd.DataFrame()
        if 'customerId' in df_orders.columns and 'createdAt' in df_orders.columns and 'total' in df_orders.columns:
            snapshot_date = end_date
            rfm_df = df_orders.groupby('customerId').agg(
                recency=('createdAt', lambda date: (snapshot_date - pd.to_datetime(date, utc=True).max()).days),
                frequency=('customerId', 'count'),
                monetary=('total', 'sum')
            ).reset_index()
            try:
                rfm_df['R_score'] = pd.qcut(rfm_df['recency'], 4, labels=[4, 3, 2, 1], duplicates='drop')
                rfm_df['F_score'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
                rfm_df['M_score'] = pd.qcut(rfm_df['monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
            except ValueError:
                rfm_df['R_score'] = 1; rfm_df['F_score'] = 1; rfm_df['M_score'] = 1
            rfm_df['RFM_score'] = rfm_df['R_score'].astype(str) + rfm_df['F_score'].astype(str) + rfm_df['M_score'].astype(str)
            segment_map = {
                r'[3-4][3-4][3-4]': '🏆 Campeones',
                r'[3-4][1-2][1-4]': '💖 Leales',
                r'[1-2][3-4][3-4]': '😮 En Riesgo',
                r'[1-2][1-2][1-2]': '❄️ Hibernando'
            }
            rfm_df['Segmento'] = rfm_df['RFM_score'].replace(segment_map, regex=True)
            rfm_segments = rfm_df.groupby('Segmento').size().reset_index(name='Clientes')

        # --- Programa de Referidos ---
        referred_pct = 0
        referred_count = sum(1 for u in users.values() if u.get('acquisitionInfo', {}).get('referredBy'))
        total_users = len(users)
        if total_users > 0:
            referred_pct = referred_count / total_users * 100

        return {
            "retention_30d": round(retention_30d, 2),
            "clv": round(clv, 2),
            "mau": int(mau),
            "repurchase_rate": round(repurchase_rate, 2),
            "avg_orders_by_commune": avg_orders_by_commune,
            "retention_cohorts": retention_cohorts,
            "rfm_segments": rfm_segments,
            "referred_pct": round(referred_pct, 2)
        }
    except Exception as e:
        print(f"ERROR en get_retention_kpis: {e}")
        import traceback
        traceback.print_exc()
        return {
            "retention_30d": 0,
            "clv": 0,
            "mau": 0,
            "repurchase_rate": 0,
            "avg_orders_by_commune": {},
            "retention_cohorts": pd.DataFrame(),
            "rfm_segments": pd.DataFrame(),
            "referred_pct": 0
        }


def get_rfm_segmentation(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Realiza un análisis RFM para segmentar a los clientes en un período de tiempo."""
    try:
        all_orders_docs = _get_completed_orders_in_range(start_date, end_date)
        if not all_orders_docs:
            return {
                "specialties_distribution": {},
                "region_distribution": {},
                "cohort_distribution": {},
                "ticket_distribution": {},
                "rfm_segments": {},
                "campaign_distribution": {},
                "referred_pct": 0,
                "churn_distribution": {},
                "segment_distribution": {},
                "sample_customers": {}
            }
        orders_df = pd.DataFrame(all_orders_docs)
        # Segmentación por especialidad
        specialties_dist = {}
        if 'specialties' in orders_df.columns:
            specialties_series = orders_df['specialties'].dropna().explode()
            specialties_dist = specialties_series.value_counts().to_dict()
        # Segmentación por región/comuna
        region_dist = {}
        if 'serviceAddress' in orders_df.columns:
            region_series = orders_df['serviceAddress'].apply(lambda sa: sa.get('region', 'Desconocida') if isinstance(sa, dict) else 'Desconocida')
            commune_series = orders_df['serviceAddress'].apply(lambda sa: sa.get('commune', 'Desconocida') if isinstance(sa, dict) else 'Desconocida')
            region_dist = region_series.value_counts().to_dict()
            for k, v in commune_series.value_counts().to_dict().items():
                region_dist[f"Comuna: {k}"] = v
        # Segmentación por antigüedad/cohorte
        cohort_dist = {}
        if 'createdAt' in orders_df.columns:
            cohort_series = pd.to_datetime(orders_df['createdAt'], utc=True, errors='coerce').dt.to_period('M').value_counts().sort_index()
            cohort_dist = {str(k): int(v) for k, v in cohort_series.items()}
        # Segmentación por ticket promedio
        ticket_dist = {}
        if 'total' in orders_df.columns and 'customerId' in orders_df.columns:
            ticket_avg = orders_df.groupby('customerId')['total'].mean()
            bins = [0, 20000, 50000, 100000, 500000, float('inf')]
            labels = ['<20K', '20K-50K', '50K-100K', '100K-500K', '>500K']
            ticket_groups = pd.cut(ticket_avg, bins=bins, labels=labels)
            ticket_dist = ticket_groups.value_counts().sort_index().to_dict()
        # Segmentación RFM
        snapshot_date = end_date
        rfm_df = orders_df.groupby('customerId').agg(
            recency=('createdAt', lambda date: (snapshot_date - pd.to_datetime(date, utc=True).max()).days),
            frequency=('customerId', 'count'),
            monetary=('total', 'sum')
        ).reset_index()
        try:
            rfm_df['R_score'] = pd.qcut(rfm_df['recency'], 4, labels=[4, 3, 2, 1], duplicates='drop')
            rfm_df['F_score'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
            rfm_df['M_score'] = pd.qcut(rfm_df['monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
        except ValueError:
            rfm_df['R_score'] = 1; rfm_df['F_score'] = 1; rfm_df['M_score'] = 1
        rfm_df['RFM_score'] = rfm_df['R_score'].astype(str) + rfm_df['F_score'].astype(str) + rfm_df['M_score'].astype(str)
        segment_map = {
            r'[3-4][3-4][3-4]': '🏆 Campeones',
            r'[3-4][1-2][1-4]': '💖 Leales',
            r'[1-2][3-4][3-4]': '😮 En Riesgo',
            r'[1-2][1-2][1-2]': '❄️ Hibernando'
        }
        rfm_df['Segmento'] = rfm_df['RFM_score'].replace(segment_map, regex=True)
        rfm_segments = rfm_df.groupby('Segmento').size().reset_index(name='Clientes')
        # Efectividad de campañas
        campaign_dist = {}
        if 'acquisitionInfo' in orders_df.columns:
            campaign_series = orders_df['acquisitionInfo'].apply(lambda ai: ai.get('campaign', 'Sin Campaña') if isinstance(ai, dict) else 'Sin Campaña')
            campaign_dist = campaign_series.value_counts().to_dict()
        # Programa de referidos
        db = get_db_client()
        users_query = db.collection('users').stream()
        users = {doc.id: doc.to_dict() for doc in users_query}
        referred_count = sum(1 for u in users.values() if u.get('acquisitionInfo', {}).get('referredBy'))
        total_users = len(users)
        referred_pct = referred_count / total_users * 100 if total_users > 0 else 0
        # Predicción de churn (simplificado)
        churn_dist = {}
        if 'customerId' in orders_df.columns and 'createdAt' in orders_df.columns:
            last_order = orders_df.groupby('customerId')['createdAt'].max()
            last_order_dt = pd.to_datetime(last_order, utc=True, errors='coerce')
            days_since_last = last_order_dt.apply(lambda d: (snapshot_date - d).days if pd.notnull(d) else None)
            churn_bins = [0, 30, 90, 180, 365, float('inf')]
            churn_labels = ['Activo (<30d)', 'En riesgo (30-90d)', 'Dormido (90-180d)', 'Hibernando (180-365d)', 'Perdido (>365d)']
            churn_groups = pd.cut(days_since_last, bins=churn_bins, labels=churn_labels)
            churn_dist = churn_groups.value_counts().sort_index().to_dict()
        # Segmentación RFM para muestra de clientes
        customers_docs = {doc.id: doc.to_dict() for doc in db.collection('customers').stream()}
        rfm_df['email'] = rfm_df['customerId'].map(lambda cid: customers_docs.get(cid, {}).get('email', 'N/A'))
        sample_customers = {
            segment: rfm_df[rfm_df['Segmento'] == segment].head(5)[['customerId', 'email', 'recency', 'frequency', 'monetary']].to_dict('records') 
            for segment in rfm_df['Segmento'].unique()
        }
        segment_distribution = rfm_df['Segmento'].value_counts().to_dict()
        return {
            "specialties_distribution": specialties_dist,
            "region_distribution": region_dist,
            "cohort_distribution": cohort_dist,
            "ticket_distribution": ticket_dist,
            "rfm_segments": rfm_segments,
            "campaign_distribution": campaign_dist,
            "referred_pct": round(referred_pct, 2),
            "churn_distribution": churn_dist,
            "segment_distribution": segment_distribution,
            "sample_customers": sample_customers
        }
    except Exception as e:
        print(f"ERROR en get_rfm_segmentation: {e}")
        import traceback
        traceback.print_exc()
        return {
            "specialties_distribution": {},
            "region_distribution": {},
            "cohort_distribution": {},
            "ticket_distribution": {},
            "rfm_segments": {},
            "campaign_distribution": {},
            "referred_pct": 0,
            "churn_distribution": {},
            "segment_distribution": {},
            "sample_customers": {}
        }

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

def get_document(collection_name, doc_id):
    """
    Obtiene un documento por ID en la colección especificada. Devuelve None si no existe.
    """
    db = get_db_client()
    doc_ref = db.collection(collection_name).document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

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


# --- Limpieza Quirúrgica ---

def _delete_collection_in_batches(coll_ref, batch_size, executor):
    """Función de ayuda para borrar una colección por lotes."""
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0
    
    futures = []
    for doc in docs:
        future = executor.submit(doc.reference.delete)
        futures.append(future)
        deleted += 1

    # Esperar a que todos los borrados del lote terminen
    for future in futures:
        future.result()

    if deleted >= batch_size:
        return _delete_collection_in_batches(coll_ref, batch_size, executor)
    return deleted

def clean_services_subcollections() -> dict:
    """
    Itera sobre todos los documentos en la colección 'services' y elimina
    recursivamente sus subcolecciones 'variants' y 'subcategories'.
    Esta es una operación intensiva y debe usarse con cuidado.
    """
    db = get_db_client()
    services_ref = db.collection('services')
    all_services = list(services_ref.stream())
    
    total_services_scanned = len(all_services)
    services_cleaned = 0
    total_subdocs_deleted = 0
    
    # Usamos un ThreadPoolExecutor para paralelizar las eliminaciones
    with ThreadPoolExecutor(max_workers=10) as executor:
        for service_doc in all_services:
            print(f"Limpiando servicio: {service_doc.id}...")
            cleaned_this_service = False
            
            # Limpiar subcolección 'variants'
            variants_ref = service_doc.reference.collection('variants')
            deleted_variants = _delete_collection_in_batches(variants_ref, 100, executor)
            if deleted_variants > 0:
                total_subdocs_deleted += deleted_variants
                cleaned_this_service = True
                print(f"  -> {deleted_variants} variantes eliminadas.")
            
            # Limpiar subcolección 'subcategories'
            subcategories_ref = service_doc.reference.collection('subcategories')
            deleted_subcats = _delete_collection_in_batches(subcategories_ref, 100, executor)
            if deleted_subcats > 0:
                total_subdocs_deleted += deleted_subcats
                cleaned_this_service = True
                print(f"  -> {deleted_subcats} subcategorías eliminadas.")
            
            if cleaned_this_service:
                services_cleaned += 1
                
    return {
        "services_scanned": total_services_scanned,
        "services_with_subcollections_cleaned": services_cleaned,
        "total_subdocuments_deleted": total_subdocs_deleted
    }

def clean_collection(collection_name: str) -> dict:
    """Elimina TODOS los documentos de una colección de nivel superior."""
    db = get_db_client()
    coll_ref = db.collection(collection_name)
    deleted_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            docs_batch = coll_ref.limit(100).stream()
            docs_to_delete = list(docs_batch)
            if not docs_to_delete: break
            futures = [executor.submit(doc.reference.delete) for doc in docs_to_delete]
            for future in futures: future.result()
            deleted_count += len(docs_to_delete)
            print(f"Borrados {deleted_count} documentos de '{collection_name}'...")
    return {"collection_cleaned": collection_name, "total_documents_deleted": deleted_count}


# --- Para creación de colecciones presupuesto personalizado en firestore ---
def initialize_quote_schema_with_samples() -> Dict[str, str]:
    """
    Crea las colecciones de presupuestos si no existen y añade un conjunto
    de documentos de ejemplo para demostrar el flujo completo.
    DEVUELVE LOS IDs de los documentos creados.
    """
    db = get_db_client()
    now = datetime.now()

    # --- IDs de ejemplo (simulamos un usuario y una categoría existentes) ---
    # En una demo real, podrías obtener un usuario y categoría reales de tu DB
    sample_customer_id = "sample_customer_123"
    sample_category_id = "sample_category_gasfiteria"

    # --- 1. Crear una Solicitud de Presupuesto (QuoteRequest) de ejemplo ---
    req_ref = db.collection('quote_requests').document()
    request_data = {
        "customerId": sample_customer_id,
        "categoryId": sample_category_id,
        "categoryName": "Gasfitería",
        "status": 'in_progress',
        "description": "Necesito reparar una fuga de agua debajo del lavaplatos. Adjunto foto.",
        "images": ["https://via.placeholder.com/150"],
        "quoteIds": [], # Se actualizará después
        "requestedAt": now
    }
    req_ref.set(request_data)
    
    # --- 2. Crear un Presupuesto (Quote) de ejemplo para esa solicitud ---
    quote_ref = db.collection('quotes').document()
    quote_data = {
        "requestId": req_ref.id,
        "customerId": sample_customer_id,
        "categoryId": sample_category_id,
        "professionalId": "sample_professional_456",
        "status": 'sent',
        "title": "Reparación de Fuga en Lavaplatos",
        "scopeDescription": "Se procederá a revisar la conexión del sifón, reemplazar sellos y verificar la presión del agua.",
        "lineItems": {
            "activities": [{"description": "Visita técnica y diagnóstico", "price": 20000}],
            "materials": [{"description": "Sello de goma para sifón", "quantity": 1, "price": 5000}]
        },
        "totalAmount": 25000,
        "validUntil": now + timedelta(days=7),
        "createdAt": now,
        "updatedAt": now
    }
    quote_ref.set(quote_data)
    
    # Actualizamos la solicitud con el ID del presupuesto creado
    req_ref.update({"quoteIds": [quote_ref.id]})
    
    # --- 3. Simular la aceptación y crear un Servicio Personalizado (CustomService) ---
    custom_service_ref = db.collection('custom_services').document()
    custom_service_data = {
        "quoteId": quote_ref.id,
        "customerId": sample_customer_id,
        "categoryId": sample_category_id,
        "name": f"Presupuesto Personalizado #{quote_ref.id[:5]}",
        "description": quote_data["scopeDescription"],
        "price": quote_data["totalAmount"],
        "details": {
            "activities": [item['description'] for item in quote_data['lineItems']['activities']],
            "materials": [item['description'] for item in quote_data['lineItems']['materials']]
        },
        "createdAt": now
    }
    custom_service_ref.set(custom_service_data)

    # --- 4. Simular la creación de la Orden ---
    order_ref = db.collection('orders').document()
    order_data = {
        "customerId": sample_customer_id,
        "orderType": 'custom_quote',
        "total": custom_service_data["price"],
        "status": "pending_payment",
        "createdAt": now,
        "updatedAt": now,
        "items": [{
            "customServiceId": custom_service_ref.id,
            "serviceName": custom_service_data["name"],
            "quantity": 1,
            "price": custom_service_data["price"],
            "lineItems": quote_data["lineItems"]
        }],
        # ... (otros campos de la orden como paymentDetails, etc. serían None al inicio)
    }
    order_ref.set(order_data)

    return {
        "quote_request_id": req_ref.id,
        "quote_id": quote_ref.id,
        "custom_service_id": custom_service_ref.id,
        "order_id": order_ref.id
    }
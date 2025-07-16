# dashboard/pages/2_🛒_Engagement_y_Conversión.py

import streamlit as st
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.auth import check_login


st.set_page_config(page_title="Conversión - LiliApp", layout="wide")
check_login() # Protege la página
render_menu() # Renderiza el menú

@st.cache_data(ttl=600)
def load_data(start_date, end_date):
    # TODO: Llamar al endpoint /api/v1/kpis/conversion
    return {
        "aov_clp": 58700,
        "abandonment_rate": 42.1,
        "payment_methods": {"Tarjeta": 68, "Webpay": 32}
    }

st.title("🛒 Engagement y Conversión")
st.markdown("Métricas clave del embudo de compra y comportamiento del usuario.")

if 'date_range' in st.session_state:
    start_date, end_date = st.session_state['date_range']
    data = load_data(start_date, end_date)
    
    # --- KPIs ---
    col1, col2 = st.columns(2)
    col1.metric("Ticket Promedio (CLP)", f"${data['aov_clp']:,}")
    col2.metric("Tasa de Abandono de Carrito", f"{data['abandonment_rate']}%")

    # --- Gráficos ---
    # TODO: Añadir un gráfico de los métodos de pago, etc.

else:
    st.warning("Selecciona un rango de fechas en la página principal.")
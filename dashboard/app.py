import streamlit as st
import requests

st.set_page_config(page_title="Dashboard LiliApp", layout="wide")

st.title("📊 Dashboard de Business Intelligence - LiliApp")

st.write("Bienvenido al centro de control de LiliApp. Selecciona un reporte del menú lateral.")

# --- Ejemplo de cómo llamar a la API ---
API_URL = "http://127.0.0.1:8000" # URL de tu API FastAPI local

st.subheader("Métrica de Ejemplo (desde la API)")

try:
    response = requests.get(f"{API_URL}/api/v1/kpis/new-users")
    if response.status_code == 200:
        data = response.json()
        st.metric(label="Nuevos Usuarios (últimos 30 días)", value=data.get("new_users_last_30_days"))
    else:
        st.error("No se pudo conectar con la API de BI.")
except requests.exceptions.ConnectionError:
    st.error("Error de conexión. Asegúrate de que el backend (FastAPI) esté corriendo.")
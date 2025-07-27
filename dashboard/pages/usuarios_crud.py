# dashboard/pages/usuarios_crud.py

import streamlit as st
import requests
import pandas as pd
from pathlib import Path
import sys

# --- Patrón de Importación y Autenticación ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from dashboard.auth import check_login
from dashboard.menu import render_menu

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Gestión de Clientes - LiliApp", layout="wide")
check_login()
render_menu()

# API URL base
API_URL = "http://127.0.0.1:8000/api/v1/crud"

# ===================================================================
# ===               FUNCIONES DE INTERACCIÓN CON API              ===
# ===================================================================

@st.cache_data(ttl=60)
def get_all_users():
    """Carga todos los documentos de la colección 'users'."""
    try:
        response = requests.get(f"{API_URL}/users")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al cargar usuarios: {e}")
        return []

@st.cache_data(ttl=30)
def get_user_details(user_id):
    """Obtiene todos los detalles de un usuario: perfil y direcciones."""
    if not user_id: return None, []
    try:
        profile_res = requests.get(f"{API_URL}/users/{user_id}/profile")
        addresses_res = requests.get(f"{API_URL}/users/{user_id}/addresses")
        
        profile = profile_res.json() if profile_res.ok else None
        addresses = addresses_res.json() if addresses_res.ok else []
        
        return profile, addresses
    except requests.exceptions.RequestException as e:
        st.error(f"Error al cargar detalles del usuario: {e}")
        return None, []

def handle_api_update(url, data, success_message):
    """Función genérica para manejar peticiones PUT."""
    try:
        response = requests.put(url, json=data)
        response.raise_for_status()
        st.toast(success_message, icon="✅")
        st.cache_data.clear() # Limpiamos caché para recargar datos
        st.rerun()
    except requests.exceptions.RequestException as e:
        error_detail = e.response.json().get('detail') if e.response else str(e)
        st.error(f"Error al actualizar: {error_detail}")

# ===================================================================
# ===               CUERPO PRINCIPAL DEL DASHBOARD                ===
# ===================================================================

st.title("👥 Gestión de Datos Maestros: Clientes")
st.markdown("Busca un cliente para ver y editar su información de perfil y direcciones.")

all_users = get_all_users()

if all_users:
    df_users = pd.DataFrame(all_users)
    
    # --- 1. VISTA MAESTRA: SELECCIÓN DE USUARIO ---
    st.subheader("Buscar y Seleccionar Cliente")
    
    customer_users = df_users[df_users['accountType'] == 'customer']
    user_options = {user['id']: user.get('email', 'Sin Email') for index, user in customer_users.iterrows()}
    
    selected_user_id = st.selectbox(
        "Busca un cliente por email:",
        options=[None] + list(user_options.keys()),
        format_func=lambda user_id: user_options.get(user_id, "Elige un cliente...")
    )

    st.markdown("---")

    # --- 2. VISTA DE DETALLE DEL USUARIO SELECCIONADO ---
    if selected_user_id:
        # Recuperamos los datos del usuario seleccionado del DataFrame principal
        user_data = df_users[df_users['id'] == selected_user_id].iloc[0].to_dict()
        profile_data, addresses_data = get_user_details(selected_user_id)
        
        if not profile_data:
            st.warning("Este usuario no tiene un perfil de cliente creado. Los datos pueden ser creados con el ETL de Órdenes.")
            st.stop()
            
        st.header(f"Editando Cliente: {profile_data.get('displayName', '')}")
        
        tab_user, tab_profile, tab_addresses, tab_orders = st.tabs(["🔑 Cuenta", "👤 Perfil", "📍 Direcciones", "🛍️ Órdenes"])
        
        # --- Pestaña de Cuenta (users) ---
        with tab_user:
            with st.form("user_form"):
                st.write("#### Datos de la Cuenta")
                email = st.text_input("Email", value=user_data.get("email", ""), key="user_email")
                phone = st.text_input("Teléfono", value=user_data.get("phone", ""), key="user_phone")
                status = st.selectbox("Estado de la Cuenta", options=["verified", "pending", "suspended"], index=["verified", "pending", "suspended"].index(user_data.get("accountStatus", "pending")), key="user_status")
                
                if st.form_submit_button("Guardar Cambios en Cuenta", use_container_width=True):
                    payload = {"email": email, "phone": phone, "accountStatus": status}
                    handle_api_update(f"{API_URL}/users/{selected_user_id}", payload, "Datos de la cuenta actualizados.")

        # --- Pestaña de Perfil (customer_profiles) ---
        with tab_profile:
            with st.form("profile_form"):
                st.write("#### Información del Perfil")
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    first_name = st.text_input("Nombre", value=profile_data.get("firstName", ""))
                    display_name = st.text_input("Nombre a Mostrar", value=profile_data.get("displayName", ""))
                with p_col2:
                    last_name = st.text_input("Apellido", value=profile_data.get("lastName", ""))
                    rut = st.text_input("RUT", value=profile_data.get("rut", ""))
                
                if st.form_submit_button("Guardar Cambios en Perfil", use_container_width=True):
                    payload = {"firstName": first_name, "lastName": last_name, "displayName": display_name, "rut": rut}
                    handle_api_update(f"{API_URL}/users/{selected_user_id}/profile", payload, "Perfil actualizado con éxito.")

        # --- Pestaña de Direcciones ---
        with tab_addresses:
            st.write("#### Direcciones Guardadas")
            if addresses_data:
                df_addresses = pd.DataFrame(addresses_data)
                st.dataframe(df_addresses, use_container_width=True, hide_index=True)
                # TODO: Implementar edición de direcciones con st.data_editor o un modal
            else:
                st.info("Este cliente no tiene direcciones guardadas.")
        
        # --- Pestaña de Órdenes ---
        with tab_orders:
            st.write("#### Historial de Órdenes")
            st.info("La visualización del historial de órdenes del cliente se implementará aquí.", icon="🚧")

else:
    st.warning("No se encontraron usuarios o hubo un error al cargar los datos.")
# dashboard/pages/usuarios_crud.py
import streamlit as st
import pandas as pd
import uuid

# --- Importaciones ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_customers, update_customer_fields, add_address, update_address

# --- Configuración de Página ---
st.set_page_config(page_title="Gestión de Clientes - LiliApp", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

# --- Funciones de Utilidad ---
@st.cache_data(ttl=60)
def load_customers_data():
    """Carga todos los clientes usando el api_client."""
    return get_customers() or []

def refresh_data(toast_message=""):
    if toast_message: st.toast(toast_message, icon="✅")
    st.cache_data.clear()
    st.rerun()

# --- Cuerpo Principal del Dashboard ---
st.title("👥 Gestión de Clientes (Modelo Desnormalizado)")
st.markdown("Administra la información de los clientes y sus direcciones anidadas.")

customers_data = load_customers_data()

if not customers_data:
    st.info("No hay clientes en la base de datos.")
    st.stop()

# --- Vista Maestro-Detalle ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Lista de Clientes")
    customer_map = {c['id']: c.get('displayName', c.get('email', 'N/A')) for c in customers_data}
    selected_customer_id = st.selectbox(
        "Selecciona un cliente:",
        options=[""] + list(customer_map.keys()),
        format_func=lambda cid: "Selecciona..." if not cid else customer_map.get(cid)
    )

with col2:
    if selected_customer_id:
        selected_customer = next((c for c in customers_data if c['id'] == selected_customer_id), None)
        
        if selected_customer:
            st.subheader(f"Detalles de: {selected_customer.get('displayName', 'Cliente sin nombre')}")
            
            tab_profile, tab_addresses = st.tabs(["📋 Perfil", "🏠 Direcciones"])

            with tab_profile:
                with st.form("edit_profile_form"):
                    st.write("#### Información Principal")
                    
                    email = st.text_input("Email (solo lectura)", value=selected_customer.get('email', ''), disabled=True)
                    phone = st.text_input("Teléfono", value=selected_customer.get('phone', ''))
                    
                    p_col1, p_col2 = st.columns(2)
                    firstName = p_col1.text_input("Nombre", value=selected_customer.get('firstName', ''))
                    lastName = p_col2.text_input("Apellido", value=selected_customer.get('lastName', ''))
                    
                    rut = st.text_input("RUT", value=selected_customer.get('rut', ''))
                    
                    if st.form_submit_button("Guardar Cambios en Perfil", use_container_width=True):
                        payload = {
                            "phone": phone,
                            "firstName": firstName,
                            "lastName": lastName,
                            "displayName": f"{firstName} {lastName}".strip(),
                            "rut": rut
                        }
                        res = update_customer_fields(selected_customer_id, payload)
                        if res: refresh_data("Perfil actualizado con éxito.")

            with tab_addresses:
                st.write("#### Direcciones Guardadas")
                st.caption("Puedes editar los datos directamente en la tabla. Los cambios se guardarán al presionar el botón.")

                addresses = selected_customer.get('addresses', [])
                
                if addresses:
                    # Usamos un data_editor para permitir la edición en la tabla
                    edited_addresses_df = st.data_editor(
                        pd.DataFrame(addresses),
                        key=f"editor_addresses_{selected_customer_id}",
                        use_container_width=True,
                        hide_index=True,
                        # Deshabilitamos la edición del ID para mantener la integridad
                        column_config={
                            "id": st.column_config.Column(disabled=True),
                            "isPrimary": st.column_config.CheckboxColumn(default=False)
                        }
                    )
                    
                    if st.button("Guardar Cambios en Direcciones", use_container_width=True, key=f"save_addr_{selected_customer_id}"):
                        # Convertimos el DataFrame editado de nuevo a una lista de diccionarios
                        updated_addresses_list = edited_addresses_df.to_dict('records')
                        
                        # Iteramos y llamamos a la API para cada dirección modificada
                        # Nota: st.data_editor no nos dice qué cambió, así que actualizamos todas.
                        # Para una optimización mayor, se podría comparar con el estado original.
                        with st.spinner("Guardando direcciones..."):
                            for address_payload in updated_addresses_list:
                                address_id = address_payload.get("id")
                                res = update_address(selected_customer_id, address_id, address_payload)
                            
                            # Si todo fue bien, refrescamos.
                            refresh_data("Direcciones actualizadas con éxito.")

                else:
                    st.info("Este cliente no tiene direcciones guardadas.")

                with st.expander("➕ Añadir Nueva Dirección"):
                    with st.form(f"add_address_form_{selected_customer_id}"):
                        a_col1, a_col2 = st.columns(2)
                        alias = a_col1.text_input("Alias (ej: Casa, Oficina)", value="Casa")
                        street = a_col2.text_input("Calle")
                        number = a_col1.text_input("Número")
                        commune = a_col2.text_input("Comuna")
                        region = a_col1.text_input("Región", value="Región Metropolitana")

                        if st.form_submit_button("Guardar Nueva Dirección", use_container_width=True):
                            if street and commune:
                                address_payload = {
                                    "id": f"addr_{uuid.uuid4().hex[:8]}", # ID único
                                    "alias": alias,
                                    "street": street,
                                    "number": number,
                                    "commune": commune,
                                    "region": region,
                                    "isPrimary": not addresses
                                }
                                res = add_address(selected_customer_id, address_payload)
                                if res: refresh_data("Dirección añadida con éxito.")
    else:
        st.info("Selecciona un cliente de la lista para ver sus detalles.")



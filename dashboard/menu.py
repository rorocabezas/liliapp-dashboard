import streamlit as st
from datetime import datetime, timedelta

# --- Constantes de Roles ---
# Definir roles como constantes mejora la legibilidad y previene errores de tipeo.
ADMIN_ROLE = "admin"
PROFESSIONAL_ROLE = "professional"
CUSTOMER_ROLE = "customer"

def _render_global_filters():
    """
    Función interna para renderizar y gestionar todos los filtros globales.
    Esto mantiene la función principal del menú más limpia.
    """
    st.markdown("---")
    st.header("Filtros Globales")

    # --- Filtro de Rango de Fechas ---
    # Si el rango de fechas no existe en la sesión, lo inicializamos como una tupla.
    if 'date_range' not in st.session_state:
        today = datetime.now()
        st.session_state['date_range'] = (today - timedelta(days=30), today)

    # El widget st.date_input con un valor de tupla, devuelve una tupla.
    date_range_tuple = st.date_input(
        "Selecciona un rango de fechas",
        value=st.session_state['date_range'],
        format="DD/MM/YYYY",
        key="global_date_range_picker"
    )

    # Actualizamos la sesión solo si el valor ha cambiado.
    # El widget puede devolver una tupla de 1 elemento mientras se está seleccionando.
    if len(date_range_tuple) == 2:
        if date_range_tuple != st.session_state.get('date_range'):
            st.session_state['date_range'] = date_range_tuple
            st.rerun() # Forzamos la recarga de la página para que los nuevos filtros se apliquen.

def render_menu():
    """
    Genera un menú dinámico en la barra lateral basado en el rol del usuario
    y oculta el menú por defecto de Streamlit.
    """
    if not st.session_state.get("authenticated"):
        return

    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] { display: none; }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        user_name = st.session_state.get("username", "Usuario")
        user_role = st.session_state.get("user_role", "Desconocido")
        
        st.write(f"Usuario: **{user_name}**")
        st.write(f"Rol: **:blue-background[{user_role.capitalize()}]**")
        st.markdown("---")

        # --- NAVEGACIÓN PRINCIPAL ---
        # Renombrar 'app.py' a 'Home.py' es una convención de Streamlit
        st.page_link("Home.py", label="Página Principal", icon="🏠")
        st.markdown("---")
        
        st.subheader("Análisis de Negocio")
        st.page_link("pages/adquisicion.py", label="Adquisición", icon="📈")
        st.page_link("pages/engagement.py", label="Conversión", icon="🛒")
        st.page_link("pages/operaciones.py", label="Operaciones", icon="⚙️")
        st.page_link("pages/retencion.py", label="Retención", icon="💖")
        st.page_link("pages/segmentacion.py", label="Segmentación", icon="🎯")
        #st.page_link("pages/salud_tienda.py", label="Salud de la Tienda", icon="🩺")
        st.markdown("---")

        st.subheader("Cargas de Datos ETL")
        st.page_link("pages/cargas.py", label="ETL Masivo", icon="⚙️")       
        st.page_link("pages/mapeo_jumpseller_a_servicio.py", label="Mapeo Jumpseller a Servicio", icon="🗺")
        st.page_link("pages/Mapeo_Jumpseller_a_Cliente.py", label="Mapeo Jumpseller a Cliente", icon="🗺️")
        st.page_link("pages/schema_initializer.py", label="Inicializador de Esquema", icon="🏗️")
        st.markdown("---")
        #st.page_link("pages/Mapeo_de_servicios.py", label="Mapeo de Servicios", icon="🛠️")
        #st.page_link("pages/Mapeo_de_ordenes.py", label="Mapeo de Ordenes", icon="🔄")
        #st.page_link("pages/Mapeo_Jumpseller_a_Usuario.py", label="Mapeo Jumpseller a Usuario", icon="🗺️")
        st.markdown("---")
        #st.page_link("pages/auditoria.py", label="Auditoría de Datos", icon="🔬")
        #st.page_link("pages/salud_firestore.py", label="Salud de Firestore", icon="🩺")
        

        st.subheader("Datos Maestros")
        #st.page_link("pages/servicios_crud.py", label="Servicios", icon="🛠️")
        #st.page_link("pages/usuarios_crud.py", label="Clientes", icon="👥")
        #st.markdown("---")      

        #st.subheader("Catálogo Jumpseller")
        #st.page_link("pages/catalogo_jumpseller.py", label="Explorador de API", icon="📦")
       
        # --- Llamada a la función de filtros ---
        _render_global_filters()
        
        # --- SECCIÓN DE ADMINISTRACIÓN (SOLO para Admins) ---
        if user_role == ADMIN_ROLE:
            st.markdown("---")
            st.subheader("Herramientas de Admin")
            st.page_link("pages/99_Admin_Tools.py", label="Gestión de Usuarios", icon="🛠️")
        
        # --- BOTÓN DE CERRAR SESIÓN ---
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.switch_page("Home.py") # Asegúrate que tu archivo principal se llame Home.py
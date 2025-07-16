# dashboard/menu.py
import streamlit as st

# Definimos los roles para mantener el código limpio y legible
ADMIN_ROLE = "admin"
PROFESSIONAL_ROLE = "professional"
CUSTOMER_ROLE = "customer" # Aunque los clientes no usarían este dashboard, es bueno definirlo

def render_menu():
    """
    Genera un menú dinámico en la barra lateral basado en el rol del usuario
    y oculta el menú por defecto de Streamlit.
    """
    # Si el usuario no está logueado, no mostramos nada.
    if not st.session_state.get("authenticated"):
        return

    # Oculta el menú por defecto que genera Streamlit a partir de la carpeta /pages
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        # Información del usuario en la parte superior
        user_name = st.session_state.get("username", "Usuario")
        user_role = st.session_state.get("user_role", "Desconocido")
        
        st.write(f"Usuario: **{user_name}**")
        st.write(f"Rol: **:blue-background[{user_role.capitalize()}]**")
        st.markdown("---")

        # --- NAVEGACIÓN PRINCIPAL (Común para todos) ---
        st.page_link("app.py", label="Página Principal", icon="🏠")
        
        st.subheader("Análisis de Negocio")
        st.page_link("pages/adquisicion.py", label="Adquisición", icon="📈")
        st.page_link("pages/engagement.py", label="Conversión", icon="🛒")
        st.page_link("pages/operaciones.py", label="Operaciones", icon="⚙️")
        st.page_link("pages/retencion.py", label="Retención", icon="💖")
        st.page_link("pages/segmentacion.py", label="Segmentación", icon="🎯")
       

        # --- SECCIÓN DE ADMINISTRACIÓN (SOLO para Admins) ---
        if user_role == ADMIN_ROLE:
            st.subheader("Herramientas de Admin")
            # Aquí podrías añadir páginas para gestionar usuarios, etc.
            st.page_link("pages/99_Admin_Tools.py", label="Gestión de Usuarios", icon="🛠️")
        
        # --- BOTÓN DE CERRAR SESIÓN ---
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Cerrar Sesión", use_container_width=True):
            # Limpiamos toda la sesión
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Usamos switch_page para una redirección limpia a la página de login
            st.switch_page("app.py")
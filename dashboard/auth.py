# dashboard/auth.py

import streamlit as st
import requests
from pathlib import Path

API_URL = "http://127.0.0.1:8000"

def handle_login(email, password):
    """
    Encapsula la lógica de llamada a la API para mantener el formulario limpio.
    """

    if not email or not password:
        st.warning("Por favor, ingresa tu email y contraseña.")
        return
    try:
        response = requests.post(f"{API_URL}/api/v1/auth/login", json={"email": email, "password": password})
        if response.status_code == 200:
            data = response.json()
            st.session_state['authenticated'] = True
            st.session_state['user_role'] = data.get("role", "customer")
            st.session_state['username'] = data.get("email", "Usuario")
            st.rerun()
        else:
            st.error(f"❌ {response.json().get('detail', 'Credenciales inválidas.')}")
    except requests.ConnectionError:
        st.error("🔌 Error de conexión con el servidor.")
    except Exception as e:
        st.error(f"Ocurrió un error inesperado: {e}")

def render_login_form():
    """
    Renderiza un formulario de login profesional, centrado y oculta el sidebar.
    """
    # Inyectamos CSS para una transformación visual completa
    st.markdown(
        """
        <style>
            /* Ocultar el menú de navegación generado por la carpeta /pages */
            [data-testid="stSidebarNav"] {
                display: none;
            }
            /* Ocultar la barra lateral completa en la página de login */
            [data-testid="stSidebar"] {
                display: none;
            }
            /* Estilos para el fondo y otros elementos */
            [data-testid="stAppViewContainer"] > .main {
                background-color: #F0F2F6;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .footer {
                position: fixed; left: 0; bottom: 0; width: 100%;
                background-color: transparent; color: #888; text-align: center; padding: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Layout centrado
    _, col2, _ = st.columns([1, 1.5, 1])
    with col2:
        logo_path = Path(__file__).parent / "assets" / "logo.png"
        if logo_path.exists():
            st.image(str(logo_path), width=120)
        
        st.title("LiliApp Dashboard")
        with st.form("login_form"):
            st.markdown("##### Inicia sesión para continuar")
            email_input = st.text_input("📧 Email", placeholder="tucorreo@liliapp.cl")
            password_input = st.text_input("🔑 Contraseña", type="password")
            st.markdown("")
            submitted = st.form_submit_button("Iniciar Sesión", type="primary", use_container_width=True)
            if submitted:
                handle_login(email_input, password_input)

    # Footer
    st.markdown('<div class="footer"><p>© 2024 LiliApp | Business Intelligence. Todos los derechos reservados.</p></div>', unsafe_allow_html=True)


def check_login():
    """
    Función principal de autenticación. Gestiona el estado de la UI (sidebar).
    """
    # Configuración inicial del sidebar, por defecto oculto
    st.set_page_config(initial_sidebar_state="collapsed")

    if not st.session_state.get('authenticated', False):
        render_login_form()
        st.stop()
    else:
        # Si está autenticado, nos aseguramos de que el fondo sea blanco para las páginas del dashboard
        st.markdown("""
            <style>
                [data-testid="stAppViewContainer"] > .main {background-color: white;}
            </style>
        """, unsafe_allow_html=True)
    return True
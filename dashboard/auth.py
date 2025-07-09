# dashboard/auth.py

import streamlit as st
import requests
import os

API_URL = "http://127.0.0.1:8000"  # La URL de tu backend

def render_login_form():
    """
    Renderiza un formulario de login centrado y limpio usando st.form.
    """
    
    # CSS Mínimo para el fondo y para ocultar elementos de Streamlit
    st.markdown(
        f"""
        <style>
            [data-testid="stAppViewContainer"] > .main {{
                background-color: #F0F2F6;
            }}
            [data-testid="stHeader"] {{visibility: hidden;}}
            [data-testid="stMainMenu"] {{visibility: hidden;}}
            footer {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True
    )

    # Usamos columnas para centrar el formulario en la página
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        # Título y logo fuera del formulario para un mejor layout
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "assets", "logo.png")
            st.image(logo_path, width=100)
        except Exception:
            st.error("No se pudo cargar el logo.")

        st.markdown("<h2 style='text-align: center;'>Acceso al Dashboard de BI</h2>", unsafe_allow_html=True)

        # Usamos st.form como el contenedor principal del login
        with st.form(key='login_form'):
            email = st.text_input(
                label='Email',
                placeholder="tucorreo@liliapp.cl"
            )
            password = st.text_input(
                label='Contraseña',
                type="password",
                placeholder="Ingresa tu contraseña"
            )
            
            # El botón de submit del formulario
            login_button = st.form_submit_button(
                'Iniciar Sesión',
                use_container_width=True,
                type="primary"
            )

            if login_button:
                if not email or not password:
                    st.warning("Por favor, ingresa tu email y contraseña.")
                else:
                    try:
                        # Llamada a la API de FastAPI
                        response = requests.post(
                            f"{API_URL}/api/v1/auth/login",
                            json={"email": email, "password": password}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state['authenticated'] = True
                            st.session_state['custom_token'] = data.get("custom_token")
                            st.session_state['user_uid'] = data.get("uid")
                            st.session_state['username'] = email
                            st.rerun()
                        else:
                            error_detail = response.json().get("detail", "Credenciales inválidas.")
                            st.error(f"❌ {error_detail}")

                    except requests.exceptions.ConnectionError:
                        st.error("🔌 Error de conexión. El servidor de backend no está disponible.")
                    except Exception as e:
                        st.error(f"Ocurrió un error inesperado: {e}")


def check_login():
    """
    Función principal de autenticación. Llama al formulario de login si es necesario.
    """
    if not st.session_state.get('authenticated', False):
        render_login_form()
        st.stop()
    else:
        # Resetea el color de fondo para las páginas autenticadas
        st.markdown("""
            <style>
                [data-testid="stAppViewContainer"] > .main {background-color: white;}
            </style>
        """, unsafe_allow_html=True)
    return True
# dashboard/styles.py
import streamlit as st

# ==========================================================
# ===         CONFIGURACIÓN DE ESTILOS Y COLORES         ===
# ==========================================================

# --- Paleta de Colores Corporativos (Estilo Material Design) ---
COLOR_PRIMARY = "#6200EE"   # Morado Intenso
COLOR_SECONDARY = "#03DAC6" # Teal/Turquesa
COLOR_SUCCESS = "#4CAF50"    # Verde
COLOR_WARNING = "#FF9800"    # Naranja
COLOR_DANGER = "#F44336"     # Rojo

# ==========================================================
# ===         INYECCIÓN DE CSS Y COMPONENTES             ===
# ==========================================================

def load_custom_css():
    """
    Carga el CSS avanzado para las tarjetas de métricas de alto impacto.
    """
    st.markdown(f"""
    <style>
        /* Contenedor principal de la tarjeta */
        div.metric-card-container {{
            background-color: var(--card-bg-color, #FFFFFF); /* Color de fondo */
            color: white; /* Color del texto */
            padding: 25px 20px;
            border-radius: 12px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1), 0 6px 6px rgba(0,0,0,0.15);
            position: relative; /* Contexto para el posicionamiento del ícono */
            overflow: hidden; /* Oculta el exceso del ícono de fondo */
            transition: transform 0.2s ease-in-out;
        }}
        div.metric-card-container:hover {{
            transform: translateY(-5px); /* Efecto de elevación al pasar el mouse */
        }}

        /* Pseudo-elemento para el ÍCONO de fondo */
        div.metric-card-container::after {{
            content: var(--icon-content, '❓'); /* El ícono se pasa como variable CSS */
            position: absolute;
            top: -10px;
            right: -20px;
            font-size: 100px; /* Tamaño gigante del ícono de fondo */
            font-weight: 900;
            color: rgba(255, 255, 255, 0.15); /* Color blanco semi-transparente */
            transform: rotate(20deg); /* Rotación ligera */
            z-index: 1; /* Detrás del contenido principal */
        }}

        /* Contenedor del contenido para asegurar que esté sobre el ícono de fondo */
        div.metric-card-content {{
            position: relative;
            z-index: 2;
        }}

        /* Título de la métrica */
        p.metric-card-title {{
            font-size: 16px;
            font-weight: 500;
            margin: 0;
            opacity: 0.9;
        }}
        
        /* Valor principal de la métrica */
        p.metric-card-value {{
            font-size: 42px;
            font-weight: 700;
            margin: 5px 0 0 0;
            line-height: 1;
        }}
    </style>
    """, unsafe_allow_html=True)

def metric_card(icon: str, title: str, value: str, background_color: str, key: str):
    """
    Renderiza una tarjeta de métrica con el ícono de fondo.
    """
    st.markdown(
        f"""
        <div class="metric-card-container" style="--card-bg-color: {background_color}; --icon-content: '{icon}';" key="{key}">
            <div class="metric-card-content">
                <p class="metric-card-title">{title}</p>
                <p class="metric-card-value">{value}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
# dashboard/app.py
import streamlit as st
from pathlib import Path
import sys

# --- Patrón de Importación Robusto ---
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from dashboard.auth import check_login
from dashboard.menu import render_menu
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Dashboard LiliApp", layout="wide")

check_login()
render_menu() 

# --- CUERPO PRINCIPAL DEL DASHBOARD ---
st.title("📊 Dashboard de Business Intelligence - LiliApp")
st.markdown("### Resumen Ejecutivo")

st.info("Utiliza el menú de navegación para explorar los reportes. Los filtros globales se aplican en todas las páginas.", icon="ℹ️")
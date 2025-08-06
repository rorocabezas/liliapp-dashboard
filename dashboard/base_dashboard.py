# dashboard/base_dashboard.py
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional

from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_kpis
from dashboard.styles import load_custom_css

class BaseDashboard:
    """Clase base abstracta para todos los dashboards de BI."""
    
    def __init__(self, page_title: str, page_icon: str, endpoint: str):
        self.page_title = page_title
        self.page_icon = page_icon
        self.endpoint = endpoint # 'acquisition', 'engagement', etc.
        self.data: Optional[Dict[str, Any]] = None
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None

    def setup_page(self) -> None:
        """Configuración inicial y común para todas las páginas."""
        st.set_page_config(
            page_title=f"{self.page_title} - LiliApp BI", 
            layout="wide", 
            initial_sidebar_state="expanded"
        )
        check_login()
        render_menu()
        load_custom_css()
        st.title(f"{self.page_icon} Análisis de {self.page_title}")

    def validate_date_range(self) -> bool:
        """Valida y procesa el rango de fechas global."""
        if 'date_range' not in st.session_state or len(st.session_state.date_range) != 2:
            st.warning("⚠️ El rango de fechas no está disponible."); return False
        self.start_date, self.end_date = st.session_state.date_range
        return True

    @st.cache_data(ttl=300)
    def load_data(_self, start_date_str: str, end_date_str: str) -> Optional[Dict[str, Any]]:
        """Carga los datos de la API. Reutilizable para todos los dashboards."""
        return get_kpis(_self.endpoint, start_date_str, end_date_str)
        
    def run(self) -> None:
        """Método principal de ejecución."""
        self.setup_page()
        
        if not self.validate_date_range(): st.stop()
            
        start_str = self.start_date.strftime('%Y-%m-%d')
        end_str = self.end_date.strftime('%Y-%m-%d')
        
        self.data = self.load_data(start_str, end_str)

        if not self.data:
            st.error("❌ No se pudieron cargar los datos para el análisis."); st.stop()
        
        start_display = self.start_date.strftime('%d/%m/%Y')
        end_display = self.end_date.strftime('%d/%m/%Y')
        st.subheader(f"📊 Resumen del Período: {start_display} al {end_display}")
        
        # Llama a los métodos de renderizado que serán definidos por las clases hijas
        self.render_kpi_cards()
        self.render_visualizations()

    # --- Métodos abstractos que las clases hijas DEBEN implementar ---
    def render_kpi_cards(self) -> None:
        raise NotImplementedError("Este método debe ser implementado por la clase hija.")
    
    def render_visualizations(self) -> None:
        raise NotImplementedError("Este método debe ser implementado por la clase hija.")
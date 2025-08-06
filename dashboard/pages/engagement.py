# dashboard/pages/engagement.py
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, List

# --- Importaciones de Módulos del Proyecto ---
from dashboard.base_dashboard import BaseDashboard
from dashboard.styles import metric_card, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING

class EngagementDashboard(BaseDashboard):
    """
    Dashboard de engagement y conversión que hereda de la clase base.
    """
    
    def __init__(self):
        super().__init__(page_title="Engagement y Conversión", page_icon="🛒", endpoint="engagement")
    
    def render_kpi_cards(self) -> None:
        """Renderiza las tarjetas de KPIs específicas para Engagement."""
        cols = st.columns(3)
        with cols[0]:
            metric_card("🛒", "Tasa de Abandono", f"{self.data.get('abandonment_rate', 0)}%", COLOR_WARNING, "card1")
        with cols[1]:
            metric_card("💰", "Ticket Promedio (AOV)", f"${self.data.get('aov_clp', 0):,.0f} CLP", COLOR_PRIMARY, "card2")
        with cols[2]:
            metric_card("🔁", "Frec. de Compra", f"{self.data.get('purchase_frequency', 0)} órd/cliente", COLOR_SECONDARY, "card3")
        st.markdown("<br>", unsafe_allow_html=True)

    def render_visualizations(self) -> None:
        """Renderiza las visualizaciones específicas para Engagement."""
        col1, col2 = st.columns(2)
        with col1:
            self._render_payment_pie_chart()
        with col2:
            # --- CAMBIO: Llamamos a la nueva función de renderizado ---
            self._render_top_categories_chart()

    def _render_payment_pie_chart(self) -> None:
        """Renderiza un gráfico de torta interactivo para los métodos de pago."""
        st.subheader("💳 Distribución de Métodos de Pago")
        payment_dist = self.data.get('payment_method_distribution', {})
        if not payment_dist:
            st.info("ℹ️ No hay datos de métodos de pago en este período."); return
        df_payment = pd.DataFrame(list(payment_dist.items()), columns=['Método', 'Cantidad'])
        fig = px.pie(df_payment, names='Método', values='Cantidad', hole=.4, color_discrete_sequence=px.colors.sequential.Teal)
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), legend_title_text='Métodos de Pago')
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    def _render_top_categories_chart(self) -> None:
        """Renderiza un gráfico de barras para las categorías más vendidas por monto."""
        # --- CAMBIO: Título actualizado ---
        st.subheader("🏆 Top 5 Categorías por Ingresos")
        # --- CAMBIO: Usamos la nueva clave 'top_categories' ---
        top_categories = self.data.get('top_categories', [])
        
        if not top_categories:
            st.info("ℹ️ No hay datos de ventas de categorías en este período."); return

        # --- CAMBIO: Las columnas ahora son 'name' y 'sales' ---
        df_top = pd.DataFrame(top_categories).sort_values('sales', ascending=True)
        
        fig = px.bar(
            df_top,
            x='sales',
            y='name',
            orientation='h',
            labels={'sales': 'Ingresos (CLP)', 'name': 'Categoría'},
            text_auto=True,
            color_discrete_sequence=[COLOR_PRIMARY]
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis_title=None, yaxis_title=None,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            yaxis={'categoryorder':'total ascending'}
        )
        # Formateamos el texto para que muestre el signo peso y miles
        fig.update_traces(texttemplate='$%{x:,.0f}', textposition='outside')
        
        st.plotly_chart(fig, use_container_width=True)


# --- Punto de Entrada Principal ---
if __name__ == "__main__":
    dashboard = EngagementDashboard()
    dashboard.run()
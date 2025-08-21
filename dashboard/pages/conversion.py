# dashboard/pages/conversion.py
import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.base_dashboard import BaseDashboard
from dashboard.styles import metric_card, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_INFO

class ConversionDashboard(BaseDashboard):
    """
    Dashboard de Conversión y Engagement, con KPIs visuales y cards profesionales.
    """
    def __init__(self):
        super().__init__(
            page_title="Conversión y Engagement",
            page_icon="🛒",
            endpoint="conversion"
        )

    def render_kpi_cards(self) -> None:
        col1, col2 = st.columns(2)
        with col1:
            abandonment = self.data.get('cart_abandonment_rate', 0)
            metric_card("🛒", "Tasa de Abandono de Carrito", f"{abandonment:.1f}%", COLOR_WARNING, "card_abandonment")
        with col2:
            conversion = self.data.get('service_conversion_rate', {})
            for cat, val in conversion.items():
                metric_card("🔄", f"Conversión {cat}", f"{val:.1f}%", COLOR_SUCCESS, f"card_conversion_{cat}")
        st.markdown("<br>", unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            avg_ticket = self.data.get('avg_ticket', 0)
            metric_card("💵", "Ticket Promedio (CLP)", f"${avg_ticket:,.0f}", COLOR_PRIMARY, "card_ticket")
        with col4:
            freq = self.data.get('purchase_frequency', 0)
            metric_card("🔁", "Frecuencia de Compra", f"{freq:.2f}", COLOR_INFO, "card_frequency")
        st.markdown("<br>", unsafe_allow_html=True)
        col5, col6 = st.columns(2)
        with col5:
            payment_methods = self.data.get('popular_payment_methods', {})
            for method, pct in payment_methods.items():
                metric_card("💳", f"Pago: {method}", f"{pct:.1f}%", COLOR_PRIMARY, f"card_payment_{method}")
        with col6:
            photos_pct = self.data.get('orders_with_photos_pct', 0)
            metric_card("📷", "Pedidos con Fotos", f"{photos_pct:.1f}%", COLOR_SUCCESS, "card_photos")
        st.markdown("<br>", unsafe_allow_html=True)
        col7, col8 = st.columns(2)
        with col7:
            feedback_pct = self.data.get('orders_with_feedback_pct', 0)
            metric_card("📝", "Pedidos con Feedback", f"{feedback_pct:.1f}%", COLOR_INFO, "card_feedback")
        with col8:
            specialties = self.data.get('orders_by_specialty', {})
            for spec, pct in specialties.items():
                metric_card("🏷️", f"{spec}", f"{pct:.1f}%", COLOR_PRIMARY, f"card_specialty_{spec}")
        st.markdown("<br>", unsafe_allow_html=True)

    def render_visualizations(self) -> None:
        st.subheader("Tendencia de Conversión por Servicio")
        trend_data = self.data.get('conversion_trend', {})
        if trend_data:
            df_trend = pd.DataFrame(trend_data)
            fig = px.line(df_trend, x='date', y='conversion_rate', color='service', labels={'date': 'Fecha', 'conversion_rate': 'Conversión (%)', 'service': 'Servicio'})
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de tendencia de conversión disponibles.")
        st.subheader("Distribución de Pedidos por Especialidad")
        specialties_data = self.data.get('orders_by_specialty', {})
        if specialties_data:
            df_spec = pd.DataFrame(list(specialties_data.items()), columns=['Especialidad', 'Porcentaje'])
            fig2 = px.pie(df_spec, names='Especialidad', values='Porcentaje', color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No hay datos de especialidad disponibles.")

if __name__ == "__main__":
    dashboard = ConversionDashboard()
    dashboard.run()

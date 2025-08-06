# dashboard/pages/adquisicion.py
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from typing import Dict, List

# --- Importaciones de Módulos del Proyecto ---
from dashboard.base_dashboard import BaseDashboard
from dashboard.styles import metric_card, COLOR_PRIMARY, COLOR_SUCCESS

class AcquisitionDashboard(BaseDashboard):
    """
    Dashboard de adquisición de clientes que hereda toda la lógica
    común de la clase BaseDashboard.
    """
    
    def __init__(self):
        # Llama al constructor de la clase madre con la configuración específica para esta página.
        super().__init__(
            page_title="Adquisición de Clientes",
            page_icon="📈",
            endpoint="acquisition"
        )
    
    def render_kpi_cards(self) -> None:
        """
        Implementación del método abstracto para renderizar las tarjetas de métricas
        específicas de la página de Adquisición.
        """
        col1, col2 = st.columns(2)
        
        with col1:
            new_customers = self.data.get('new_customers', 0)
            metric_card("👤", "Nuevos Clientes Registrados", f"{new_customers:,}", COLOR_PRIMARY, "card_new_customers")
        
        with col2:
            onboarding_rate = self.data.get('onboarding_rate', 0)
            metric_card("✅", "Tasa de Onboarding Completado", f"{onboarding_rate}%", COLOR_SUCCESS, "card_onboarding")
        
        st.markdown("<br>", unsafe_allow_html=True)
    
    def render_visualizations(self) -> None:
        """
        Implementación del método abstracto para renderizar las visualizaciones
        específicas de la página de Adquisición.
        """
        col_trend, col_map = st.columns(2)
        
        with col_trend:
            self._render_trend_chart()
        
        with col_map:
            self._render_acquisition_heatmap()
    
    def _render_trend_chart(self) -> None:
        """Renderiza un gráfico de área interactivo con Plotly Express."""
        st.subheader("Tendencia de Nuevos Clientes por Día")
        
        daily_data = self.data.get('daily_new_users', {})
        
        if (daily_data and daily_data.get('counts') and sum(daily_data['counts']) > 0):
            try:
                df_daily = pd.DataFrame(daily_data)
                df_daily['dates'] = pd.to_datetime(df_daily['dates'])
                # No necesitamos set_index para Plotly Express, lo cual es más simple
                
                # --- CREACIÓN DEL GRÁFICO CON PLOTLY EXPRESS ---
                fig = px.area(
                    df_daily,
                    x='dates',
                    y='counts',
                    labels={'dates': 'Fecha', 'counts': 'Nuevos Clientes'},
                    color_discrete_sequence=[COLOR_PRIMARY] # Usamos nuestro color corporativo
                )

                # --- Personalización Profesional del Gráfico ---
                fig.update_layout(
                    margin=dict(l=0, r=0, t=40, b=0), # Márgenes ajustados
                    xaxis_title=None, # Ocultamos el título del eje X
                    yaxis_title=None, # Ocultamos el título del eje Y
                    yaxis_gridcolor='#e0e0e0', # Color de la rejilla más suave
                    xaxis_gridcolor='#e0e0e0',
                    plot_bgcolor='rgba(0,0,0,0)', # Fondo transparente
                    paper_bgcolor='rgba(0,0,0,0)',
                    hovermode='x unified' # El tooltip muestra todos los datos para una fecha
                )
                
                # Personalizar los tooltips (lo que ves al pasar el mouse)
                fig.update_traces(
                    hovertemplate='<b>%{x|%d %b, %Y}</b><br>Nuevos Clientes: %{y}<extra></extra>'
                )

                # Renderizar el gráfico en Streamlit
                st.plotly_chart(fig, use_container_width=True)

                # --- Estadísticas del período (sin cambios) ---
                with st.expander("📊 Estadísticas del período"):
                    total_new_users = df_daily['counts'].sum()
                    avg_daily = df_daily['counts'].mean()
                    max_day_val = df_daily['counts'].max()
                    max_day_date = df_daily.loc[df_daily['counts'].idxmax()]['dates'].strftime('%d/%m/%Y')

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total en Período", f"{total_new_users:,.0f}")
                    col2.metric("Promedio Diario", f"{avg_daily:.1f}")
                    col3.metric("Día Peak", f"{max_day_val:,.0f}", help=f"El día con más registros fue el {max_day_date}")

            except Exception as e:
                st.error(f"Error al crear el gráfico de tendencia: {str(e)}")
        else:
            st.info("ℹ️ No hay datos de nuevos clientes para mostrar en este período.")
    
    def _render_acquisition_heatmap(self) -> None:
        """Renderiza el mapa de calor de adquisición por comuna."""
        st.subheader("Mapa de Calor de Adquisición por Comuna")
        
        acquisition_by_commune = self.data.get('acquisition_by_commune', [])
        
        if not acquisition_by_commune:
            st.info("ℹ️ No hay datos de comuna para mostrar en este período.")
            return
        
        try:
            m = folium.Map(location=[-33.45, -70.6667], zoom_start=11, tiles="CartoDB positron")
            
            heat_data = [[item['lat'], item['lon'], item['count']] for item in acquisition_by_commune if all(k in item for k in ['lat', 'lon', 'count'])]
            
            if heat_data:
                HeatMap(heat_data, radius=25, blur=15).add_to(m)
            
            st_folium(m, use_container_width=True, height=400)
            
            # ---  Top comunas por adquisición ---
            with st.expander("🏢 Top comunas por adquisición"):
                df_communes = pd.DataFrame(acquisition_by_commune)
                df_communes_sorted = df_communes.sort_values('count', ascending=False)
                
                for _, row in df_communes_sorted.head(5).iterrows():
                    st.write(f"**{row.get('commune', 'N/A')}**: {row['count']} nuevos clientes")
           
                
        except Exception as e:
            st.error(f"Error al crear el mapa de calor: {str(e)}")

# --- Punto de Entrada Principal ---
if __name__ == "__main__":
    dashboard = AcquisitionDashboard()
    dashboard.run()
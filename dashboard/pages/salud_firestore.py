import streamlit as st

# --- Importaciones ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_firestore_health_summary

# --- Configuración de Página ---
st.set_page_config(page_title="Salud de Datos Firestore - LiliApp", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

# --- Carga de Datos ---
@st.cache_data(ttl=300) # Cache por 5 minutos
def load_health_data():
    with st.spinner("Analizando la salud de la base de datos Firestore..."):
        return get_firestore_health_summary()

# --- Cuerpo del Dashboard ---
st.title("🩺 Dashboard de Salud de Datos en Firestore")
st.markdown("Una radiografía de nuestras colecciones para entender la estructura y completitud de los datos.")

data = load_health_data()

if st.button("Recargar Análisis"):
    st.cache_data.clear()
    st.rerun()

if not data:
    st.error("No se pudo generar el resumen de salud. Revisa el backend.")
    st.stop()

# --- Sección de Conteos Generales ---
st.subheader("📊 Conteos de Documentos por Colección Principal")
counts = data.get("collection_counts", {})
if counts:
    cols = st.columns(len(counts))
    for i, (collection, count) in enumerate(counts.items()):
        cols[i].metric(f"📄 {collection.capitalize()}", f"{count:,}")
else:
    st.info("No se encontraron colecciones principales.")

st.markdown("---")

# --- Sección de Salud de Usuarios ---
st.subheader("👤 Análisis de la Colección `Users`")
user_health = data.get("user_health", {})
if user_health:
    total_users = user_health.get("total_users", 0)
    st.write(f"Se analizaron **{total_users}** documentos de usuario.")

    st.progress(user_health.get("with_customer_profile_percent", 0) / 100, text=f"**{user_health.get('with_customer_profile_percent', 0):.1f}%** de los usuarios tienen un Perfil de Cliente.")
    st.progress(user_health.get("profiles_with_rut_percent", 0) / 100, text=f"**{user_health.get('profiles_with_rut_percent', 0):.1f}%** de los perfiles tienen un RUT definido.")
    st.progress(user_health.get("with_addresses_subcollection_percent", 0) / 100, text=f"**{user_health.get('with_addresses_subcollection_percent', 0):.1f}%** de los perfiles tienen al menos una dirección.")
    
    st.markdown("##### Estructura de Subcolecciones:")
    cols = st.columns(2)
    cols[0].metric("Avg. Direcciones por Usuario", f"{user_health.get('avg_addresses_per_user', 0):.2f}")
    cols[1].metric("Máx. Direcciones en un Usuario", f"{user_health.get('max_addresses_in_one_user', 0)}")
else:
    st.info("No hay datos de salud para la colección de usuarios.")

st.markdown("---")

# --- Sección de Diagnóstico ---
st.subheader("💬 Diagnóstico del Arquitecto")
if user_health:
    max_addresses = user_health.get('max_addresses_in_one_user', 0)
    st.info(
        """
        **Observaciones sobre la Estructura de Usuarios:**
        - Las barras de progreso nos muestran qué tan completos están nuestros datos. Un bajo porcentaje en "RUT definido" podría indicar la necesidad de hacerlo obligatorio en el registro.
        - **Avg. y Máx. Direcciones** son KPIs cruciales. Nos muestran que los usuarios ya están guardando múltiples direcciones.
        """
    )
    if max_addresses > 10:
        st.warning(
            f"""
            **¡Alerta de Escalabilidad POSITIVA!**
            Hemos detectado un usuario con **{max_addresses} direcciones**. Esto **valida nuestra decisión** de usar subcoleculares.
            Si estuviéramos usando un arreglo anidado, este usuario estaría en riesgo de alcanzar el límite de 1MB del documento,
            lo que haría que su perfil dejara de funcionar. Nuestra arquitectura actual soporta este caso de uso sin problemas.
            """,
            icon="🛡️"
        )
    else:
        st.success(
            """
            **Conclusión sobre la Arquitectura:**
            El modelo actual de `users -> customer_profiles -> addresses` con subcoleculares es **correcto y escalable**.
            La "dificultad" de saltar entre colecciones se resuelve creando funciones de servicio reutilizables en el backend
            (como `get_firestore_data_for_audit`), no aplanando la estructura de datos. Aplanar los datos introduciría
            problemas de escalabilidad graves a largo plazo.
            """,
            icon="✅"
        )
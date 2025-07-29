import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# --- Patrón de Importación y Autenticación ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
from dashboard.auth import check_login
from dashboard.menu import render_menu
# Se importa el cliente de API centralizado
from dashboard.api_client import (
    get_jumpseller_orders, get_jumpseller_products, get_jumpseller_categories,
    post_jumpseller_category, get_jumpseller_customers, update_jumpseller_customer,
    delete_jumpseller_customer, get_jumpseller_customer_details
)

st.set_page_config(page_title="Explorador Jumpseller - LiliApp", layout="wide")
check_login()
render_menu()

st.title("📦 Explorador de Datos de Jumpseller")
st.markdown("Visualiza y gestiona los datos en crudo directamente desde la API de Jumpseller.")

tab_orders, tab_products, tab_categories, tab_customers = st.tabs(["🛍️ Órdenes", "🛠️ Productos", "🗂️ Categorías", "👤 Clientes"])

# --- Pestaña de Órdenes (con AgGrid y Quick Actions) ---
with tab_orders:
    st.header("Últimas Órdenes Pagadas")
    page_orders = st.number_input("Página de Órdenes", min_value=1, value=1, key="page_orders")

    if st.button("Cargar Órdenes", key="btn_load_orders"):
        with st.spinner("Cargando órdenes..."):
            orders_data = get_jumpseller_orders(page=page_orders, status="paid")
            if orders_data:
                processed_orders = []
                for item in orders_data:
                    order = item.get('order', {})
                    customer = order.get('customer', {})
                    processed_orders.append({
                        'ID Orden': order.get('id'),
                        'Estado': order.get('status'),
                        'Total': order.get('total'),
                        'Fecha Creación': order.get('created_at'),
                        'ID Cliente': customer.get('id'),
                        'Nombre Cliente': customer.get('name')
                    })
                st.session_state.orders_df = pd.DataFrame(processed_orders)
            else:
                st.session_state.orders_df = pd.DataFrame()

    if 'orders_df' in st.session_state and not st.session_state.orders_df.empty:
        gb = GridOptionsBuilder.from_dataframe(st.session_state.orders_df)
        cell_button_renderer = JsCode("""
            class BtnCellRenderer {
                init(params) {
                    this.params = params;
                    this.eGui = document.createElement('div');
                    if (params.data['ID Cliente']) {
                        this.eGui.innerHTML = `<button class="btn btn-sm" style="background-color: #0068c9; color: white; border: none; padding: 5px 10px; border-radius: 5px;">Ver Cliente</button>`;
                        this.btn = this.eGui.querySelector('button');
                        this.btn.addEventListener('click', () => this.onBtnClick());
                    }
                }
                getGui() { return this.eGui; }
                onBtnClick() {
                    this.params.api.sendDataToStreamlit({ type: 'view_customer_clicked', data: this.params.data });
                }
            }
        """)
        gb.configure_column("Acciones", cellRenderer=cell_button_renderer, width=120, headerName="Acciones")
        gb.configure_pagination(paginationAutoPageSize=True)
        grid_options = gb.build()

        df_display = st.session_state.orders_df.copy()
        df_display['Acciones'] = ''

        grid_response = AgGrid(
            df_display[['ID Orden', 'Estado', 'Total', 'Fecha Creación', 'Nombre Cliente', 'Acciones']],
            gridOptions=grid_options, update_mode='MANUAL', allow_unsafe_jscode=True,
            enable_enterprise_modules=False, height=400, width='100%', key='orders_grid'
        )

        if grid_response.get('data_streamlit_send') and grid_response['data_streamlit_send']['type'] == 'view_customer_clicked':
            customer_id = grid_response['data_streamlit_send']['data'].get('ID Cliente')
            if customer_id:
                with st.spinner(f"Buscando detalles del cliente ID: {customer_id}..."):
                    customer_details = get_jumpseller_customer_details(customer_id)
                    if customer_details:
                        @st.dialog(f"Detalles del Cliente: {customer_details.get('name', '')}")
                        def show_customer_details_dialog(details):
                            st.write(f"**Nombre:** {details.get('name')}")
                            st.write(f"**Email:** {details.get('email')}")
                            st.write(f"**Teléfono:** {details.get('phone')}")
                            address = details.get('shipping_address', {})
                            st.write(f"**Dirección:** {address.get('address', '')}, {address.get('city', '')}")
                        show_customer_details_dialog(customer_details)
    elif 'orders_df' in st.session_state:
        st.info("No se encontraron órdenes para los filtros seleccionados.")

# --- Pestaña de Productos (Refactorizada) ---
with tab_products:
    st.header("Productos Disponibles")
    page_products = st.number_input("Página de Productos", min_value=1, value=1, key="page_products")
    if st.button("Cargar Productos", key="btn_load_products"):
        with st.spinner("Cargando productos..."):
            products_data = get_jumpseller_products(page=page_products, status="available")
            if products_data:
                st.session_state.products_df = pd.DataFrame([item.get('product', {}) for item in products_data])
            else:
                st.session_state.products_df = pd.DataFrame()

    if 'products_df' in st.session_state and not st.session_state.products_df.empty:
        st.dataframe(st.session_state.products_df[['id', 'name', 'price', 'stock', 'status']], use_container_width=True, hide_index=True)
    elif 'products_df' in st.session_state:
        st.info("No se encontraron productos.")

# --- Pestaña de Categorías (Refactorizada) ---
with tab_categories:
    st.header("Gestión de Categorías en Jumpseller")
    with st.expander("➕ Crear Nueva Categoría"):
        with st.form("create_cat_form", clear_on_submit=True):
            cat_name = st.text_input("Nombre de la Nueva Categoría")
            if st.form_submit_button("Crear Categoría"):
                if cat_name:
                    response = post_jumpseller_category(cat_name)
                    if response:
                        st.success(f"Categoría '{cat_name}' creada con éxito.")
                        st.cache_data.clear() # Limpiar cache si se usa
    
    st.markdown("---")
    st.header("Lista de Categorías")
    page_categories = st.number_input("Página de Categorías", min_value=1, value=1, key="page_cats")
    if st.button("Cargar Categorías", key="btn_load_cats"):
        with st.spinner("Cargando categorías..."):
            categories_data = get_jumpseller_categories(page=page_categories)
            if categories_data:
                st.session_state.categories_df = pd.DataFrame([item.get('category', {}) for item in categories_data])
            else:
                st.session_state.categories_df = pd.DataFrame()

    if 'categories_df' in st.session_state and not st.session_state.categories_df.empty:
        st.dataframe(st.session_state.categories_df, use_container_width=True, hide_index=True)
    elif 'categories_df' in st.session_state:
        st.info("No se encontraron más categorías.")

# --- Pestaña de Clientes (Refactorizada) ---
with tab_customers:
    st.header("Gestión de Clientes en Jumpseller")
    if st.button("Cargar Clientes", key="load_customers"):
        with st.spinner("Cargando clientes..."):
            customers_data = get_jumpseller_customers()
            if customers_data:
                st.session_state.customers_data = [item.get('customer', {}) for item in customers_data]
            else:
                st.session_state.customers_data = []

    if 'customers_data' in st.session_state and st.session_state.customers_data:
        df_customers = pd.DataFrame(st.session_state.customers_data)
        st.dataframe(df_customers, use_container_width=True, hide_index=True)
        st.markdown("---")
        
        st.subheader("Editar o Eliminar un Cliente")
        customer_options = {cust['id']: f"{cust.get('fullname', 'N/A')} ({cust.get('email', 'N/A')})" for cust in st.session_state.customers_data}
        selected_customer_id = st.selectbox(
            "Selecciona un cliente para gestionar:",
            options=[None] + list(customer_options.keys()),
            format_func=lambda cust_id: customer_options.get(cust_id, "Elige un cliente...")
        )

        if selected_customer_id:
            customer_details = next((c for c in st.session_state.customers_data if c['id'] == selected_customer_id), {})
            
            with st.form("edit_customer_form"):
                st.write(f"**Editando Cliente ID: {customer_details.get('id')}**")
                fullname = st.text_input("Nombre Completo", value=customer_details.get("fullname", ""))
                email = st.text_input("Email", value=customer_details.get("email", ""))
                phone = st.text_input("Teléfono", value=customer_details.get("phone", ""))
                
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.form_submit_button("Guardar Cambios", type="primary"):
                        payload = {"fullname": fullname, "email": email, "phone": phone}
                        response = update_jumpseller_customer(selected_customer_id, payload)
                        if response:
                            st.success("Cliente actualizado con éxito. Presiona 'Cargar Clientes' para ver los cambios.")
                            del st.session_state.customers_data
                with col2:
                    if st.form_submit_button("Eliminar Cliente", type="secondary"):
                        response = delete_jumpseller_customer(selected_customer_id)
                        if response:
                            st.success("Cliente eliminado con éxito. Presiona 'Cargar Clientes' para ver los cambios.")
                            del st.session_state.customers_data

    elif 'customers_data' in st.session_state:
        st.info("No se encontraron clientes.")
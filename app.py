import math

import pandas as pd
import psycopg2
import streamlit as st

from db import (
    count_products,
    create_product,
    delete_product,
    get_category_report,
    get_low_stock_report,
    get_report_summary,
    list_categories,
    list_products,
    test_connection,
)
from validators import normalize_product


st.set_page_config(
    page_title="CRUD Productos - Supabase",
    layout="wide",
)


st.markdown(
    """
    <style>
    .block-container {
        max-width: 1180px;
        padding-top: 1.6rem;
    }
    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.8rem 1rem;
    }
    .table-title {
        color: #334155;
        font-weight: 700;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 0.4rem;
    }
    .muted {
        color: #64748b;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_flash():
    flash = st.session_state.pop("flash", None)
    if not flash:
        return

    kind, message = flash
    if kind == "success":
        st.success(message)
    elif kind == "warning":
        st.warning(message)
    else:
        st.error(message)


def require_database():
    try:
        test_connection()
    except RuntimeError as exc:
        st.error("Falta configurar la conexion con Supabase.")
        st.info(str(exc))
        st.code(
            '[supabase]\n'
            'db_url = "postgresql://postgres.PROJECT_REF:TU_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require"',
            language="toml",
        )
        st.stop()
    except psycopg2.Error as exc:
        st.error("No se pudo conectar con PostgreSQL/Supabase.")
        st.caption(str(exc).strip())
        st.stop()


def format_money(value):
    return f"S/ {float(value):,.2f}"


def render_errors(errors):
    for message in errors.values():
        st.error(message)


st.title("CRUD de productos")
st.caption("Python + Streamlit + SQL parametrizado + Supabase PostgreSQL")

require_database()
show_flash()

categories = list_categories()

with st.sidebar:
    st.header("Filtros")
    search = st.text_input("Buscar por nombre", max_chars=80)
    categoria_filter = st.selectbox("Categoria", ["Todas", *categories])
    estado_filter = st.selectbox("Estado", ["Todos", "Activos", "Inactivos"])

    price_col_1, price_col_2 = st.columns(2)
    min_price_input = price_col_1.number_input(
        "Precio min.",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
    )
    max_price_input = price_col_2.number_input(
        "Precio max.",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        help="Usa 0 para no aplicar limite.",
    )
    page_size = st.selectbox("Registros por pagina", [5, 10, 20, 50], index=1)

min_price = min_price_input if min_price_input > 0 else None
max_price = max_price_input if max_price_input > 0 else None

if min_price is not None and max_price is not None and min_price > max_price:
    st.sidebar.error("El precio minimo no puede ser mayor que el precio maximo.")
    st.stop()

filters = {
    "search": search,
    "categoria": categoria_filter,
    "estado": estado_filter,
    "min_price": min_price,
    "max_price": max_price,
}

filter_signature = (search, categoria_filter, estado_filter, min_price, max_price, page_size)
if st.session_state.get("filter_signature") != filter_signature:
    st.session_state["page"] = 1
    st.session_state["filter_signature"] = filter_signature

if "page" not in st.session_state:
    st.session_state["page"] = 1

crud_tab, reports_tab = st.tabs(["CRUD", "Reportes"])

with crud_tab:
    with st.expander("Crear nuevo producto", expanded=True):
        with st.form("create_product_form", clear_on_submit=True):
            form_col_1, form_col_2 = st.columns(2)
            nombre = form_col_1.text_input("Nombre", max_chars=80)
            categoria = form_col_2.text_input("Categoria", max_chars=50)
            precio = form_col_1.number_input(
                "Precio",
                min_value=0.01,
                max_value=999999.99,
                value=1.00,
                step=1.00,
                format="%.2f",
            )
            stock = form_col_2.number_input(
                "Stock",
                min_value=0,
                max_value=1000000,
                value=0,
                step=1,
            )
            activo = st.checkbox("Activo", value=True)
            submitted = st.form_submit_button("Crear producto", type="primary")

        if submitted:
            product, errors = normalize_product(
                {
                    "nombre": nombre,
                    "categoria": categoria,
                    "precio": precio,
                    "stock": stock,
                    "activo": activo,
                }
            )
            if errors:
                render_errors(errors)
            else:
                try:
                    new_id = create_product(product)
                    st.success(f"Producto creado correctamente. ID: {new_id}")
                except psycopg2.Error as exc:
                    st.error("No se pudo crear el producto.")
                    st.caption(str(exc).strip())

    total_records = count_products(filters)
    total_pages = max(1, math.ceil(total_records / page_size))
    st.session_state["page"] = min(st.session_state["page"], total_pages)
    current_page = st.session_state["page"]
    offset = (current_page - 1) * page_size
    products = list_products(filters, limit=page_size, offset=offset)

    st.subheader("Lectura, busqueda y acciones")
    st.markdown(
        f'<p class="muted">Mostrando {len(products)} de {total_records} registros.</p>',
        unsafe_allow_html=True,
    )

    if products:
        header_cols = st.columns([0.45, 2.1, 1.35, 0.9, 0.75, 0.85, 1.6])
        headers = ["ID", "Nombre", "Categoria", "Precio", "Stock", "Estado", "Acciones"]
        for col, header in zip(header_cols, headers):
            col.markdown(f'<div class="table-title">{header}</div>', unsafe_allow_html=True)

        for product in products:
            row_cols = st.columns([0.45, 2.1, 1.35, 0.9, 0.75, 0.85, 1.6])
            row_cols[0].write(product["id"])
            row_cols[1].write(product["nombre"])
            row_cols[2].write(product["categoria"])
            row_cols[3].write(format_money(product["precio"]))
            row_cols[4].write(product["stock"])
            row_cols[5].write("Activo" if product["activo"] else "Inactivo")

            action_col_1, action_col_2 = row_cols[6].columns(2)
            if action_col_1.button("Editar", key=f"edit_{product['id']}", use_container_width=True):
                st.session_state["edit_producto_id"] = int(product["id"])
                st.switch_page("pages/1_Editar_producto.py")
            if action_col_2.button("Eliminar", key=f"delete_{product['id']}", use_container_width=True):
                st.session_state["delete_candidate"] = {
                    "id": int(product["id"]),
                    "nombre": product["nombre"],
                }

        delete_candidate = st.session_state.get("delete_candidate")
        if delete_candidate:
            st.warning(
                f"Vas a eliminar el producto #{delete_candidate['id']}: "
                f"{delete_candidate['nombre']}. Esta accion no se puede deshacer."
            )
            confirm_text = st.text_input(
                'Escribe "ELIMINAR" para confirmar',
                key="delete_confirm_text",
                max_chars=8,
            )
            confirm_col, cancel_col = st.columns([1, 4])
            if confirm_col.button(
                "Confirmar",
                type="primary",
                disabled=confirm_text.strip().upper() != "ELIMINAR",
            ):
                try:
                    deleted = delete_product(delete_candidate["id"])
                    if deleted:
                        st.session_state["flash"] = ("success", "Producto eliminado correctamente.")
                    else:
                        st.session_state["flash"] = ("warning", "El producto ya no existe.")
                    st.session_state.pop("delete_candidate", None)
                    st.session_state.pop("delete_confirm_text", None)
                    st.rerun()
                except psycopg2.Error as exc:
                    st.error("No se pudo eliminar el producto.")
                    st.caption(str(exc).strip())

            if cancel_col.button("Cancelar eliminacion"):
                st.session_state.pop("delete_candidate", None)
                st.session_state.pop("delete_confirm_text", None)
                st.rerun()
    else:
        st.info("No hay productos que coincidan con los filtros actuales.")

    prev_col, page_col, next_col = st.columns([1, 3, 1])
    if prev_col.button("Anterior", disabled=current_page <= 1, use_container_width=True):
        st.session_state["page"] = current_page - 1
        st.rerun()
    page_col.markdown(
        f"<div style='text-align:center; padding-top:0.45rem;'>Pagina {current_page} de {total_pages}</div>",
        unsafe_allow_html=True,
    )
    if next_col.button("Siguiente", disabled=current_page >= total_pages, use_container_width=True):
        st.session_state["page"] = current_page + 1
        st.rerun()

with reports_tab:
    st.subheader("Reportes de inventario")
    report_col_1, report_col_2 = st.columns([2, 1])
    report_category = report_col_1.selectbox("Categoria del reporte", ["Todas", *categories])
    stock_limit = report_col_2.slider("Stock bajo hasta", min_value=0, max_value=100, value=10)

    summary = get_report_summary(report_category)
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Productos", summary["total_productos"])
    metric_2.metric("Unidades", summary["total_unidades"])
    metric_3.metric("Valor inventario", format_money(summary["valor_inventario"]))
    metric_4.metric("Precio promedio", format_money(summary["precio_promedio"]))

    category_rows = get_category_report(report_category)
    if category_rows:
        category_df = pd.DataFrame(category_rows)
        category_df["valor_inventario"] = category_df["valor_inventario"].astype(float)
        st.markdown("**Resumen por categoria**")
        st.dataframe(category_df, use_container_width=True, hide_index=True)
        st.bar_chart(category_df.set_index("categoria")["valor_inventario"])
    else:
        st.info("No hay datos para el reporte seleccionado.")

    low_stock_rows = get_low_stock_report(stock_limit, report_category)
    st.markdown("**Productos con stock bajo**")
    if low_stock_rows:
        st.dataframe(pd.DataFrame(low_stock_rows), use_container_width=True, hide_index=True)
    else:
        st.success("No hay productos por debajo del umbral seleccionado.")

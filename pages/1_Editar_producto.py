import psycopg2
import streamlit as st

from db import get_product_by_id, update_product
from validators import normalize_product


st.set_page_config(
    page_title="Editar producto",
    layout="centered",
)


def get_selected_product_id():
    product_id = st.session_state.get("edit_producto_id")
    if product_id:
        return int(product_id)

    query_value = st.query_params.get("id")
    if isinstance(query_value, list):
        query_value = query_value[0] if query_value else None

    try:
        return int(query_value) if query_value else None
    except (TypeError, ValueError):
        return None


def render_errors(errors):
    for message in errors.values():
        st.error(message)


st.title("Editar producto")

selected_id = get_selected_product_id()
if not selected_id:
    st.warning("Selecciona un producto desde la tabla principal.")
    if st.button("Volver al listado"):
        st.switch_page("app.py")
    st.stop()

try:
    product = get_product_by_id(selected_id)
except RuntimeError as exc:
    st.error("Falta configurar la conexion con Supabase.")
    st.info(str(exc))
    st.stop()
except psycopg2.Error as exc:
    st.error("No se pudo consultar el producto.")
    st.caption(str(exc).strip())
    st.stop()

if not product:
    st.warning("El producto seleccionado ya no existe.")
    if st.button("Volver al listado"):
        st.switch_page("app.py")
    st.stop()

with st.form("edit_product_form"):
    form_col_1, form_col_2 = st.columns(2)
    nombre = form_col_1.text_input("Nombre", value=product["nombre"], max_chars=80)
    categoria = form_col_2.text_input("Categoria", value=product["categoria"], max_chars=50)
    precio = form_col_1.number_input(
        "Precio",
        min_value=0.01,
        max_value=999999.99,
        value=float(product["precio"]),
        step=1.00,
        format="%.2f",
    )
    stock = form_col_2.number_input(
        "Stock",
        min_value=0,
        max_value=1000000,
        value=int(product["stock"]),
        step=1,
    )
    activo = st.checkbox("Activo", value=bool(product["activo"]))

    save = st.form_submit_button("Guardar cambios", type="primary")

if save:
    cleaned_product, errors = normalize_product(
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
            updated = update_product(selected_id, cleaned_product)
            if updated:
                st.session_state["flash"] = ("success", "Producto actualizado correctamente.")
                st.switch_page("app.py")
            else:
                st.warning("El producto ya no existe.")
        except psycopg2.Error as exc:
            st.error("No se pudo actualizar el producto.")
            st.caption(str(exc).strip())

if st.button("Volver al listado"):
    st.switch_page("app.py")


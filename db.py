import os
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import streamlit as st


def _read_db_url():
    secret_url = None
    try:
        supabase_section = st.secrets.get("supabase", {})
        secret_url = supabase_section.get("db_url")
    except Exception:
        secret_url = None

    db_url = secret_url or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError(
            "Configura .streamlit/secrets.toml con [supabase].db_url "
            "o define la variable SUPABASE_DB_URL."
        )

    if "sslmode=" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"
    return db_url


@st.cache_resource(show_spinner=False)
def get_connection_pool():
    return pool.ThreadedConnectionPool(minconn=1, maxconn=5, dsn=_read_db_url())


@contextmanager
def get_connection():
    connection_pool = get_connection_pool()
    connection = connection_pool.getconn()
    try:
        yield connection
    finally:
        connection_pool.putconn(connection)


def run_query(sql, params=None, fetch=None):
    params = params or ()
    with get_connection() as connection:
        try:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                result = None
                if fetch == "one":
                    result = cursor.fetchone()
                elif fetch == "all":
                    result = cursor.fetchall()
                connection.commit()
                return result
        except Exception:
            connection.rollback()
            raise


def test_connection():
    return run_query("select 1 as ok;", fetch="one")


def _build_product_filters(filters):
    filters = filters or {}
    clauses = []
    params = []

    search = str(filters.get("search") or "").strip()
    if search:
        clauses.append("nombre ILIKE %s")
        params.append(f"%{search}%")

    categoria = filters.get("categoria")
    if categoria and categoria != "Todas":
        clauses.append("categoria = %s")
        params.append(categoria)

    estado = filters.get("estado")
    if estado == "Activos":
        clauses.append("activo = true")
    elif estado == "Inactivos":
        clauses.append("activo = false")

    min_price = filters.get("min_price")
    if min_price is not None:
        clauses.append("precio >= %s")
        params.append(min_price)

    max_price = filters.get("max_price")
    if max_price is not None:
        clauses.append("precio <= %s")
        params.append(max_price)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def list_categories():
    rows = run_query(
        """
        SELECT DISTINCT categoria
        FROM public.productos
        ORDER BY categoria;
        """,
        fetch="all",
    )
    return [row["categoria"] for row in rows]


def count_products(filters=None):
    where_sql, params = _build_product_filters(filters)
    row = run_query(
        f"""
        SELECT COUNT(*)::int AS total
        FROM public.productos
        {where_sql};
        """,
        params,
        fetch="one",
    )
    return row["total"]


def list_products(filters=None, limit=10, offset=0):
    where_sql, params = _build_product_filters(filters)
    params = [*params, limit, offset]
    return run_query(
        f"""
        SELECT
            id,
            nombre,
            categoria,
            precio,
            stock,
            activo,
            created_at,
            updated_at
        FROM public.productos
        {where_sql}
        ORDER BY id DESC
        LIMIT %s OFFSET %s;
        """,
        params,
        fetch="all",
    )


def get_product_by_id(product_id):
    return run_query(
        """
        SELECT
            id,
            nombre,
            categoria,
            precio,
            stock,
            activo,
            created_at,
            updated_at
        FROM public.productos
        WHERE id = %s;
        """,
        (product_id,),
        fetch="one",
    )


def create_product(product):
    row = run_query(
        """
        INSERT INTO public.productos (nombre, categoria, precio, stock, activo)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            product["nombre"],
            product["categoria"],
            product["precio"],
            product["stock"],
            product["activo"],
        ),
        fetch="one",
    )
    return row["id"]


def update_product(product_id, product):
    row = run_query(
        """
        UPDATE public.productos
        SET
            nombre = %s,
            categoria = %s,
            precio = %s,
            stock = %s,
            activo = %s
        WHERE id = %s
        RETURNING id;
        """,
        (
            product["nombre"],
            product["categoria"],
            product["precio"],
            product["stock"],
            product["activo"],
            product_id,
        ),
        fetch="one",
    )
    return row


def delete_product(product_id):
    row = run_query(
        """
        DELETE FROM public.productos
        WHERE id = %s
        RETURNING id;
        """,
        (product_id,),
        fetch="one",
    )
    return row


def _build_report_filter(categoria):
    if categoria and categoria != "Todas":
        return "WHERE categoria = %s", [categoria]
    return "", []


def get_report_summary(categoria="Todas"):
    where_sql, params = _build_report_filter(categoria)
    return run_query(
        f"""
        SELECT
            COUNT(*)::int AS total_productos,
            COALESCE(SUM(stock), 0)::int AS total_unidades,
            COALESCE(SUM(stock * precio), 0)::numeric(12, 2) AS valor_inventario,
            COALESCE(AVG(precio), 0)::numeric(12, 2) AS precio_promedio
        FROM public.productos
        {where_sql};
        """,
        params,
        fetch="one",
    )


def get_category_report(categoria="Todas"):
    where_sql, params = _build_report_filter(categoria)
    return run_query(
        f"""
        SELECT
            categoria,
            COUNT(*)::int AS productos,
            COALESCE(SUM(stock), 0)::int AS unidades,
            COALESCE(SUM(stock * precio), 0)::numeric(12, 2) AS valor_inventario
        FROM public.productos
        {where_sql}
        GROUP BY categoria
        ORDER BY valor_inventario DESC, categoria ASC;
        """,
        params,
        fetch="all",
    )


def get_low_stock_report(stock_limit=10, categoria="Todas"):
    clauses = ["stock <= %s"]
    params = [stock_limit]
    if categoria and categoria != "Todas":
        clauses.append("categoria = %s")
        params.append(categoria)

    where_sql = f"WHERE {' AND '.join(clauses)}"
    return run_query(
        f"""
        SELECT id, nombre, categoria, precio, stock, activo
        FROM public.productos
        {where_sql}
        ORDER BY stock ASC, nombre ASC;
        """,
        params,
        fetch="all",
    )

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re


TEXT_RE = re.compile(r"^[\w\s.,()/_-]+$", re.UNICODE)
MONEY_SCALE = Decimal("0.01")
MAX_PRICE = Decimal("999999.99")
MAX_STOCK = 1_000_000


def _to_money(value):
    try:
        return Decimal(str(value)).quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None


def normalize_product(values):
    """Return cleaned product data and validation errors."""
    errors = {}

    nombre = str(values.get("nombre", "")).strip()
    categoria = str(values.get("categoria", "")).strip()
    precio = _to_money(values.get("precio"))

    try:
        stock = int(values.get("stock", 0))
    except (TypeError, ValueError):
        stock = None

    if len(nombre) < 2 or len(nombre) > 80:
        errors["nombre"] = "El nombre debe tener entre 2 y 80 caracteres."
    elif not TEXT_RE.match(nombre):
        errors["nombre"] = "El nombre contiene caracteres no permitidos."

    if len(categoria) < 2 or len(categoria) > 50:
        errors["categoria"] = "La categoria debe tener entre 2 y 50 caracteres."
    elif not TEXT_RE.match(categoria):
        errors["categoria"] = "La categoria contiene caracteres no permitidos."

    if precio is None:
        errors["precio"] = "El precio debe ser un numero valido."
    elif precio <= 0 or precio > MAX_PRICE:
        errors["precio"] = "El precio debe ser mayor que 0 y menor o igual a 999999.99."

    if stock is None:
        errors["stock"] = "El stock debe ser un numero entero."
    elif stock < 0 or stock > MAX_STOCK:
        errors["stock"] = "El stock debe estar entre 0 y 1000000."

    cleaned = {
        "nombre": nombre,
        "categoria": categoria,
        "precio": precio,
        "stock": stock,
        "activo": bool(values.get("activo", True)),
    }
    return cleaned, errors

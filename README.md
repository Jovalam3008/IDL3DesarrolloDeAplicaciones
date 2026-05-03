# CRUD Streamlit + Supabase PostgreSQL

Proyecto academico que implementa operaciones CRUD sobre la tabla `productos` usando Python, Streamlit y SQL parametrizado contra PostgreSQL en Supabase.

## Estructura

- `app.py`: pagina principal con crear, leer, filtrar, paginar, eliminar y reportes.
- `pages/1_Editar_producto.py`: pagina de actualizacion de registros.
- `db.py`: capa de conexion y consultas SQL parametrizadas.
- `validators.py`: validacion de datos antes de insertar o actualizar.
- `sql/01_schema.sql`: creacion de tabla, indices, trigger de `updated_at`, vista de reporte y datos semilla.
- `sql/02_consultas_reportes.sql`: consultas SQL de referencia para CRUD y reportes.
- `.streamlit/secrets.toml.example`: plantilla de credenciales.

## Pasos para conectar con Supabase

1. Crea un proyecto en Supabase.
2. Entra a `SQL Editor` y ejecuta completo el archivo `sql/01_schema.sql`.
3. Ve a `Connect` en el dashboard del proyecto y copia una cadena de conexion PostgreSQL.
4. Para uso local con Streamlit, usa preferentemente `Session pooler` si tu red no soporta IPv6. Tambien puedes usar la conexion directa si tu red soporta IPv6.
5. Copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml`.
6. Pega tu cadena en `db_url` y reemplaza `TU_PASSWORD` por la clave real de la base de datos.
7. Asegurate de que la cadena incluya `sslmode=require`. Si tu password tiene caracteres como `@`, `#`, `/` o `%`, codificalos en formato URL.

Ejemplo:

```toml
[supabase]
db_url = "postgresql://postgres.PROJECT_REF:TU_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require"
```

No subas `.streamlit/secrets.toml` a Git. Ya esta incluido en `.gitignore`.

## Ejecucion local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Si PowerShell bloquea la activacion del entorno virtual, usa esta opcion solo para la terminal actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Tambien puedes ejecutar sin activar el entorno:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

La aplicacion quedara disponible normalmente en:

```text
http://localhost:8501
```

## Control de versiones

```powershell
git status
git add .
git commit -m "Implementa CRUD con Streamlit y Supabase"
```

## Seguridad aplicada

- Las operaciones usan parametros de `psycopg2`, evitando concatenar valores del usuario en SQL.
- Los formularios usan limites del lado de Streamlit y validacion del lado servidor en `validators.py`.
- La eliminacion solicita confirmacion escribiendo `ELIMINAR`.
- Las credenciales se guardan en secretos locales, no en el repositorio.

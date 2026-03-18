"""
Utilidades generales: manejo de URIs, errores, conversiones.
"""

import os
from pathlib import Path
from sqlalchemy.engine.url import make_url

try:
    import tomllib
except ImportError:
    tomllib = None


def get_db_uri() -> str:
    """Obtiene URI de BD desde env var, con limpieza de comillas."""
    raw_uri = os.getenv(
        "DEEPSQL_DB_URI",
        "postgresql+psycopg2://usuario:clave@localhost:5432/mi_basedatos",
    )
    return raw_uri.strip().strip('"').strip("'")


def get_connections_file_path() -> str:
    """Obtiene ruta del archivo connections.toml."""
    configured_path = os.getenv("DEEPSQL_CONNECTIONS_FILE", "connections.toml").strip()
    return configured_path or "connections.toml"


def resolve_optional_path(raw_path: str, base_dir: Path) -> str:
    """Resuelve ruta relativa o absoluta desde base_dir."""
    raw_value = (raw_path or "").strip()
    if not raw_value:
        return ""

    candidate = Path(raw_value)
    if candidate.is_absolute():
        return str(candidate)

    return str((base_dir / candidate).resolve())


def validate_db_uri(uri: str) -> None:
    """Valida formato de URI según SQLAlchemy."""
    try:
        make_url(uri)
    except Exception as exc:
        raise RuntimeError(
            "La URI de base de datos tiene formato invalido para SQLAlchemy. "
            "Ejemplos validos: "
            "postgresql+psycopg2://user:pass@host:5432/db, "
            "oracle+oracledb://user:pass@host:1521/?service_name=DB1, "
            "mysql+pymysql://user:pass@host:3306/db, "
            "mssql+pyodbc://user:pass@host:1433/db?driver=ODBC+Driver+18+for+SQL+Server, "
            "sqlite:///./archivo.db. "
            "Si la clave contiene caracteres especiales (@, :, /, #, ?), debe ir URL-encoded. "
            "En CMD define la variable con: set \"DEEPSQL_DB_URI=...\"."
        ) from exc


def safe_uri_for_display(uri: str) -> str:
    """Renderiza URI sin mostrar contraseña."""
    try:
        return make_url(uri).render_as_string(hide_password=True)
    except Exception:
        return "<uri-invalida>"


def build_connection_error(exc: Exception, db_uri: str, db_dialect: str) -> RuntimeError:
    """Construye mensaje de error de conexión con contexto."""
    from deepsql.dialect import get_dialect_label

    base_msg = (
        f"No se pudo conectar al perfil activo ({get_dialect_label(db_dialect)}). "
        f"URI: {safe_uri_for_display(db_uri)}"
    )

    if isinstance(exc, UnicodeDecodeError):
        return RuntimeError(
            base_msg
            + "\n\n"
            + "Se detecto un problema de codificacion (UnicodeDecodeError). "
            + "Suele ocurrir cuando usuario/clave/host/db contienen caracteres especiales sin URL-encoding "
            + "(por ejemplo: ñ, ó, espacios, #, ?, @, /, :).\n"
            + "Accion recomendada: URL-encode en la URI (ejemplo de password con caracteres especiales: clave%40segura%23)."
        )

    return RuntimeError(base_msg + f"\n\nDetalle tecnico: {exc}")

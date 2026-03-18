"""
Gestión de perfiles de conexión y carga de configuración TOML.
"""

import os
from pathlib import Path

from deepsql.config import DEFAULT_ORACLE_MODE, DEFAULT_ORACLE_CLIENT_LIB_DIR
from deepsql.dialect import get_db_dialect
from deepsql.utils import (
    get_db_uri,
    get_connections_file_path,
    validate_db_uri,
    resolve_optional_path,
)

try:
    import tomllib
except ImportError:
    tomllib = None


def load_connections_config() -> tuple[dict, str, str]:
    """
    Carga perfiles de conexión desde connections.toml o legacy env var.
    
    Returns:
        Tupla (profiles_dict, default_profile_name, source_label)
    """
    config_path = Path(get_connections_file_path())
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()

    config_dir = config_path.parent
    default_profile = os.getenv("DEEPSQL_DEFAULT_PROFILE", "").strip()

    if config_path.exists():
        if tomllib is None:
            raise RuntimeError(
                "No se puede leer connections.toml con Python < 3.11 sin tomli. "
                "Instala tomli (pip install tomli) o usa DEEPSQL_DB_URI."
            )

        with config_path.open("rb") as f:
            config_data = tomllib.load(f)

        profiles_data = config_data.get("profiles", {})
        if not isinstance(profiles_data, dict) or not profiles_data:
            raise RuntimeError(
                "connections.toml debe incluir al menos un perfil en [profiles.<nombre>]."
            )

        profiles = {}
        for profile_name, profile_data in profiles_data.items():
            if not isinstance(profile_data, dict):
                raise RuntimeError(f"El perfil '{profile_name}' debe ser un bloque TOML.")

            db_uri = str(profile_data.get("db_uri", "")).strip().strip('"').strip("'")
            if not db_uri:
                raise RuntimeError(f"El perfil '{profile_name}' no define 'db_uri'.")
            validate_db_uri(db_uri)

            oracle_mode = str(profile_data.get("oracle_mode", DEFAULT_ORACLE_MODE)).strip().lower()
            if oracle_mode not in {"thin", "thick"}:
                raise RuntimeError(
                    f"El perfil '{profile_name}' tiene oracle_mode invalido. Usa 'thin' o 'thick'."
                )

            profiles[profile_name] = {
                "name": profile_name,
                "label": str(profile_data.get("label", profile_name)).strip() or profile_name,
                "db_uri": db_uri,
                "oracle_mode": oracle_mode,
                "oracle_client_lib_dir": resolve_optional_path(
                    str(profile_data.get("oracle_client_lib_dir", DEFAULT_ORACLE_CLIENT_LIB_DIR)),
                    config_dir,
                ),
            }

        app_cfg = config_data.get("app", {})
        if isinstance(app_cfg, dict):
            app_default = str(app_cfg.get("default_profile", "")).strip()
            if app_default:
                default_profile = app_default

        source_label = f"Archivo {config_path}"
    else:
        # Fallback: usar DEEPSQL_DB_URI como perfil legacy
        legacy_uri = get_db_uri()
        validate_db_uri(legacy_uri)
        profiles = {
            "legacy_env": {
                "name": "legacy_env",
                "label": "Legacy DEEPSQL_DB_URI",
                "db_uri": legacy_uri,
                "oracle_mode": DEFAULT_ORACLE_MODE,
                "oracle_client_lib_dir": DEFAULT_ORACLE_CLIENT_LIB_DIR,
            }
        }
        source_label = "Variable DEEPSQL_DB_URI"

    if default_profile not in profiles:
        default_profile = next(iter(profiles))

    return profiles, default_profile, source_label


def get_profile(profile_name: str, profiles: dict = None) -> dict:
    """
    Obtiene perfil de conexión por nombre.
    
    Args:
        profile_name: Nombre del perfil.
        profiles: Dict de perfiles (si no se proporciona, carga globalmente).
    """
    if profiles is None:
        # Cargar perfiles globalmente si no se proporcionan
        profiles, _, _ = load_connections_config()
    
    if profile_name not in profiles:
        raise RuntimeError(f"Perfil de base de datos no encontrado: {profile_name}")
    return profiles[profile_name]

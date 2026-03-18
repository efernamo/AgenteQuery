"""
Operaciones de base de datos: conexión, dialecto, Oracle driver, etc.
"""

import os
import streamlit as st
from pathlib import Path

from langchain_community.utilities import SQLDatabase
from sqlalchemy import text

from deepsql.config import (
    SQL_TIMEOUT_MS,
    DEFAULT_ORACLE_MODE,
    ORACLE_RUNTIME_BY_PROFILE,
    DEFAULT_ORACLE_CLIENT_LIB_DIR,
)
from deepsql.dialect import get_db_dialect
from deepsql.utils import build_connection_error
from deepsql.connection import get_profile


def configure_oracle_driver(profile_name: str, profile: dict) -> str:
    """
    Configura driver Oracle (thick/thin mode).
    
    Returns:
        String describiendo el modo configurado.
    """
    db_uri = profile["db_uri"]
    dialect = get_db_dialect(db_uri)
    if dialect != "oracle":
        return None

    mode = profile.get("oracle_mode", DEFAULT_ORACLE_MODE)
    lib_dir_override = profile.get("oracle_client_lib_dir", DEFAULT_ORACLE_CLIENT_LIB_DIR)

    if mode == "thin":
        ORACLE_RUNTIME_BY_PROFILE[profile_name] = "thin"
        return "thin"

    try:
        import oracledb
    except ImportError as exc:
        raise RuntimeError(
            "No se encontro el paquete 'oracledb'. Ejecuta: pip install oracledb"
        ) from exc

    if mode != "thick":
        raise RuntimeError("oracle_mode debe ser 'thin' o 'thick'.")

    if profile_name in ORACLE_RUNTIME_BY_PROFILE:
        return ORACLE_RUNTIME_BY_PROFILE[profile_name]

    if hasattr(oracledb, "is_thin_mode") and not oracledb.is_thin_mode():
        ORACLE_RUNTIME_BY_PROFILE[profile_name] = "thick"
        return "thick"

    candidate_dirs = []
    if lib_dir_override:
        candidate_dirs.append(lib_dir_override)

    if os.name == "nt":
        common_windows_dirs = [
            r"C:\oracle\instantclient_21_13",
            r"C:\oracle\instantclient_21_12",
            r"C:\oracle\instantclient_19_22",
            r"C:\instantclient_21_13",
            r"C:\instantclient_19_22",
        ]
        candidate_dirs.extend(common_windows_dirs)

    path_dirs = [p.strip() for p in os.getenv("PATH", "").split(os.pathsep) if p.strip()]
    for path_dir in path_dirs:
        if os.path.exists(os.path.join(path_dir, "oci.dll")):
            candidate_dirs.append(path_dir)

    checked = []
    for lib_dir in candidate_dirs:
        normalized_dir = os.path.normpath(lib_dir)
        if normalized_dir in checked:
            continue
        checked.append(normalized_dir)

        if not os.path.isdir(normalized_dir):
            continue

        if not os.path.exists(os.path.join(normalized_dir, "oci.dll")):
            continue

        try:
            oracledb.init_oracle_client(lib_dir=normalized_dir)
            ORACLE_RUNTIME_BY_PROFILE[profile_name] = f"thick ({normalized_dir})"
            return "thick"
        except Exception:
            continue

    try:
        oracledb.init_oracle_client()
        ORACLE_RUNTIME_BY_PROFILE[profile_name] = "thick (PATH)"
        return "thick"
    except Exception as exc:
        if "already initialized" in str(exc).lower():
            ORACLE_RUNTIME_BY_PROFILE[profile_name] = "thick"
            return "thick"
        raise RuntimeError(
            "No se pudo iniciar Oracle en modo thick. "
            "Verifica Instant Client x64, VC++ Redistributable y oracle_client_lib_dir en el perfil. "
            f"Detalle tecnico: {exc}"
        ) from exc

    return "thick"


def make_db(selected_tables: list = None, profile_name: str = None, profiles: dict = None, default_profile: str = None) -> SQLDatabase:
    """
    Crea instancia SQLDatabase con configuración de dialecto.
    
    Args:
        selected_tables: Lista de tablas a incluir (filtro opcional).
        profile_name: Nombre del perfil a usar.
        profiles: Dict de perfiles cargados (opcional).
        default_profile: Nombre del perfil por defecto si no se especifica (opcional).
    """
    table_tuple = tuple(sorted(selected_tables)) if selected_tables else None
    
    profile = get_profile(profile_name or default_profile, profiles)
    db_uri = profile["db_uri"]
    db_dialect = get_db_dialect(db_uri)

    # PostgreSQL: read-only + timeout
    if db_dialect == "postgresql":
        connect_options = f"-c default_transaction_read_only=on -c statement_timeout={SQL_TIMEOUT_MS}"
        try:
            return SQLDatabase.from_uri(
                db_uri,
                include_tables=list(table_tuple) if table_tuple else None,
                engine_args={"connect_args": {"options": connect_options}},
            )
        except Exception as exc:
            raise build_connection_error(exc, db_uri, db_dialect) from exc

    # MySQL/MariaDB: timeout
    if db_dialect in {"mysql", "mariadb"}:
        timeout_seconds = max(1, int(SQL_TIMEOUT_MS / 1000))
        try:
            return SQLDatabase.from_uri(
                db_uri,
                include_tables=list(table_tuple) if table_tuple else None,
                engine_args={"connect_args": {"connect_timeout": timeout_seconds}},
            )
        except Exception as exc:
            raise build_connection_error(exc, db_uri, db_dialect) from exc

    # Oracle: configura driver
    if db_dialect == "oracle":
        configure_oracle_driver(profile_name or default_profile, profile)

    # Generic path (Oracle/SQL Server/SQLite)
    try:
        return SQLDatabase.from_uri(
            db_uri,
            include_tables=list(table_tuple) if table_tuple else None,
        )
    except Exception as exc:
        raise build_connection_error(exc, db_uri, db_dialect) from exc


def probe_connection(profile_name: str, profiles: dict = None, default_profile: str = None) -> str:
    """
    Prueba conectividad a un perfil de BD.
    
    Args:
        profile_name: Nombre del perfil.
        profiles: Dict de perfiles (opcional).
        default_profile: Nombre del perfil por defecto (opcional).
    
    Returns:
        Mensaje de éxito o excepción.
    """
    from deepsql.dialect import get_dialect_label
    
    profile = get_profile(profile_name, profiles)
    db_uri = profile["db_uri"]
    db_dialect = get_db_dialect(db_uri)
    db = make_db(profile_name=profile_name, profiles=profiles, default_profile=default_profile)

    query = "SELECT 1 FROM DUAL" if db_dialect == "oracle" else "SELECT 1"

    with db._engine.connect() as connection:
        connection.execute(text(query))

    return f"Conexión OK con {profile['label']} ({get_dialect_label(db_dialect)})."


@st.cache_data
def get_all_tables(profile_name: str) -> list:
    """
    Carga lista completa de tablas de un perfil.
    Usa @st.cache_data para caché automáticas en Streamlit.
    """
    db = make_db(profile_name=profile_name)
    return sorted(db.get_usable_table_names())


def get_all_tables_once(profile_name: str) -> list:
    """
    Envoltura de get_all_tables que también carga en session_state.
    Evita múltiples cálculos dentro de la misma sesión.
    """
    state_key = f"all_tables::{profile_name}"
    if state_key not in st.session_state:
        with st.spinner("Cargando catalogo de tablas..."):
            st.session_state[state_key] = get_all_tables(profile_name)
    return st.session_state[state_key]

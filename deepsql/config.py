"""
Configuración y variables de entorno.
Centraliza todos los parámetros de la aplicación.
"""

import os


def get_env_int(name: str, default_value: int) -> int:
    """Lee variable de entorno como entero."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default_value
    try:
        return int(raw_value)
    except ValueError:
        return default_value


def get_env_csv(name: str, default_csv: str) -> list[str]:
    """Lee variable de entorno como lista CSV."""
    raw_value = os.getenv(name, default_csv)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


# Configuración de Ollama
OLLAMA_MODEL = os.getenv("DEEPSQL_OLLAMA_MODEL", "deepseek-coder-v2:16b")
MODEL_OPTIONS = get_env_csv(
    "DEEPSQL_MODEL_OPTIONS",
    "qwen2.5-coder:7b,deepseek-coder-v2:16b,llama3.1:8b",
)
if OLLAMA_MODEL not in MODEL_OPTIONS:
    MODEL_OPTIONS.insert(0, OLLAMA_MODEL)

# Configuración de SQL y timeouts
SQL_TIMEOUT_MS = get_env_int("DEEPSQL_SQL_TIMEOUT_MS", 8000)
DEFAULT_LIMIT = get_env_int("DEEPSQL_DEFAULT_LIMIT", 200)
MAX_ITERATIONS = get_env_int("DEEPSQL_MAX_ITERATIONS", 15)
NUM_CTX = get_env_int("DEEPSQL_NUM_CTX", 8192)

# Configuración de Oracle
DEFAULT_ORACLE_MODE = os.getenv("DEEPSQL_ORACLE_MODE", "thick").strip().lower()
DEFAULT_ORACLE_CLIENT_LIB_DIR = os.getenv("DEEPSQL_ORACLE_CLIENT_LIB_DIR", "").strip()

# Almacenamiento runtime para Oracle
ORACLE_RUNTIME_BY_PROFILE = {}

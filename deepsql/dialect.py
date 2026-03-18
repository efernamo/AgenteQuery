"""
Funciones de soporte para dialectos de BD (PostgreSQL, Oracle, MySQL, etc).
"""


def get_db_dialect(uri: str) -> str:
    """Extrae dialecto de BD de la URI (postgresql, oracle, mysql, etc)."""
    if "://" not in uri:
        return "unknown"
    return uri.split("://", 1)[0].split("+", 1)[0].lower()


def get_dialect_label(dialect: str) -> str:
    """Retorna etiqueta legible del dialecto."""
    labels = {
        "postgresql": "PostgreSQL",
        "oracle": "Oracle",
        "mysql": "MySQL",
        "mariadb": "MariaDB",
        "mssql": "SQL Server",
        "sqlite": "SQLite",
    }
    return labels.get(dialect, dialect.upper() if dialect else "SQL")


def get_row_limit_hint(dialect: str, default_limit: int) -> str:
    """Retorna sintaxis de LIMIT recomendada para el dialecto."""
    if dialect == "oracle":
        return f"FETCH FIRST {default_limit} ROWS ONLY"
    if dialect == "mssql":
        return f"TOP {default_limit} o OFFSET ... FETCH NEXT {default_limit} ROWS ONLY"
    return f"LIMIT {default_limit}"

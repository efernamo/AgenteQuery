"""
Validación de consultas SQL y extracción desde respuestas del agente.
"""

import re


def extract_sql_tables(sql_query: str) -> set:
    """Extrae nombres de tabla de una consulta SQL."""
    if not sql_query:
        return set()
    pattern = re.compile(r'\b(?:from|join)\s+([a-zA-Z_][\w$.\"]*)', re.IGNORECASE)
    found = set()
    for match in pattern.finditer(sql_query):
        token = match.group(1).rstrip(",;")
        token = token.split(".")[-1]
        normalized = normalize_sql_identifier(token)
        if normalized:
            found.add(normalized)
    return found


def normalize_sql_identifier(name: str) -> str:
    """Normaliza identificador SQL para comparación."""
    return name.replace('"', "").strip().lower()


def validate_sql_query(sql_query: str, allowed_tables: list, db_dialect: str, default_limit: int) -> tuple[bool, str]:
    """
    Valida consulta SQL aplicando guardrails.
    
    Returns:
        Tupla (is_valid, guardrail_message)
    """
    from deepsql.dialect import get_row_limit_hint
    
    if not sql_query:
        return False, "No se pudo auditar la consulta SQL porque no se detectó sentencia."

    normalized_query = sql_query.strip().lower()
    blocked = [
        "insert", "update", "delete", "drop", "alter", "truncate", "create", "grant",
        "revoke", "comment", "copy", "call", "merge", "vacuum", "reindex", "refresh",
    ]
    blocked_pattern = re.compile(r"\b(" + "|".join(blocked) + r")\b", re.IGNORECASE)

    if blocked_pattern.search(normalized_query):
        return False, "Se detectaron comandos potencialmente peligrosos (DDL/DML)."

    if not (normalized_query.startswith("select") or normalized_query.startswith("with") or normalized_query.startswith("explain")):
        return False, "Solo se permiten sentencias de lectura (SELECT/WITH/EXPLAIN)."

    has_limit = re.search(r"\blimit\b", normalized_query, re.IGNORECASE) is not None
    has_fetch_first = re.search(r"\bfetch\s+first\s+\d+\s+rows\s+only\b", normalized_query, re.IGNORECASE) is not None
    has_fetch_next = re.search(r"\boffset\s+\d+\s+rows\s+fetch\s+next\s+\d+\s+rows\s+only\b", normalized_query, re.IGNORECASE) is not None
    has_top = re.search(r"\bselect\s+top\s+\d+\b", normalized_query, re.IGNORECASE) is not None
    has_rownum = re.search(r"\brownum\b", normalized_query, re.IGNORECASE) is not None
    has_row_limiter = has_limit or has_fetch_first or has_fetch_next or has_top or has_rownum
    aggregate_only_pattern = re.compile(r"\b(count|sum|avg|min|max)\s*\(", re.IGNORECASE)
    is_aggregate_query = bool(aggregate_only_pattern.search(normalized_query))

    if not has_row_limiter and not is_aggregate_query:
        return False, (
            "La consulta no incluye paginacion. "
            f"Se recomienda usar un limitador de filas segun el motor (ej: {get_row_limit_hint(db_dialect, default_limit)})."
        )

    allowed_set = {normalize_sql_identifier(table_name) for table_name in allowed_tables}
    referenced_set = extract_sql_tables(sql_query)

    if allowed_set and referenced_set:
        disallowed = sorted(table for table in referenced_set if table not in allowed_set)
        if disallowed:
            return False, "Se detectaron tablas fuera del contexto permitido: " + ", ".join(disallowed)

    return True, "Consulta validada por guardrails basicos."


def extract_sql_from_steps(intermediate_steps: list) -> str:
    """Extrae SQL ejecutado de los pasos intermedios del agente."""
    if not intermediate_steps:
        return None

    for step in reversed(intermediate_steps):
        if not isinstance(step, tuple) or len(step) < 1:
            continue

        action = step[0]
        tool_name = getattr(action, "tool", "")
        tool_input = getattr(action, "tool_input", None)

        if tool_name in {"sql_db_query", "sql_db_query_checker"} and tool_input:
            if isinstance(tool_input, dict):
                return tool_input.get("query") or str(tool_input)
            return str(tool_input)

    return None


def extract_sql_from_output(output_text: str) -> str:
    """Extrae SQL desde la respuesta de salida del agente."""
    if not output_text:
        return None

    code_block_match = re.search(r"```sql\s*(.*?)\s*```", output_text, re.IGNORECASE | re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    sql_used_match = re.search(r"SQL\s+USED\s*:\s*(.+)", output_text, re.IGNORECASE)
    if sql_used_match:
        return sql_used_match.group(1).strip()

    return None


def has_sql_execution(intermediate_steps: list) -> bool:
    """Verifica si el agente ejecutó realmente una consulta SQL."""
    if not intermediate_steps:
        return False

    for step in intermediate_steps:
        if not isinstance(step, tuple) or len(step) < 1:
            continue
        action = step[0]
        tool_name = getattr(action, "tool", "")
        if tool_name == "sql_db_query":
            return True

    return False

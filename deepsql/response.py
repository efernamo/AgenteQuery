"""
Construcción de respuestas finales para mostrar al usuario.
"""


def build_final_response(
    output_text: str,
    sql_query: str,
    latency_ms: float = None,
    guardrail_msg: str = None,
) -> str:
    """
    Construye respuesta final con SQL y metadatos.
    """
    output_text = (output_text or "").strip()
    if not output_text:
        output_text = "Consulta ejecutada."

    if not sql_query:
        response = output_text
    elif "```sql" in output_text.lower():
        response = output_text
    else:
        response = f"{output_text}\n\n---\n**Consulta SQL utilizada:**\n```sql\n{sql_query}\n```"

    details = []
    if latency_ms is not None:
        details.append(f"Latencia total: `{latency_ms:.0f} ms`")
    if guardrail_msg:
        details.append(f"Guardrails: {guardrail_msg}")

    if details:
        response += "\n\n---\n" + "\n".join(f"- {item}" for item in details)

    return response

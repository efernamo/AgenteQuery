"""
Construcción y ejecución del agente LangChain SQL.
"""

import streamlit as st
from langchain_community.agent_toolkits import SQLDatabaseToolkit, create_sql_agent
from langchain_ollama import ChatOllama

from deepsql.config import NUM_CTX, MAX_ITERATIONS, DEFAULT_LIMIT
from deepsql.database import make_db
from deepsql.dialect import get_db_dialect, get_dialect_label, get_row_limit_hint
from deepsql.connection import get_profile


@st.cache_resource
def get_agent_executor(
    profile_name: str,
    selected_tables_key: tuple = None,
    model_name: str = None,
):
    """
    Construye y cachea el executor del agente SQL.
    
    Args:
        profile_name: Nombre del perfil de BD a usar.
        selected_tables_key: Tupla de tablas seleccionadas (filtro opcional).
        model_name: Modelo de Ollama a usar.
    """
    db = make_db(
        selected_tables=list(selected_tables_key) if selected_tables_key else None,
        profile_name=profile_name,
    )
    
    # Obtener perfil y dialecto
    profile = get_profile(profile_name)
    db_dialect = get_db_dialect(profile["db_uri"])
    
    llm = ChatOllama(
        model=model_name,
        temperature=0,
        num_ctx=NUM_CTX,
    )
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    dialect_label = get_dialect_label(db_dialect)
    row_limit_hint = get_row_limit_hint(db_dialect, DEFAULT_LIMIT)

    custom_prefix = """You are a SQL Expert. You help users query a {dialect_label} database.

CONSTRAINTS:
- Only use tables in your SQLDatabase context
- Write-only queries forbidden: SELECT/WITH/EXPLAIN only
- Non-aggregate queries: MUST include row limiting
- Row limit syntax for {dialect_label}: {row_limit_hint}

CRITICAL ACTIONS RULES:
1. Generate ONE Thought-Action pair per turn
2. After "Action Input: [value]" STOP - wait for Observation
3. When you have the answer, use ONLY "Final Answer: [answer]"
4. NEVER mix Action and Final Answer in same response

THOUGHT-ACTION FORMAT:
Thought: [what you need to do]
Action: [tool name: sql_db_list_tables OR sql_db_schema OR sql_db_query]
Action Input: [exact input for the tool]

After I provide Observation, you continue with next Thought or Final Answer."""

    custom_suffix = """Begin!

Question: {input}

Thought: I need to check the database structure first.
{agent_scratchpad}"""

    return create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type="zero-shot-react-description",
        handle_parsing_errors=True,
        max_iterations=MAX_ITERATIONS,
        prefix=custom_prefix.format(
            dialect_label=dialect_label,
            row_limit_hint=row_limit_hint,
        ),
        suffix=custom_suffix,
        agent_executor_kwargs={
            "return_intermediate_steps": True,
            "handle_parsing_errors": True,
        },
    )

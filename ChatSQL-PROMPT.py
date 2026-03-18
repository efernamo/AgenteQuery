"""
DeepSQL Private Insights - Aplicación principal

Analítica conversacional sobre bases SQL con LLM local (Ollama).
Interfaz: Streamlit | Orquestación: LangChain | LLM: Ollama

Estructura modular:
  - deepsql/config.py: Configuración global
  - deepsql/database.py: Operaciones de BD
  - deepsql/agent.py: Construcción del agente
  - deepsql/sql_validator.py: Validación y extracción SQL
  - deepsql/*.py: Otros módulos especializados
"""

import time
import streamlit as st
from streamlit_mic_recorder import speech_to_text

# Importar módulos especializados
from deepsql.config import OLLAMA_MODEL, MODEL_OPTIONS, SQL_TIMEOUT_MS, DEFAULT_LIMIT
from deepsql.connection import load_connections_config, get_profile
from deepsql.database import make_db, probe_connection, ORACLE_RUNTIME_BY_PROFILE, get_all_tables, get_all_tables_once
from deepsql.agent import get_agent_executor
from deepsql.dialect import get_db_dialect, get_dialect_label
from deepsql.sql_validator import (
    extract_sql_from_steps,
    extract_sql_from_output,
    has_sql_execution,
    validate_sql_query,
)
from deepsql.response import build_final_response


# ============================================================================
# 1. CONFIGURACIÓN DE PÁGINA
# ============================================================================

st.set_page_config(
    page_title="DeepSQL Private Insights",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# 2. ESTILOS CSS
# ============================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #e3e3e3; }
    [data-testid="stSidebar"] { background-color: #161a1e !important; border-right: 1px solid #2d333b; }
    .stChatMessage { border-radius: 12px; border: 1px solid #333; padding: 20px; margin-bottom: 15px; }
    .hero-text {
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; text-align: center; margin-bottom: 0.2rem;
    }
    .stStatusWidget { border-radius: 10px; border: 1px solid #4facfe; }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# 3. CARGA GLOBAL DE PERFILES
# ============================================================================

CONNECTION_PROFILES, DEFAULT_PROFILE_NAME, CONNECTION_SOURCE = load_connections_config()
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    st.divider()

    profile_names = list(CONNECTION_PROFILES.keys())
    selected_profile_index = profile_names.index(DEFAULT_PROFILE_NAME) if DEFAULT_PROFILE_NAME in profile_names else 0
    selected_profile = st.selectbox(
        "Base de datos",
        options=profile_names,
        index=selected_profile_index,
        format_func=lambda name: f"{CONNECTION_PROFILES[name]['label']} ({get_dialect_label(get_db_dialect(CONNECTION_PROFILES[name]['db_uri']))})",
        help="Selecciona el perfil de conexión definido en connections.toml.",
    )
    active_profile = get_profile(selected_profile)
    active_dialect = get_db_dialect(active_profile["db_uri"])

    model_index = MODEL_OPTIONS.index(OLLAMA_MODEL) if OLLAMA_MODEL in MODEL_OPTIONS else 0
    selected_model = st.selectbox(
        "Modelo LLM",
        options=MODEL_OPTIONS,
        index=model_index,
        help="Selecciona el modelo de Ollama para esta sesión.",
    )
    st.write(f"**Modelo activo:** `{selected_model}`")
    st.write(f"**Database:** `{get_dialect_label(active_dialect)}`")
    st.caption(f"Perfil activo: {active_profile['label']}")
    st.caption(f"Origen de conexiones: {CONNECTION_SOURCE}")

    if st.button("🔌 Probar conexión", use_container_width=True):
        with st.spinner("Verificando conexión del perfil activo..."):
            try:
                probe_msg = probe_connection(selected_profile)
                st.success(probe_msg)
            except Exception as exc:
                st.error(f"No fue posible conectar: {exc}")

    st.caption(
        f"Timeout referencia: {SQL_TIMEOUT_MS} ms | Limite recomendado: {DEFAULT_LIMIT} filas"
    )
    if active_dialect == "oracle":
        oracle_runtime_mode = ORACLE_RUNTIME_BY_PROFILE.get(selected_profile) or active_profile.get("oracle_mode", "thick")
        st.caption(f"Driver Oracle: modo `{oracle_runtime_mode}`")

    col_a, col_b = st.columns([0.75, 0.25])
    with col_a:
        st.markdown("### 🧩 Filtro de Tablas")
    with col_b:
        if st.button("Recargar", use_container_width=True):
            get_all_tables.clear()
            st.session_state.pop(f"all_tables::{selected_profile}", None)
            st.rerun()

    try:
        all_tables = get_all_tables_once(selected_profile)
    except Exception as exc:
        st.error(f"No se pudo cargar el catalogo de tablas: {exc}")
        all_tables = []
    st.caption("Si seleccionas tablas, el agente solo consultará esas tablas.")
    selected_tables = st.multiselect(
        "Tablas permitidas (opcional):",
        options=all_tables,
        default=[],
        key=f"selected_tables::{selected_profile}",
    )

    prewarm_enabled = st.toggle(
        "Precalentar agente",
        value=True,
        help="Preconstruye el agente al cambiar modelo o tablas para acelerar el primer prompt.",
    )

    if selected_tables:
        st.success(f"Filtro activo: {len(selected_tables)} tabla(s)")
    else:
        st.info("Sin filtro: se usan todas las tablas.")

    st.divider()
    if st.button("🗑️ Limpiar Conversación", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption("Desarrollado con LangChain 0.3 + Streamlit")

# Precompute scope key once and optionally prewarm when configuration changes.
selected_tables_key = tuple(sorted(selected_tables)) if selected_tables else None
agent_signature = (selected_profile, selected_model, selected_tables_key)

if prewarm_enabled and st.session_state.get("agent_warmed_signature") != agent_signature:
    with st.spinner("Precalentando agente para acelerar el primer mensaje..."):
        get_agent_executor(selected_profile, selected_tables_key, selected_model)
    st.session_state.agent_warmed_signature = agent_signature

# --- 5. ESTRUCTURA DE LA INTERFAZ ---
st.markdown('<h1 class="hero-text">DeepSQL Intelligence</h1>', unsafe_allow_html=True)
model_brand = selected_model.split(":", 1)[0].split("-", 1)[0].strip()
model_brand = model_brand.capitalize() if model_brand else "LLM"
st.markdown(
    f"<p style='text-align: center; color: #848d97; margin-bottom: 2rem;'>Analista de datos privado impulsado por {model_brand}</p>",
    unsafe_allow_html=True,
)

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola. Estoy conectado a tu base de datos. ¿En qué puedo ayudarte hoy?"}
    ]

# Renderizar mensajes del historial
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

# --- 6. MANEJO DE PREGUNTAS (TEXTO + VOZ) ---
col_empty, col_mic = st.columns([0.9, 0.1])
with col_mic:
    texto_voz = speech_to_text(
        start_prompt="🎤",
        stop_prompt="🛑",
        language='es',
        key='speech_key'
    )

if texto_voz:
    st.session_state.voz_input = texto_voz.strip()

chat_prompt = st.chat_input("Ej: ¿Cuáles son las 3 ramas con más servicios?")
final_prompt = None

if chat_prompt and chat_prompt.strip():
    final_prompt = chat_prompt.strip()
elif st.session_state.get("voz_input"):
    final_prompt = st.session_state.voz_input
    st.session_state.voz_input = None

if final_prompt:
    # Guardar y mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(final_prompt)

    # Generar respuesta del agente
    with st.chat_message("assistant", avatar="🤖"):
        with st.status("🧠 Procesando consulta SQL...", expanded=True) as status:
            try:
                # Ejecución del agente
                start_time = time.perf_counter()
                agent_executor = get_agent_executor(selected_profile, selected_tables_key, selected_model)
                response = agent_executor.invoke({"input": final_prompt})
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                output_text = response.get("output", "")
                intermediate_steps = response.get("intermediate_steps", [])
                sql_used = extract_sql_from_steps(intermediate_steps) or extract_sql_from_output(output_text)
                executed_sql = has_sql_execution(intermediate_steps)

                if not executed_sql:
                    output_text = (
                        "No pude confirmar la ejecucion real de la consulta en la base de datos. "
                        "Reintenta la pregunta o ajusta el filtro de tablas para forzar una ejecucion valida."
                    )

                scoped_tables = selected_tables if selected_tables else all_tables
                is_valid, guardrail_msg = validate_sql_query(sql_used, scoped_tables, active_dialect, DEFAULT_LIMIT)
                if not executed_sql:
                    is_valid = False
                    guardrail_msg = "No se detecto ejecucion real via sql_db_query."

                full_response = build_final_response(
                    output_text,
                    sql_used,
                    latency_ms=elapsed_ms,
                    guardrail_msg=guardrail_msg,
                )
                
                status.update(label="✅ Análisis finalizado", state="complete", expanded=False)
                if not is_valid:
                    st.warning(f"Guardrails: {guardrail_msg}")
                st.markdown(full_response)
                
                # Guardar respuesta en el historial
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                status.update(label="❌ Error en el proceso", state="error")
                error_text = f"Lo siento, ocurrió un error: {str(e)}"
                st.error(error_text)
                st.session_state.messages.append({"role": "assistant", "content": error_text})

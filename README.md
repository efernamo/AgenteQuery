# DeepSQL Private Insights

Aplicación de analítica conversacional sobre bases SQL (PostgreSQL, Oracle, MySQL/MariaDB, SQL Server, SQLite), construida con **Streamlit** como frontend, **LangChain** como capa de orquestación y **Ollama** como motor LLM para traducir lenguaje natural a SQL ejecutable.

---

## 1) Propósito

El objetivo del proyecto es permitir que un usuario:

- consulte datos de una base SQL usando lenguaje natural (chat o voz),
- reciba una respuesta en español,
- vea la sentencia SQL utilizada para obtener el resultado,
- limite el contexto del agente seleccionando tablas específicas cuando la base tiene muchas tablas.

---

## 2) Arquitectura General

### Componentes

1. **Frontend/UI**: `Streamlit`
   - Renderiza chat, historial, estado de ejecución y controles laterales.
   - Captura input por texto y voz.

2. **Capa de Orquestación**: `LangChain SQL Agent`
   - Usa `create_sql_agent` con `SQLDatabaseToolkit`.
   - Decide qué herramientas SQL usar (`list tables`, `inspect schema`, `query`, etc.).

3. **Modelo LLM**: `ChatOllama` (configurable entre múltiples modelos)
   - Por defecto: `deepseek-coder-v2:16b` (se puede cambiar a `qwen2.5-coder:7b` ⭐ recomendado por rapidez).
   - Interpreta intención del usuario.
   - Genera pasos de razonamiento orientados a consultas SQL.
   - **Ver sección 8.5** para cambiar modelo y opciones disponibles.

4. **Capa de Datos**: `Base SQL configurable`
   - Fuente de verdad para ejecución real de consultas.
   - Conectada mediante `SQLDatabase.from_uri(DB_URI)`.

---

## 3) Comunicación entre capas

### Flujo de alto nivel

1. Usuario escribe o dicta una pregunta en la UI.
2. Streamlit envía el prompt a `agent_executor.invoke({...})`.
3. El agente (LangChain + LLM) decide herramientas SQL y construye la consulta.
4. La consulta se ejecuta en PostgreSQL a través de `SQLDatabase`.
5. El resultado vuelve al agente y luego a Streamlit.
6. El script extrae el SQL real ejecutado desde `intermediate_steps`.
7. La UI muestra respuesta + bloque final con SQL utilizado.

### Diagrama de secuencia

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant S as Streamlit (UI)
    participant A as LangChain SQL Agent
    participant L as LLM (Ollama - qwen o deepseek)
    participant D as Base de Datos SQL

    U->>S: Pregunta (texto o voz)
    S->>A: invoke({input: prompt})
    A->>L: Interpretar intención y plan SQL
    L-->>A: Acción / SQL a ejecutar
    A->>D: Ejecuta SQL (vía SQLDatabase)
    D-->>A: Resultados
    A-->>S: output + intermediate_steps
    S->>S: Extrae SQL ejecutado
    S-->>U: Respuesta breve + SQL final
```

---

## 4) Script principal y responsabilidades

Archivo principal: `ChatSQL-PROMPT.py`

### Bloques funcionales

- **Configuración de página y estilos**
  - `st.set_page_config(...)`
  - CSS personalizado para UI oscura y chat.

- **Conexión y metadatos SQL**
  - `DB_URI` define conexión PostgreSQL.
  - `get_all_tables()` obtiene tablas disponibles (cacheado con TTL).

- **Construcción del agente**
  - `get_agent_executor(selected_tables=None)`:
    - crea `SQLDatabase` con filtro opcional (`include_tables`),
    - inicializa `ChatOllama`,
    - define `custom_prefix` y `custom_suffix`,
    - habilita `return_intermediate_steps` para capturar SQL real.

- **Post-procesado de salida**
  - `extract_sql_from_steps(...)`: recupera la sentencia desde pasos intermedios.
  - `build_final_response(...)`: garantiza mostrar SQL al final de la respuesta.

- **Entrada multimodal (texto + voz)**
  - `st.chat_input(...)` para chat.
  - `speech_to_text(...)` para micrófono.
  - prioridad: texto, luego voz.

- **Sidebar de configuración**
  - selección opcional de tablas con `st.multiselect(...)`.
  - al seleccionar tablas, el agente solo consulta ese subconjunto.

---

## 5) Filtro de tablas para bases grandes

Cuando la base contiene muchas tablas, el filtro de tablas permite:

- reducir ruido de contexto para el LLM,
- disminuir errores en joins por tablas irrelevantes,
- mejorar latencia y calidad de respuesta,
- controlar explícitamente el alcance de consulta.

Comportamiento:

- **Sin selección**: se usa toda la base.
- **Con selección**: el agente se limita a las tablas elegidas (`include_tables`).

---

## 6) Ejecución local

## Requisitos

- Python 3.10+
- Base SQL accesible desde la máquina local
- Ollama instalado y modelo `deepseek-coder-v2:16b` descargado

## Dependencias Python sugeridas

```bash
pip install streamlit pandas langchain langchain-community langchain-ollama streamlit-mic-recorder
```

## Lanzar la app

```bash
streamlit run ChatSQL-PROMPT.py
```

## Instalación automática en Windows (1 comando)

Se incluye un instalador que puede:

- instalar Python 3.11 (via winget),
- instalar Ollama,
- crear `.venv`,
- instalar dependencias Python,
- descargar el modelo `deepseek-coder-v2:16b`,
- lanzar la app.

### Opción A (PowerShell)

```powershell
.\setup_deepsql.ps1 -LaunchApp
```

### Opción B (CMD)

```bat
setup_deepsql.bat -LaunchApp
```

Opciones útiles:

- `-Model qwen2.5-coder:7b` para cambiar modelo a descargar.
- `-SkipModelPull` para omitir descarga del modelo.
- `-SkipPythonInstall` o `-SkipOllamaInstall` si ya están instalados.

Nota: requiere `winget` disponible para instalación automática de Python/Ollama.

## Desinstalación automática y limpieza

Se incluye desinstalador para limpiar lo generado por el setup:

- elimina `.venv` y caches locales,
- elimina modelo de Ollama descargado,
- puede eliminar `.ollama` completo,
- si el setup instaló Python/Ollama (según estado registrado), intenta desinstalarlos.

### Opción A (PowerShell)

```powershell
.\uninstall_deepsql.ps1
```

### Opción B (CMD)

```bat
uninstall_deepsql.bat
```

Opciones útiles:

- `-PurgeOllamaHome` para forzar eliminación de `%USERPROFILE%\.ollama`.
- `-UninstallPython` para forzar desinstalar Python 3.11 por winget.
- `-UninstallOllama` para forzar desinstalar Ollama por winget.
- `-Force` para no pedir confirmaciones.

Nota: `setup_deepsql.ps1` guarda un estado en `.deepsql-install-state.json` para que el desinstalador sepa qué limpiar automáticamente.

## Configuración unificada de conexiones (recomendada)

La app ahora permite definir multiples conexiones en un solo archivo y seleccionar la base desde la UI (sidebar), sin tocar código.

### 1. Crea el archivo de perfiles

Usa `connections.toml.example` como plantilla y crea `connections.toml` en la raíz del proyecto.

Ejemplo:

```toml
[app]
default_profile = "pg_local"

[profiles.pg_local]
label = "PostgreSQL Local"
db_uri = "postgresql+psycopg2://usuario:clave@localhost:5432/mi_db"

[profiles.oracle_qa]
label = "Oracle QA"
db_uri = "oracle+oracledb://usuario:clave@host:1521/?service_name=DB1"
oracle_mode = "thick"
oracle_client_lib_dir = "./oracle/instantclient_21_13"
```

`oracle_client_lib_dir` acepta rutas absolutas o relativas. Si es relativa, se resuelve desde la carpeta donde está `connections.toml`.

### 2. Variables de entorno globales (opcional)

Estas variables siguen siendo útiles para ajustar comportamiento general:

```powershell
# Recomendado: qwen2.5-coder:7b (rápido, especializado en SQL)
$env:DEEPSQL_OLLAMA_MODEL="qwen2.5-coder:7b"

# Alternativa: deepseek-coder-v2:16b (más potente, consume más recursos)
# $env:DEEPSQL_OLLAMA_MODEL="deepseek-coder-v2:16b"

$env:DEEPSQL_SQL_TIMEOUT_MS="8000"
$env:DEEPSQL_DEFAULT_LIMIT="200"
$env:DEEPSQL_MAX_ITERATIONS="15"
$env:DEEPSQL_NUM_CTX="8192"
$env:DEEPSQL_DEFAULT_PROFILE="pg_local"
$env:DEEPSQL_CONNECTIONS_FILE="connections.toml"
```

### 3. Selecciona la base en la UI

Al arrancar Streamlit, usa el selector **Base de datos** en la barra lateral. El usuario final solo elige perfil y consulta.

También puedes usar el botón **Probar conexión** para validar rápidamente el perfil activo antes de hacer preguntas al agente.

### Compatibilidad legacy (sin archivo TOML)

Si no existe `connections.toml`, la app cae automáticamente a `DEEPSQL_DB_URI` como único perfil.

PowerShell:

```powershell
$env:DEEPSQL_DB_URI="postgresql+psycopg2://usuario:clave@localhost:5432/mi_db"
```

CMD:

```bat
set "DEEPSQL_DB_URI=postgresql+psycopg2://usuario:clave@localhost:5432/mi_db"
```

Notas:

- Si la clave tiene caracteres especiales como `@`, `:`, `/`, `#`, `?`, debes aplicar URL encoding.
- Para Oracle en modo thick, puedes definir `oracle_client_lib_dir` por perfil en `connections.toml`.

---

## 7) Configuración clave

En `ChatSQL-PROMPT.py`:

- `connections.toml`: catálogo de perfiles de conexión (recomendado).
- `DEEPSQL_CONNECTIONS_FILE`: ruta del archivo TOML de conexiones.
- `DEEPSQL_DEFAULT_PROFILE`: perfil inicial seleccionado en la UI.
- `DEEPSQL_DB_URI`: fallback legacy si no existe archivo TOML.
- `DEEPSQL_OLLAMA_MODEL`: modelo LLM a usar. **Ver sección 8.5** para seleccionar entre `qwen2.5-coder:7b` (⭐ recomendado por rapidez y especialización SQL), `deepseek-coder-v2:16b`, `llama3.1:8b`, etc. Defaults a `deepseek-coder-v2:16b` si no se configura.
- `DEEPSQL_MODEL_OPTIONS`: lista CSV de modelos disponibles en el selector UI (default: `qwen2.5-coder:7b,deepseek-coder-v2:16b,llama3.1:8b`).
- `DEEPSQL_NUM_CTX`, `temperature`: comportamiento y contexto del modelo.
- `DEEPSQL_MAX_ITERATIONS`: profundidad de exploración del agente.
- `include_tables`: control de alcance por filtro de tablas.
- `DEEPSQL_SQL_TIMEOUT_MS`: timeout por sentencia SQL (aplicado por dialecto cuando es soportado).
- `DEEPSQL_DEFAULT_LIMIT`: limite recomendado en consultas generadas.

---

## 8) Consideraciones de seguridad

- El script muestra SQL ejecutado para auditoría.
- Recomendado usar un usuario de BD con permisos mínimos necesarios.
- Se aplica `default_transaction_read_only=on` y `statement_timeout` en PostgreSQL.
- Para otros motores, se recomienda reforzar solo lectura con permisos del usuario de BD y políticas nativas del motor.
- Credenciales y parametros sensibles pueden gestionarse por perfiles (`connections.toml`) o variables de entorno.
- Para entornos productivos, agregar validación de consultas y políticas de lectura/escritura.

---

## 8.5) Selección y configuración de modelos LLM

### Modelos disponibles

La app viene pre-configurada con `deepseek-coder-v2:16b`, pero tienes varias opciones según tu hardware y presupuesto de latencia:

| Modelo | Tamaño | Ventajas | Desventajas | Recomendado para |
|--------|--------|----------|-------------|------------------|
| **qwen2.5-coder:7b** | 7B | ✅ Muy rápido, excelente formato ReAct, ligero | Menos powerful que deepseek | **⭐ Producción / Equipos limitados** |
| **deepseek-coder-v2:16b** | 16B | ✅ Más potente, mejor razonamiento complejo | Más pesado, consume más RAM | Análisis complejos, exploraciones profundas |
| **llama3.1:8b** | 8B | ✅ Rápido, versátil | Menos especializado en SQL | Cuando necesitas versatilidad general |
| **qwen2.5-coder:32b** | 32B | ✅ Máxima potencia | Muy pesado, lento | Servidor con GPU dedicada |

### ⭐ Recomendación: qwen2.5-coder:7b

Para la mayoría de casos de uso, **`qwen2.5-coder:7b` es la mejor opción** porque:

1. **Entrenamiento especializado en SQL**: Fue entrenado específicamente en código SQL y consultas a bases de datos.
2. **Mejor formato ReAct**: Respeta más consistentemente el formato Thought-Action-Observation del agente, evitando errores de parseo.
3. **Rapidez**: ~2-3x más rápido que deepseek-coder-v2 sin sacrificar calidad en consultas SQL.
4. **Menor consumo de RAM**: Requiere ~5GB vs. ~9GB de deepseek.
5. **Instalación automática**: El script `setup_deepsql.ps1` puede descargar qwen2.5-coder:7b con el parámetro `-Model`.

### Cómo cambiar el modelo

#### Opción A: En la UI (sin reiniciar)

1. Abre la aplicación: `.\.venv\Scripts\python.exe -m streamlit run ChatSQL-PROMPT.py`
2. En la barra lateral, ve al selector **Modelo LLM**.
3. Elige el modelo que desees.
4. El modelo se descargará automáticamente en segundo plano si no existe.

#### Opción B: Configurar como modelo por defecto

En PowerShell:

```powershell
$env:DEEPSQL_OLLAMA_MODEL="qwen2.5-coder:7b"
.\.venv\Scripts\python.exe -m streamlit run ChatSQL-PROMPT.py
```

O defines permanentemente en tu perfil de PowerShell:

```powershell
# Agrega al final de $PROFILE (Editor: notepad $PROFILE)
[Environment]::SetEnvironmentVariable("DEEPSQL_OLLAMA_MODEL", "qwen2.5-coder:7b", "User")
```

En CMD:

```batch
set "DEEPSQL_OLLAMA_MODEL=qwen2.5-coder:7b"
python -m streamlit run ChatSQL-PROMPT.py
```

#### Opción C: Durante la instalación (recomendado para nuevos usuarios)

Si aún no tienes la aplicación instalada, usa el script con el parámetro `-Model`:

```powershell
# Descargar e instalar con qwen2.5-coder:7b en lugar de deepseek
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_deepsql.ps1 -Model qwen2.5-coder:7b -LaunchApp
```

Esto garantiza que la instalación y el modelo predeterminado sean consistentes.

### Descargar modelos adicionales (sin instalar)

Si ya tienes Ollama instalado, puedes descargar otros modelos sin reinstalar la app:

```powershell
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:32b
ollama pull llama3.1:8b
```

Luego selecciona el modelo desde la UI.

### Compatibilidad con versiones antiguas

Si tienes código que referencia `deepseek-coder-v2:16b` de forma hardcodeada, puedes:

1. Actualizar manualmente: busca `deepseek-coder-v2:16b` en `ChatSQL-PROMPT.py` línea ~125 (`OLLAMA_MODEL = ...`).
2. O mejor: usa la variable de entorno `DEEPSQL_OLLAMA_MODEL` (recomendado en `connections.toml`).

---

## 9) Observabilidad y depuración

- `verbose=True` en el agente permite ver más trazas en consola.
- `st.status(...)` muestra estado de ejecución en UI.
- Al tener `intermediate_steps`, se puede inspeccionar el SQL real usado por el agente.
- Se reporta latencia total por consulta en la respuesta final.
- Se ejecutan guardrails basicos para auditar SQL detectado (solo lectura, LIMIT y tablas permitidas).

---

## 10) Posibles mejoras futuras

- Modo estricto de solo lectura (bloqueo de DDL/DML).
- Timeout y cancelación de consultas largas.
- Selector rápido por nombre de tabla (búsqueda incremental).
- Métricas de latencia por etapa (UI, LLM, DB).
- Desacoplar configuración en `.env` + `pydantic-settings`.

---

## 11) Resumen arquitectónico

Este proyecto implementa una arquitectura **LLM-to-SQL** con separación clara de responsabilidades:

- **Streamlit**: experiencia de usuario y orquestación de interacción.
- **LangChain**: puente entre intención humana y herramientas SQL.
- **Ollama/LLM**: traducción semántica a consultas SQL.
- **Motor SQL configurado**: ejecución y resultados confiables.

La comunicación entre estas capas permite consultas naturales, auditables y controladas por contexto de tablas, manteniendo una interfaz simple para usuarios no técnicos.

---

## 12) Propuesta técnica favorable (escenario: miles de tablas y alto volumen)

Para una base con muchísimas tablas y datos, la estrategia más favorable es pasar de un agente único a una arquitectura por etapas (pipeline), donde cada componente hace una tarea concreta y medible.

### Objetivo de la propuesta

- mejorar precisión de SQL en esquemas grandes,
- reducir latencia de respuestas,
- evitar consultas costosas o peligrosas,
- mantener trazabilidad completa (qué se ejecutó y por qué).

### Arquitectura objetivo (v2 escalable)

1. **Capa de Ingesta de Esquema (offline + cacheada)**
  - Extrae metadata de PostgreSQL: tablas, columnas, tipos, PK/FK, índices, cardinalidades aproximadas.
  - Genera un catálogo técnico (`table_catalog`) con descripciones cortas por tabla/columna.
  - Actualización programada (ej. cada noche o por trigger de migraciones).

2. **Capa de Retrieval de Tablas (online, previa al SQL agent)**
  - Entrada: pregunta del usuario.
  - Salida: top-k tablas candidatas (ej. 8-20), usando:
    - búsqueda semántica sobre el catálogo,
    - reglas por palabras clave,
    - expansión por FK para joins.
  - Resultado: contexto pequeño y relevante para el LLM.

3. **Generación SQL con LLM + restricciones fuertes**
  - El agente solo ve tablas candidatas.
  - Reglas:
    - solo lectura,
    - `LIMIT` por defecto,
    - sin `SELECT *` salvo excepción,
    - timeout de ejecución.

4. **Validación previa a ejecución (guardrails)**
  - Parser SQL + checklist:
    - sentencia permitida (`SELECT`, `WITH`, `EXPLAIN`),
    - tablas dentro del contexto permitido,
    - prohibición DDL/DML,
    - costo estimado aceptable (opcional con `EXPLAIN`).

5. **Ejecución y post-procesado**
  - Ejecuta SQL validado.
  - Devuelve respuesta breve + SQL final + metadatos mínimos (tiempo/filas).

6. **Observabilidad y evaluación continua**
  - Telemetría por etapa:
    - latencia retrieval,
    - latencia LLM,
    - latencia DB,
    - tasa de error SQL,
    - exactitud por benchmark interno.

### Diagrama de componentes (v2)

```mermaid
flowchart LR
   U[Usuario] --> UI[Streamlit UI]
   UI --> RT[Router/Tabla Retrieval]
   RT --> AG[SQL Agent + LLM]
   AG --> GV[Guardrails SQL]
   GV --> DB[(PostgreSQL)]
   DB --> RS[Resultados]
   RS --> UI

   META[(Catálogo de esquema)] --> RT
   META --> AG
   OBS[Logs/Métricas] --- UI
   OBS --- RT
   OBS --- AG
   OBS --- DB
```

---

## 13) Workthrough técnico (implementación paso a paso)

Este walkthrough está orientado a evolucionar desde la versión actual sin romper funcionalidad.

### Fase 1 — Hardening mínimo (1-2 días)

1. Mover `DB_URI` a variables de entorno.
2. Forzar modo lectura (bloqueo de DDL/DML).
3. Añadir timeout SQL y `LIMIT` por defecto.
4. Registrar latencias básicas en cada consulta.

**Resultado esperado:** seguridad y estabilidad base sin cambiar UX.

### Fase 2 — Retrieval de tablas (2-4 días)

1. Crear extractor de metadatos:
  - tablas, columnas, FK, índices.
2. Construir un índice semántico de descripciones (embeddings).
3. Implementar `retrieve_tables(question) -> top_k_tables`.
4. Alimentar `include_tables` con ese resultado.

**Resultado esperado:** el LLM deja de ver cientos/miles de tablas y mejora precisión.

### Fase 3 — Guardrails SQL robustos (2-3 días)

1. Validar SQL antes de ejecutar:
  - tipo de sentencia permitido,
  - tablas permitidas,
  - tamaño/costo estimado.
2. Si falla validación, pedir regeneración al agente con feedback específico.
3. Exponer motivo de bloqueo al usuario en lenguaje claro.

**Resultado esperado:** menos errores y menos consultas caras/inseguras.

### Fase 4 — Benchmark y selección de modelo (2-5 días)

1. Crear dataset interno de 50-200 preguntas reales.
2. Evaluar modelos candidatos (ej. DeepSeek/Qwen/SQLCoder) con mismas reglas.
3. Medir:
  - exactitud SQL ejecutable,
  - exactitud de respuesta,
  - latencia p95,
  - tasa de retries.
4. Elegir modelo ganador por entorno (local GPU/CPU).

**Resultado esperado:** decisión objetiva de modelo, no por intuición.

---

## 14) Workthrough operativo de una consulta (runtime)

Ejemplo: “¿Cuántas sucursales activas hay este mes?”

1. **UI recibe prompt**
  - texto o voz transcrita.

2. **Router elige tablas**
  - detecta intención “sucursales” y propone: `branches`, `appointments` (si aplica), etc.

3. **Agente genera SQL sobre contexto reducido**
  - evita tablas irrelevantes.

4. **Guardrails validan**
  - sentencia de solo lectura,
  - tablas permitidas,
  - `LIMIT` y costo razonable.

5. **DB ejecuta**
  - retorna datos y tiempo de ejecución.

6. **Post-procesado responde**
  - resumen breve en español,
  - bloque `Consulta SQL utilizada`,
  - opcional: latencia y número de filas.

---

## 15) KPIs recomendados para aceptar la mejora

- **Precisión SQL ejecutable** >= 90%
- **Precisión de respuesta** >= 85%
- **Latencia p95 end-to-end** <= 8 s (consulta típica)
- **Tasa de errores SQL** <= 5%
- **Tasa de bloqueos por guardrails** (monitorizar tendencia)

Estos KPIs permiten controlar que la arquitectura escale en calidad y costo cuando el esquema y el volumen de datos crecen.

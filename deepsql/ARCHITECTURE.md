# Estructura Modular de DeepSQL

Este directorio contiene los módulos que fragmentan la lógica de `ChatSQL-PROMPT.py` para mejorar legibilidad y mantenibilidad.

## Módulos

- **config.py** — Variables de entorno, configuración global (Ollama, SQL timeouts, Oracle)
- **utils.py** — Utilidades: gestión de URIs, validación, manejo de errores  
- **dialect.py** — Soporte para dialectos (PostgreSQL, Oracle, MySQL, SQL Server, SQLite)
- **connection.py** — Carga y gestión de perfiles de conexión desde `connections.toml`
- **database.py** — Operaciones de BD: crear conexiones, configurar drivers Oracle, probar conexiones
- **sql_validator.py** — Validación de SQL y extracción desde respuestas del agente
- **agent.py** — Construcción y cacheo del executor del agente LangChain
- **response.py** — Formateo de respuestas finales con SQL y metadatos

## Dependencias entre módulos

```
config.py
  ↓
utils.py → dialect.py
  ↓
connection.py → database.py
  ↓
agent.py ← sql_validator.py ← response.py
  ↑
ChatSQL-PROMPT.py (orquestador principal)
```

## Ventajas

✅ **Legibilidad**: Cada módulo tiene responsabilidad única y clara  
✅ **Mantenibilidad**: Cambios localizados sin afectar otras partes  
✅ **Testing**: Facilita pruebas unitarias de cada componente  
✅ **Reutilización**: Funciones pueden importarse desde otros scripts  

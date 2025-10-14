import sys
import logging
from flask import Flask, request, jsonify
import subprocess
import json
import os
from functools import wraps

# Importa las herramientas y sus manifiestos desde tools.py
from tools import AVAILABLE_TOOLS, TOOL_MANIFEST, AGENT_MEMORY_FILE

# --- CONFIGURACIÓN ---
OLLAMA_MODEL = 'granite4:micro-h'

# Clave API para autenticación (se recomienda usar variables de entorno en producción)
API_KEY = os.environ.get("AGENT_API_KEY")

# Configura el logger
logging.basicConfig(
    level=logging.INFO, # Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/epardo/projects/python_agent_cli/agent_server_debug.log"),
        logging.StreamHandler(sys.stdout) # Para ver logs en la consola también
    ]
)

app = Flask(__name__)

# Decorador para requerir la clave API
def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if not API_KEY:
            logging.error("AGENT_API_KEY no está configurada en el entorno.")
            return jsonify({"error": "Configuración del servidor incompleta: AGENT_API_KEY no definida."}), 500

        request_api_key = request.headers.get('X-API-Key')
        if not request_api_key or request_api_key != API_KEY:
            logging.warning(f"Intento de acceso no autorizado con clave: {request_api_key}")
            return jsonify({"error": "Acceso no autorizado."}), 401
        return view_function(*args, **kwargs)
    return decorated_function

# --- FUNCIONES DEL ORQUESTADOR (ADAPTADAS PARA EL SERVIDOR) ---

def load_long_term_memory() -> str:
    """Carga las directivas y memoria a largo plazo del agente."""
    try:
        with open(AGENT_MEMORY_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.info(f"Advertencia: No se encontró el archivo de memoria del agente en {AGENT_MEMORY_FILE}.")
        return "Advertencia: No se encontró el archivo de memoria del agente."

def build_system_prompt(long_term_memory: str, conversation_history: list, user_request: str) -> str:
    """Construye el prompt completo para el modelo de Ollama."""
    tools_json_str = json.dumps(TOOL_MANIFEST, indent=2)
    history_str = "\n".join(conversation_history)
    
    prompt = f"""
Eres un asistente experto de línea de comandos. Tu nombre es 'PyAgent'.
Responde siempre en español.

### MEMORIA A LARGO PLAZO Y DIRECTIVAS ###
{long_term_memory}

### HERRAMIENTAS DISPONIBLES ###
Tienes acceso a las siguientes herramientas. Para usarlas, responde ÚNICAMENTE con un objeto JSON válido:
{tools_json_str}

### HISTORIAL DE LA CONVERSACIÓN ###
{history_str}

### TAREA ACTUAL ###
Usuario: {user_request}
Responde a la petición del usuario. Si necesitas usar una herramienta, genera el JSON correspondiente. Si tienes la respuesta final, proporciónala directamente.
"""
    return prompt

def call_ollama(prompt: str) -> str:
    """Llama al modelo de Ollama a través de la línea de comandos."""
    command = ["/usr/local/bin/ollama", "run", OLLAMA_MODEL, prompt]

    logging.info(f"Llamando a Ollama con comando: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, check=False)    
    if result.returncode != 0:
        logging.error(f"Error al llamar a Ollama: {result.stderr}")
        return json.dumps({"error": f"Error al llamar a Ollama: {result.stderr}"})
    
    return result.stdout.strip()

def execute_tool(tool_name: str, parameters: dict) -> str:
    """Busca y ejecuta una herramienta del toolbelt."""
    if tool_name not in AVAILABLE_TOOLS:
        logging.warning(f"Herramienta '{tool_name}' no existe.")
        return json.dumps({"error": f"La herramienta '{tool_name}' no existe."})
    
    logging.info(f"Ejecutando herramienta: {tool_name} con parámetros {parameters}")
    
    # --- CAPA DE SEGURIDAD (¡ADAPTADA PARA SERVIDOR!) ---
    # En un entorno de servidor, la confirmación interactiva no es posible.
    # Aquí se podría implementar:
    # 1. Una lista blanca de comandos seguros.
    # 2. Un sistema de aprobación externo (ej. enviar a un humano vía API).
    # 3. Un flag de configuración para permitir/denegar acciones peligrosas.
    # Por simplicidad en este prototipo, asumimos que las herramientas son seguras o pre-aprobadas.
    # Para run_shell_command y write_file, se recomienda extrema precaución.
    
    try:
        tool_function = AVAILABLE_TOOLS[tool_name]
        result = tool_function(**parameters)
        
        # Convierte el resultado a una cadena JSON para el historial
        return json.dumps(result) if isinstance(result, dict) else str(result)
    except Exception as e:
        logging.error(f"Error al ejecutar la herramienta '{tool_name}': {e}")
        return json.dumps({"error": f"Error al ejecutar la herramienta '{tool_name}': {e}"})

# --- RUTAS DEL SERVIDOR ---

@app.route('/chat', methods=['POST'])
@require_api_key
def chat():
    data = request.json
    user_message = data.get('user_message')
    conversation_history = data.get('history', [])

    if not user_message:
        return jsonify({"error": "user_message es requerido"}), 400
    
    logging.info(f"Mensaje de usuario recibido: {user_message}")

    long_term_memory = load_long_term_memory()
    
    # --- CICLO DE RAZONAMIENTO Y ACCIÓN (UN TURNO) ---
    # Este bucle interno maneja las llamadas a herramientas dentro de un solo turno de chat.
    # El cliente (quien llama a esta API) es responsable de manejar el historial completo.
    
    current_turn_history = list(conversation_history) # Copia para no modificar el original
    current_turn_history.append(f"Usuario: {user_message}")

    response_to_client = {}
    
    while True:
        prompt = build_system_prompt(long_term_memory, current_turn_history, user_message)
        raw_ollama_response = call_ollama(prompt)
        logging.info(f"Respuesta cruda de Ollama: {raw_ollama_response}")

        try:
            tool_call = json.loads(raw_ollama_response)
            # Check if the JSON response is a tool call (i.e., has a single key which is the tool name)
            if isinstance(tool_call, dict) and len(tool_call) == 1:
                tool_name = next(iter(tool_call)) # Get the first (and only) key
                parameters = tool_call[tool_name]
                
                tool_result = execute_tool(tool_name, parameters)
                logging.info(f"Resultado de la herramienta: {tool_result}")
                current_turn_history.append(f"Observación de Herramienta: {tool_result}")
                # Si se ejecuta una herramienta, el modelo necesita razonar de nuevo sobre el resultado.
                # En este modelo de API, el cliente podría decidir si quiere que el agente
                # haga otro turno automáticamente o si espera la siguiente petición. (Para este prototipo, el agente intenta dar una respuesta final después de la herramienta.)
                user_message = f"El resultado de la herramienta fue: {tool_result}. Basado en esto, proporciona la respuesta final al usuario de forma concisa y directa."
                logging.info(f"Re-prompting con: {user_message}")
                continue 
            else:
                # Si es un JSON pero no una llamada a herramienta, trátalo como texto
                response_to_client = {"agent_response": raw_ollama_response}
                break

        except json.JSONDecodeError:
            # Si no es JSON, es la respuesta final del modelo
            response_to_client = {"agent_response": raw_ollama_response}
            break
    
    return jsonify(response_to_client)


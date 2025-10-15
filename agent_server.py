import sys
import logging
from flask import Flask, request, jsonify, render_template, Response
import subprocess
import json
import os
import re

# Importa las herramientas y sus manifiestos desde tools.py
from tools import AVAILABLE_TOOLS, TOOL_MANIFEST, AGENT_MEMORY_FILE

# --- CONFIGURACIÓN ---
OLLAMA_MODEL = "granite4:micro-h"

# Configura el logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            "/home/epardo/projects/python_agent_cli/agent_server_debug.log"
        ),
        logging.StreamHandler(sys.stdout),
    ],
)

app = Flask(__name__)

# --- FUNCIONES DEL ORQUESTADOR ---

def load_long_term_memory() -> str:
    try:
        with open(AGENT_MEMORY_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Advertencia: No se encontró el archivo de memoria del agente."

def build_system_prompt(
    long_term_memory: str,
    conversation_history: list,
    user_request: str
) -> str:
    tools_json_str = json.dumps(TOOL_MANIFEST, indent=2)
    history_str = "\n".join(conversation_history)
    return f"""
Eres un asistente experto de línea de comandos. Tu nombre es 'PyAgent'.
Responde siempre en español. Sé conciso y directo en tus respuestas.

### MEMORIA A LARGO PLAZO Y DIRECTIVAS ###
{long_term_memory}

### HERRAMIENTAS DISPONIBLES ###
Tienes acceso a las siguientes herramientas. Para usarlas, responde ÚNICAMENTE con un objeto JSON válido que represente la herramienta a usar. No añadas texto adicional fuera del JSON.
{tools_json_str}

### HISTORIAL DE LA CONVERSACIÓN ###
{history_str}

### TAREA ACTUAL ###
Usuario: {user_request}
Antes de responder o usar una herramienta, piensa paso a paso para formular un plan de acción. Luego, responde a la petición del usuario. Si necesitas usar una herramienta, genera el JSON correspondiente. Si tienes la respuesta final, proporciónala directamente en texto plano.
"""

def call_ollama_stream(prompt: str):
    command = ["/usr/local/bin/ollama", "run", OLLAMA_MODEL, prompt]
    logging.info(f"Llamando a Ollama (stream) con comando: {' '.join(command)}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    for line in iter(process.stdout.readline, ''):
        yield line
    process.stdout.close()
    return_code = process.wait()
    if return_code != 0:
        error_output = process.stderr.read()
        logging.error(f"Error en el stream de Ollama: {error_output}")
        yield json.dumps({"error": error_output})

def execute_tool(tool_name: str, parameters: dict) -> str:
    if tool_name not in AVAILABLE_TOOLS:
        return json.dumps({"error": f"La herramienta '{tool_name}' no existe."})
    logging.info(f"Ejecutando herramienta: {tool_name} con parámetros {parameters}")
    try:
        tool_function = AVAILABLE_TOOLS[tool_name]
        result = tool_function(**parameters)
        return json.dumps(result) if isinstance(result, dict) else str(result)
    except Exception as e:
        logging.error(f"Error al ejecutar la herramienta '{tool_name}': {e}")
        return json.dumps({"error": f"Error al ejecutar la herramienta '{tool_name}': {e}"})

# --- RUTAS DEL SERVIDOR ---


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("user_message")
    raw_history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "user_message es requerido"}), 400

    logging.info(f"Mensaje de usuario recibido: {user_message}")
    long_term_memory = load_long_term_memory()

    # Convert history of dicts to a list of strings for the prompt
    formatted_history = []
    for msg in raw_history:
        sender = "Usuario" if msg.get('sender') == 'user' else "Agente"
        # Strip HTML tags from agent responses for the prompt
        text = re.sub('<[^<]+?>', '', msg.get('text', ''))
        formatted_history.append(f"{sender}: {text}")

    def event_stream(current_user_message):
        current_turn_history = list(formatted_history)
        current_turn_history.append(f"Usuario: {current_user_message}")

        while True:
            prompt = build_system_prompt(long_term_memory, current_turn_history, current_user_message)
            
            response_buffer = ""
            is_tool_call = False
            
            stream_generator = call_ollama_stream(prompt)
            for chunk in stream_generator:
                response_buffer += chunk
                try:
                    parsed_json = json.loads(response_buffer)
                    if isinstance(parsed_json, dict) and len(parsed_json) == 1:
                        is_tool_call = True
                        break
                except json.JSONDecodeError:
                    pass
            
            if is_tool_call:
                logging.info(f"Llamada a herramienta detectada: {response_buffer}")
                tool_call = json.loads(response_buffer)
                tool_name = next(iter(tool_call))
                parameters = tool_call[tool_name]
                
                tool_result = execute_tool(tool_name, parameters)
                logging.info(f"Resultado de la herramienta: {tool_result}")
                
                current_turn_history.append(f"Observación de Herramienta: {tool_result}")
                current_user_message = "La herramienta ha sido ejecutada. Proporciona la respuesta final al usuario."
                continue
            else:
                logging.info("Respuesta de texto detectada, iniciando streaming.")
                yield response_buffer
                for chunk in stream_generator:
                    yield chunk
                break

    return Response(event_stream(user_message), mimetype='text/plain')

@app.route("/")
@app.route("/web_chat")
def web_chat():
    return render_template("index.html")

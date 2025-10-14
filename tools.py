import logging
import subprocess
import os
import json

AGENT_MEMORY_FILE = '/home/epardo/projects/python_agent_cli/config/agent_memory.md'

# ------------------ TOOL IMPLEMENTATIONS ------------------
# Each tool is a Python function that takes arguments and returns a string or dict.

def run_shell_command(command: str) -> dict:
    """Ejecuta un comando de shell y devuelve su salida."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False # Do not raise exception on non-zero exit codes
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except Exception as e:
        logging.error(f"Error al ejecutar run_shell_command: {e}")
        return {"error": str(e)}

def read_file(path: str) -> str:
    """Lee el contenido de un archivo en el sistema."""
    if not os.path.isabs(path):
        return "Error: La ruta debe ser absoluta."
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error al leer el archivo: {e}")
        return f"Error al leer el archivo: {e}"

def write_file(path: str, content: str) -> str:
    """Escribe contenido en un archivo."""
    if not os.path.isabs(path):
        return "Error: La ruta debe ser absoluta."
    try:
        # Create directory if it's not exist
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Archivo {path} escrito exitosamente."
    except Exception as e:
        logging.error(f"Error al escribir el archivo: {e}")
        return f"Error al escribir el archivo: {e}"

def list_directory(path: str) -> str:
    """Lista el contenido de un directorio."""
    if not os.path.isabs(path):
        return "Error: La ruta debe ser absoluta."
    try:
        return json.dumps(os.listdir(path))
    except Exception as e:
        logging.error(f"Error al listar el directorio: {e}")
        return f"Error al listar el directorio: {e}"

def update_long_term_memory(content: str) -> str:
    """Actualiza el contenido del archivo de memoria a largo plazo del agente."""
    try:
        with open(AGENT_MEMORY_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Memoria a largo plazo actualizada exitosamente en {AGENT_MEMORY_FILE}."
    except Exception as e:
        logging.error(f"Error al actualizar la memoria a largo plazo: {e}")
        return f"Error al actualizar la memoria a largo plazo: {e}"

# ------------------ TOOL REGISTRATION ------------------
# This is where you register your functions so the agent knows about them.

# 1. AVAILABLE_TOOLS maps the tool name to the actual Python function.
AVAILABLE_TOOLS = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "update_long_term_memory": update_long_term_memory,
}

# 2. TOOL_MANIFEST is a description of the tools that the LLM will see.
#    The descriptions are crucial for the model to decide which tool to use.
TOOL_MANIFEST = {
    "run_shell_command": {
        "description": "Ejecuta un comando de shell en el sistema operativo. Úsalo para operaciones de sistema, gestión de archivos, etc. Devuelve la salida estándar, el error estándar y el código de salida.",
        "parameters": {
            "command": {"type": "string", "description": "El comando exacto a ejecutar."}
        }
    },
    "read_file": {
        "description": "Lee y devuelve el contenido completo de un archivo de texto. La ruta al archivo debe ser absoluta.",
        "parameters": {
            "path": {"type": "string", "description": "La ruta absoluta al archivo a leer."}
        }
    },
    "write_file": {
        "description": "Escribe (o sobrescribe) contenido en un archivo. La ruta al archivo debe ser absoluta. Creara los directorios si no existen.",
        "parameters": {
            "path": {"type": "string", "description": "La ruta absoluta al archivo a escribir."},
            "content": {"type": "string", "description": "El contenido a escribir en el archivo."}
        }
    },
    "list_directory": {
        "description": "Lista el contenido de un directorio. La ruta debe ser absoluta.",
        "parameters": {
            "path": {"type": "string", "description": "La ruta absoluta al directorio a listar."}
        }
    },
    "update_long_term_memory": {
        "description": "Actualiza el contenido del archivo de memoria a largo plazo del agente. Esto permite al agente aprender y adaptar sus directivas.",
        "parameters": {
            "content": {"type": "string", "description": "El nuevo contenido para la memoria a largo plazo."}
        }
    }
}

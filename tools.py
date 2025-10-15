import logging
import subprocess
import os
import json
import glob
import re
import fnmatch
import requests
from datetime import datetime

AGENT_MEMORY_FILE = "/home/epardo/projects/python_agent_cli/config/agent_memory.md"

# ------------------ TOOL IMPLEMENTATIONS ------------------

def get_current_date() -> str:
    """Devuelve la fecha y hora actual del sistema."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_shell_command(command: str) -> dict:
    """Ejecuta un comando de shell y devuelve su salida."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except Exception as e:
        logging.error(f"Error al ejecutar run_shell_command: {e}")
        return {"error": str(e)}

def read_file(path: str) -> str:
    """Lee el contenido de un archivo en el sistema."""
    if not os.path.isabs(path):
        return "Error: La ruta debe ser absoluta."
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error al leer el archivo: {e}")
        return f"Error al leer el archivo: {e}"

def write_file(path: str, content: str) -> str:
    """Escribe contenido en un archivo."""
    if not os.path.isabs(path):
        return "Error: La ruta debe ser absoluta."
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
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
        if not os.path.exists(path):
            return f"Error: El directorio '{path}' no existe."
        if not os.path.isdir(path):
            return f"Error: La ruta '{path}' no es un directorio."
        contents = os.listdir(path)
        return json.dumps(contents)
    except Exception as e:
        logging.error(f"Error al listar el directorio: {e}")
        return f"Error al listar el directorio: {e}"

def update_long_term_memory(content: str) -> str:
    """Actualiza el contenido del archivo de memoria a largo plazo del agente."""
    try:
        with open(AGENT_MEMORY_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Memoria a largo plazo actualizada exitosamente en {AGENT_MEMORY_FILE}."
    except Exception as e:
        logging.error(f"Error al actualizar la memoria a largo plazo: {e}")
        return f"Error al actualizar la memoria a largo plazo: {e}"

def replace(file_path: str, old_string: str, new_string: str, instruction: str) -> str:
    """Placeholder for replace tool."""
    return "Error: La herramienta 'replace' no está completamente implementada."

def search_file_content(pattern: str, path: str = ".", include: str = "*") -> str:
    """Busca un patrón de expresión regular dentro del contenido de los archivos."""
    if not os.path.isabs(path):
        return "Error: La ruta de búsqueda debe ser absoluta."
    results = []
    try:
        compiled_pattern = re.compile(pattern)
        for root, _, files in os.walk(path):
            for file_name in files:
                if fnmatch.fnmatch(file_name, include):
                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if compiled_pattern.search(line):
                                    results.append(f"{file_path}:{line_num}: {line.strip()}")
                    except Exception as e:
                        logging.warning(f"No se pudo leer el archivo {file_path}: {e}")
    except Exception as e:
        return f"Error durante la búsqueda: {e}"
    if not results:
        return "No se encontraron coincidencias."
    return "\n".join(results)

def glob_files(pattern: str, path: str = ".") -> str:
    """Encuentra archivos que coinciden con patrones glob."""
    if not os.path.isabs(path):
        return "Error: La ruta de búsqueda debe ser absoluta."
    full_pattern = os.path.join(path, pattern)
    found_files = [os.path.abspath(f) for f in glob.glob(full_pattern, recursive=True)]
    if not found_files:
        return "No se encontraron archivos que coincidan con el patrón."
    return json.dumps(found_files)

def web_fetch(prompt: str) -> str:
    """Procesa contenido de URL(s) incluidas en un prompt."""
    urls = re.findall(r'https?://[^\s]+', prompt)
    if not urls:
        return "No se encontraron URLs en el prompt."
    results = []
    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            results.append(f"--- Contenido de {url} ---\n{response.text}")
        except requests.exceptions.RequestException as e:
            results.append(f"Error al obtener {url}: {e}")
    return "\n\n".join(results)

# ------------------ TOOL REGISTRATION ------------------

AVAILABLE_TOOLS = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "update_long_term_memory": update_long_term_memory,
    "replace": replace,
    "search_file_content": search_file_content,
    "glob": glob_files,
    "web_fetch": web_fetch,
    "get_current_date": get_current_date,
}

TOOL_MANIFEST = {
    "run_shell_command": {
        "description": "Ejecuta un comando de shell en el sistema operativo. Úsalo para operaciones de sistema, gestión de archivos, etc. Devuelve la salida estándar, el error estándar y el código de salida.",
        "parameters": {
            "command": {
                "type": "string",
                "description": "El comando exacto a ejecutar.",
            }
        },
    },
    "read_file": {
        "description": "Lee y devuelve el contenido completo de un archivo de texto. La ruta al archivo debe ser absoluta.",
        "parameters": {
            "path": {
                "type": "string",
                "description": "La ruta absoluta al archivo a leer.",
            }
        },
    },
    "write_file": {
        "description": "Escribe (o sobrescribe) contenido en un archivo. La ruta al archivo debe ser absoluta. Creara los directorios si no existen.",
        "parameters": {
            "path": {
                "type": "string",
                "description": "La ruta absoluta al archivo a escribir.",
            },
            "content": {
                "type": "string",
                "description": "El contenido a escribir en el archivo.",
            },
        },
    },
    "list_directory": {
        "description": "Lista el contenido de un directorio. La ruta debe ser absoluta.",
        "parameters": {
            "path": {
                "type": "string",
                "description": "La ruta absoluta al directorio a listar.",
            }
        },
    },
    "update_long_term_memory": {
        "description": "Actualiza el contenido del archivo de memoria a largo plazo del agente. Esto permitirá al agente aprender y adaptar sus directivas.",
        "parameters": {
            "content": {
                "type": "string",
                "description": "El nuevo contenido para la memoria a largo plazo.",
            }
        },
    },
    "replace": {
        "description": "Reemplaza una única ocurrencia de texto en un archivo. Requiere la ruta absoluta del archivo, la cadena exacta a reemplazar (con contexto de al menos 3 líneas antes y después), la nueva cadena y una instrucción clara.",
        "parameters": {
            "file_path": {
                "type": "string",
                "description": "La ruta absoluta al archivo a modificar.",
            },
            "old_string": {
                "type": "string",
                "description": "El texto exacto a reemplazar, incluyendo al menos 3 líneas de contexto antes y después.",
            },
            "new_string": {
                "type": "string",
                "description": "El texto exacto con el que se reemplazará 'old_string'.",
            },
            "instruction": {
                "type": "string",
                "description": "Una instrucción clara y semántica sobre el cambio.",
            },
        },
    },
    "search_file_content": {
        "description": "Busca un patrón de expresión regular dentro del contenido de los archivos en un directorio especificado. Puede filtrar archivos por un patrón glob. Devuelve las líneas que contienen coincidencias, junto con sus rutas de archivo y números de línea.",
        "parameters": {
            "pattern": {
                "type": "string",
                "description": "El patrón de expresión regular (regex) a buscar.",
            },
            "path": {
                "type": "string",
                "description": "La ruta absoluta al directorio donde buscar. Por defecto es el directorio actual.",
                "default": ".",
            },
            "include": {
                "type": "string",
                "description": "Un patrón glob para filtrar qué archivos se buscan (ej. '*.js', '*.{ts,tsx}'). Por defecto busca en todos los archivos.",
                "default": "*",
            },
        },
    },
    "glob": {
        "description": "Encuentra eficientemente archivos que coinciden con patrones glob específicos, devolviendo rutas absolutas. Útil para localizar archivos por su nombre o estructura de ruta.",
        "parameters": {
            "pattern": {
                "type": "string",
                "description": "El patrón glob a buscar (ej. '**/*.py', 'docs/*.md').",
            },
            "path": {
                "type": "string",
                "description": "La ruta absoluta al directorio donde buscar. Por defecto es el directorio actual.",
                "default": ".",
            },
        },
    },
    "web_fetch": {
        "description": "Procesa contenido de URL(s) incluidas en un prompt. Extrae URLs y devuelve su contenido. Útil para obtener información de páginas web.",
        "parameters": {
            "prompt": {
                "type": "string",
                "description": "Un prompt que contiene la(s) URL(s) (hasta 20) a obtener y las instrucciones específicas sobre cómo procesar su contenido.",
            }
        },
    },
    "get_current_date": {
        "description": "Devuelve la fecha y hora actual del sistema. Úsalo cuando el usuario pregunte por el día o la fecha.",
        "parameters": {}
    },
}

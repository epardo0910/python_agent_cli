import subprocess
import json
from rich.console import Console

# Importa las herramientas y sus manifiestos desde tools.py
from tools import AVAILABLE_TOOLS, TOOL_MANIFEST

# --- CONFIGURACIÓN ---
OLLAMA_MODEL = "granite4:micro-h"
AGENT_MEMORY_FILE = "/home/epardo/python_agent_cli/config/agent_memory.md"

# Inicializa una consola para una salida más atractiva
console = Console()

# --- FUNCIONES DEL ORQUESTADOR ---


def load_long_term_memory() -> str:
    """Carga las directivas y memoria a largo plazo del agente."""
    try:
        with open(AGENT_MEMORY_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Advertencia: No se encontró el archivo de memoria del agente."


def build_system_prompt(long_term_memory: str, conversation_history: list) -> str:
    """Construye el prompt completo para el modelo de Ollama."""

    # Convierte el manifiesto de herramientas a una cadena JSON bonita
    tools_json_str = json.dumps(TOOL_MANIFEST, indent=2)

    # Convierte el historial de conversación a un formato legible
    history_str = "\n".join(conversation_history)

    # Plantilla del prompt del sistema
    prompt_template = f"""
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
Responde a la siguiente petición del usuario. Si necesitas usar una herramienta, hazlo. Si tienes la respuesta final, proporciónala directamente.
"""
    return prompt_template


def call_ollama(prompt: str) -> str:
    """Llama al modelo de Ollama a través de la línea de comandos."""
    # Escapa las comillas dentro del prompt para evitar errores de shell
    escaped_prompt = prompt.replace('"', '"')
    command = f'ollama run {OLLAMA_MODEL} "{escaped_prompt}"'

    # En un agente real, manejarías esto de forma más robusta
    console.print("[grey50]Llamando a Ollama...[/grey50]")
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, check=False
    )

    if result.returncode != 0:
        return f"Error al llamar a Ollama: {result.stderr}"

    return result.stdout.strip()


def execute_tool(tool_call: dict) -> str:
    """Ejecuta una herramienta y devuelve el resultado como una cadena."""
    tool_name = tool_call.get("tool_name")
    parameters = tool_call.get("parameters", {{}})

    if tool_name not in AVAILABLE_TOOLS:
        return f"Error: La herramienta '{tool_name}' no existe."

    console.print(
        f"[yellow]Ejecutando herramienta: {tool_name} con parámetros {parameters}[/yellow]"
    )

    try:
        tool_function = AVAILABLE_TOOLS[tool_name]
        # Aquí necesitarías un mecanismo de confirmación para herramientas peligrosas
        # EJEMPLO DE CAPA DE SEGURIDAD (¡IMPLEMENTAR!):
        # if tool_name in ["run_shell_command", "write_file"]:
        #     confirm = console.input(f"¿Permitir la ejecución de '{tool_name}'? [y/N]: ")
        #     if confirm.lower() != 'y':
        #         return "Ejecución de herramienta cancelada por el usuario."

        result = tool_function(**parameters)

        # Convierte el resultado a una cadena para el historial
        return json.dumps(result) if isinstance(result, dict) else str(result)
    except Exception as e:
        return f"Error al ejecutar la herramienta '{tool_name}': {e}"


def main():
    """
    PUNTO DE ENTRADA PRINCIPAL Y BUCLE INTERACTIVO (POR IMPLEMENTAR).
    """
    console.print("[bold green]Asistente PyAgent iniciado.[/bold green]")

    # long_term_memory = load_long_term_memory()
    # conversation_history = []

    # --- BUCLE PRINCIPAL (A IMPLEMENTAR) ---
    # Este es el esqueleto del bucle que necesitas completar.

    # 1. Pedir la entrada del usuario.
    #    user_request = console.input("[bold cyan]Tú:[/bold cyan] ")
    #    if user_request.lower() == 'salir':
    #        break

    # 2. Añadir la petición al historial.
    #    conversation_history.append(f"Usuario: {user_request}")

    # 3. Construir el prompt y llamar a Ollama.
    #    prompt = build_system_prompt(long_term_memory, conversation_history)
    #    response = call_ollama(prompt)

    # 4. Analizar la respuesta de Ollama.
    #    try:
    #        tool_call = json.loads(response)
    #        # Es una llamada a herramienta
    #        tool_result = execute_tool(tool_call)
    #        conversation_history.append(f"Observación de Herramienta: {tool_result}")
    #        # Vuelve a llamar a Ollama con el resultado de la herramienta para obtener una respuesta final
    #        # (Esta parte es clave en los bucles de agentes)
    #
    #    except json.JSONDecodeError:
    #        # Es una respuesta de texto normal
    #        console.print(f"[bold green]PyAgent:[/bold green] {response}")
    #        conversation_history.append(f"PyAgent: {response}")

    console.print(
        "\n[italic]Para hacer este agente funcional, completa el bucle en la función `main()` de este script.[/italic]"
    )
    console.print(
        "[italic]Revisa el archivo README.md para más instrucciones.[/italic]"
    )


if __name__ == "__main__":
    main()

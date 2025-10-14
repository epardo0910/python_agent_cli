import requests
import json
import sys
import os

AGENT_URL = "https://agentpy.emanuel-server.com/chat"
API_KEY = os.environ.get("AGENT_API_KEY")

def chat_with_agent(user_message: str, history: list = None) -> str:
    if not API_KEY:
        return "Error: La variable de entorno AGENT_API_KEY no está configurada. Por favor, configúrala antes de usar el cliente."

    payload = {
        "user_message": user_message
    }
    if history:
        payload["history"] = history

    headers = {"X-API-Key": API_KEY}

    try:
        response = requests.post(AGENT_URL, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        
        agent_response = response.json()
        return agent_response.get("agent_response", "No se recibió una respuesta válida del agente.")
    except requests.exceptions.RequestException as e:
        return f"Error de conexión con el agente: {e}"
    except json.JSONDecodeError:
        return f"Error al decodificar la respuesta JSON del agente: {response.text}"

def main():
    print("Bienvenido al cliente de PyAgent. Escribe 'salir' para terminar.")
    conversation_history = []

    while True:
        user_input = input("Tú: ")
        if user_input.lower() == 'salir':
            break
        
        response = chat_with_agent(user_input, conversation_history)
        print(f"PyAgent: {response}")
        
        # Actualizar historial para la próxima interacción
        conversation_history.append(f"Usuario: {user_input}")
        conversation_history.append(f"Agente: {response}")

if __name__ == "__main__":
    main()

import unittest
import os
import json
from unittest.mock import patch, mock_open, MagicMock

import tools # Import the module, not individual functions
from tools import run_shell_command, read_file, write_file, list_directory, update_long_term_memory

# Import agent_server functions for testing
import agent_server # Import the module
from agent_server import load_long_term_memory, build_system_prompt, call_ollama, execute_tool, app

class TestTools(unittest.TestCase):

    def setUp(self):
        # Create a dummy directory and files for testing file operations
        self.test_dir = "/tmp/test_agent_cli_dir"
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_file_path = os.path.join(self.test_dir, "test_file.txt")
        self.test_memory_file = os.path.join(self.test_dir, "agent_memory.md")
        
        # Patch tools.AGENT_MEMORY_FILE for isolated testing
        self._patcher = patch.object(tools, 'AGENT_MEMORY_FILE', self.test_memory_file)
        self._patcher.start()

    def tearDown(self):
        # Clean up dummy directory and files
        if os.path.exists(self.test_dir):
            for root, dirs, files in os.walk(self.test_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.test_dir)
        
        # Stop the patcher
        self._patcher.stop()

    @patch('subprocess.run')
    def test_run_shell_command_success(self, mock_subprocess_run):
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "hello world\n"
        mock_subprocess_run.return_value.stderr = ""
        
        result = run_shell_command("echo hello world")
        self.assertEqual(result, {"stdout": "hello world\n", "stderr": "", "exit_code": 0})
        mock_subprocess_run.assert_called_once_with(
            "echo hello world", shell=True, capture_output=True, text=True, check=False
        )

    @patch('subprocess.run')
    def test_run_shell_command_failure(self, mock_subprocess_run):
        mock_subprocess_run.return_value.returncode = 1
        mock_subprocess_run.return_value.stdout = ""
        mock_subprocess_run.return_value.stderr = "command not found\n"
        
        result = run_shell_command("nonexistent_command")
        self.assertEqual(result, {"stdout": "", "stderr": "command not found\n", "exit_code": 1})

    def test_read_file_success(self):
        with open(self.test_file_path, "w") as f:
            f.write("test content")
        
        result = read_file(self.test_file_path)
        self.assertEqual(result, "test content")

    def test_read_file_non_absolute_path(self):
        result = read_file("relative/path.txt")
        self.assertEqual(result, "Error: La ruta debe ser absoluta.")

    def test_read_file_not_found(self):
        result = read_file("/tmp/nonexistent_file.txt")
        self.assertIn("Error al leer el archivo:", result)

    def test_write_file_success(self):
        result = write_file(self.test_file_path, "new content")
        self.assertEqual(result, f"Archivo {self.test_file_path} escrito exitosamente.")
        with open(self.test_file_path, "r") as f:
            self.assertEqual(f.read(), "new content")

    def test_write_file_non_absolute_path(self):
        result = write_file("relative/path.txt", "content")
        self.assertEqual(result, "Error: La ruta debe ser absoluta.")

    def test_list_directory_success(self):
        # Create some dummy files in the test directory
        with open(os.path.join(self.test_dir, "file1.txt"), "w") as f:
            f.write("1")
        os.makedirs(os.path.join(self.test_dir, "subdir"), exist_ok=True)
        
        result = list_directory(self.test_dir)
        # os.listdir order is not guaranteed, so sort for comparison
        expected_list = sorted(["file1.txt", "subdir"])
        self.assertEqual(sorted(json.loads(result)), expected_list)

    def test_list_directory_non_absolute_path(self):
        result = list_directory("relative/dir")
        self.assertEqual(result, "Error: La ruta debe ser absoluta.")

    def test_list_directory_not_found(self):
        result = list_directory("/tmp/nonexistent_dir")
        self.assertIn("Error al listar el directorio:", result)

    def test_update_long_term_memory_success(self):
        new_content = "Nueva directiva: Siempre sé amable."
        result = update_long_term_memory(new_content)
        self.assertEqual(result, f"Memoria a largo plazo actualizada exitosamente en {self.test_memory_file}.")
        with open(self.test_memory_file, "r") as f:
            self.assertEqual(f.read(), new_content)

    def test_update_long_term_memory_failure(self):
        with patch.object(tools, 'AGENT_MEMORY_FILE', "/root/unwritable_memory.md"):
            result = update_long_term_memory("content")
            self.assertIn("Error al actualizar la memoria a largo plazo:", result)

# Import agent_server functions for testing
class TestAgentServer(unittest.TestCase):

    def setUp(self):
        # Create a dummy directory and files for testing file operations
        self.test_dir = "/tmp/test_agent_cli_dir_server"
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_memory_file = os.path.join(self.test_dir, "agent_memory.md")

        # Patch agent_server.AGENT_MEMORY_FILE for isolated testing
        self._agent_memory_file_patcher_server = patch.object(agent_server, 'AGENT_MEMORY_FILE', self.test_memory_file)
        self._agent_memory_file_patcher_server.start()

        # Create a test client for the Flask app
        self.app = app.test_client()
        self.app.testing = True

        # Set a dummy API key for testing
        os.environ["AGENT_API_KEY"] = "test_api_key"
        # Ensure the app's API_KEY is updated for the test client
        self._api_key_patcher = patch.object(agent_server, 'API_KEY', "test_api_key")
        self._api_key_patcher.start()


    def tearDown(self):
        # Clean up dummy directory and files
        if os.path.exists(self.test_dir):
            for root, dirs, files in os.walk(self.test_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.test_dir)
        
        # Stop the patchers
        self._agent_memory_file_patcher_server.stop()
        self._api_key_patcher.stop()
        
        # Clean up environment variable
        del os.environ["AGENT_API_KEY"]

    @patch('builtins.open', new_callable=mock_open, read_data="Test memory content.")
    def test_load_long_term_memory_success(self, mock_open_func):
        expected_content = "Test memory content."
        content = load_long_term_memory()
        self.assertEqual(content, expected_content)
        mock_open_func.assert_called_once_with(self.test_memory_file, 'r', encoding='utf-8')

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_long_term_memory_not_found(self, mock_open_func):
        content = load_long_term_memory()
        self.assertIn("Advertencia: No se encontró el archivo de memoria del agente.", content)

    def test_build_system_prompt(self):
        long_term_memory = "Soy un asistente de prueba."
        conversation_history = ["Usuario: Hola", "Agente: Hola, ¿cómo estás?"]
        user_request = "Haz una prueba."

        prompt = build_system_prompt(long_term_memory, conversation_history, user_request)
        
        self.assertIn("Eres un asistente experto de línea de comandos. Tu nombre es 'PyAgent'.", prompt)
        self.assertIn("Soy un asistente de prueba.", prompt)
        self.assertIn("Usuario: Hola", prompt)
        self.assertIn("Agente: Hola, ¿cómo estás?", prompt)
        self.assertIn("Usuario: Haz una prueba.", prompt)
        self.assertIn("### HERRAMIENTAS DISPONIBLES ###", prompt)
        self.assertIn("run_shell_command", prompt)
        self.assertIn("read_file", prompt)
        self.assertIn("write_file", prompt)
        self.assertIn("list_directory", prompt)
        self.assertIn("update_long_term_memory", prompt)

    @patch('subprocess.run')
    def test_call_ollama_success(self, mock_subprocess_run):
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "Ollama response content."
        mock_subprocess_run.return_value.stderr = ""

        prompt = "Test prompt"
        result = call_ollama(prompt)
        self.assertEqual(result, "Ollama response content.")
        mock_subprocess_run.assert_called_once_with(
            ["/usr/local/bin/ollama", "run", agent_server.OLLAMA_MODEL, prompt],
            capture_output=True, text=True, check=False
        )

    @patch('subprocess.run')
    def test_call_ollama_failure(self, mock_subprocess_run):
        mock_subprocess_run.return_value.returncode = 1
        mock_subprocess_run.return_value.stdout = ""
        mock_subprocess_run.return_value.stderr = "Ollama error message."

        prompt = "Test prompt"
        result = call_ollama(prompt)
        self.assertIn("Error al llamar a Ollama:", result)
        self.assertIn("Ollama error message.", result)

    @patch('agent_server.AVAILABLE_TOOLS', new_callable=dict) # Patch with a real dictionary
    def test_execute_tool_success(self, mock_available_tools):
        # Create individual mocks for each tool
        mock_run_shell = MagicMock(return_value={"stdout": "ls output", "stderr": "", "exit_code": 0})
        mock_read_file = MagicMock(return_value="file content")
        mock_write_file = MagicMock(return_value="Archivo /tmp/test.txt escrito exitosamente.")
        mock_list_dir = MagicMock(return_value=json.dumps(["file1", "file2"]))
        mock_update_memory = MagicMock(return_value="Memoria a largo plazo actualizada exitosamente en /tmp/test_agent_cli_dir_server/agent_memory.md.")

        # Assign mocks to the patched AVAILABLE_TOOLS dictionary
        mock_available_tools["run_shell_command"] = mock_run_shell
        mock_available_tools["read_file"] = mock_read_file
        mock_available_tools["write_file"] = mock_write_file
        mock_available_tools["list_directory"] = mock_list_dir
        mock_available_tools["update_long_term_memory"] = mock_update_memory

        # Test run_shell_command
        result = execute_tool("run_shell_command", {"command": "ls"})
        self.assertEqual(json.loads(result), {"stdout": "ls output", "stderr": "", "exit_code": 0})
        mock_run_shell.assert_called_once_with(command="ls")
        mock_run_shell.reset_mock()

        # Test read_file
        result = execute_tool("read_file", {"path": "/tmp/test.txt"})
        self.assertEqual(result, "file content")
        mock_read_file.assert_called_once_with(path="/tmp/test.txt")
        mock_read_file.reset_mock()

        # Test write_file
        result = execute_tool("write_file", {"path": "/tmp/test.txt", "content": "new content"})
        self.assertEqual(result, "Archivo /tmp/test.txt escrito exitosamente.")
        mock_write_file.assert_called_once_with(path="/tmp/test.txt", content="new content")
        mock_write_file.reset_mock()

        # Test list_directory
        result = execute_tool("list_directory", {"path": "/tmp"})
        self.assertEqual(json.loads(result), ["file1", "file2"])
        mock_list_dir.assert_called_once_with(path="/tmp")
        mock_list_dir.reset_mock()

        # Test update_long_term_memory
        result = execute_tool("update_long_term_memory", {"content": "new memory"})
        self.assertEqual(result, "Memoria a largo plazo actualizada exitosamente en /tmp/test_agent_cli_dir_server/agent_memory.md.")
        mock_update_memory.assert_called_once_with(content="new memory")
        mock_update_memory.reset_mock()
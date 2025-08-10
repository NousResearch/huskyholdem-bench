#!/usr/bin/env python3

"""
Prompt Processor Script for OpenRouter API

This script allows users to:
1. List available models from OpenRouter
2. Choose a model interactively
3. Process a prompt from generate.txt
4. Save results to output.log
5. Extract code blocks and save to bot directory
6. Test the generated code by running a game with Docker

FIXED FEATURES:
- Enhanced JSON parsing for reasoning/thinking models
- Proper success detection logic for game tests
- Cleaner console output with reduced verbosity
- Better error handling and fallback parsing
"""

import os
import json
import sys
import re
import io
import tarfile
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import requests
from datetime import datetime

# Load environment variables
load_dotenv()

class OpenRouterPromptProcessor:
    """Processes prompts with OpenRouter API with enhanced reasoning model support"""

    def __init__(self, api_key: Optional[str] = None, docker_service=None):
        """
        Initialize the processor
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            docker_service: Optional Docker service for game testing
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY in .env file")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/gambling-with-bot",
            "X-Title": "Prompt Processor"
        }
        
        # Store Docker service if provided
        self.docker_service = docker_service
        
        # Define reasoning model patterns
        self.reasoning_model_keywords = [
            'thinking', 'reasoning', 'r1', 'glm-4.5', 'qwen3-235b-a22b-thinking',
            'deepseek-r1', 'o1', 'o3', 'qwq'
        ]

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models from OpenRouter"""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers
            )
            if response.status_code != 200:
                raise Exception(f"Failed to get models: {response.status_code} - {response.text}")
            
            models_data = response.json()
            return models_data.get("data", [])
        except Exception as e:
            print(f"Error fetching models: {e}")
            return []

    def display_models(self, models: List[Dict[str, Any]]) -> None:
        """Display available models in a formatted list"""
        print("\n=== Available Models ===")
        print(f"{'#':<3} {'Model ID':<40} {'Provider':<15} {'Context':<10}")
        print("-" * 70)
        
        for i, model in enumerate(models, 1):
            model_id = model.get("id", "Unknown")
            provider = model.get("provider", {}).get("id", "Unknown")
            context_length = model.get("context_length", "N/A")
            print(f"{i:<3} {model_id:<40} {provider:<15} {context_length:<10}")

    def select_model(self, models: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Allow user to select a model interactively"""
        if not models:
            print("No models available.")
            return None

        while True:
            try:
                choice = input(f"\nSelect a model (1-{len(models)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q':
                    return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(models):
                    selected_model = models[choice_num - 1]
                    print(f"\nSelected: {selected_model['id']}")
                    return selected_model
                else:
                    print(f"Please enter a number between 1 and {len(models)}")
            except ValueError:
                print("Please enter a valid number or 'q' to quit")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return None

    def _is_reasoning_model(self, model_id: str) -> bool:
        """Check if the model is a reasoning/thinking model"""
        model_lower = model_id.lower()
        return any(keyword in model_lower for keyword in self.reasoning_model_keywords)

    def _clean_reasoning_response(self, response_text: str) -> str:
        """Clean up reasoning model responses with excessive whitespace"""
        # Remove massive leading whitespace blocks
        cleaned = response_text.strip()
        
        # Remove excessive leading newlines and spaces
        while cleaned.startswith('\n') or cleaned.startswith(' '):
            cleaned = cleaned[1:]
        
        # Remove reasoning model artifacts if present in raw text
        cleaned = re.sub(r'<\|reasoning\|>.*?<\|/reasoning\|>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL)
        
        return cleaned

    def _clean_reasoning_content(self, content: str) -> str:
        """Clean reasoning model content artifacts"""
        if not content:
            return content
        
        # Remove excessive newlines (common in reasoning responses)
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # Remove reasoning tokens that might interfere
        content = re.sub(r'<\|reasoning\|>.*?<\|/reasoning\|>', '', content, flags=re.DOTALL)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        return content.strip()

    def _parse_reasoning_response(self, response_text: str, is_reasoning_model: bool) -> dict:
        """Parse response with special handling for reasoning models"""
        try:
            if not response_text or len(response_text.strip()) == 0:
                return {"error": "Empty response received from API"}
            # Step 1: Clean up excessive whitespace
            cleaned_text = self._clean_reasoning_response(response_text)
            
            # Step 2: Try standard JSON parsing first
            try:
                result = json.loads(cleaned_text)
                
                # Step 3: Clean up content for reasoning models
                if is_reasoning_model and "choices" in result:
                    for choice in result["choices"]:
                        if "message" in choice and "content" in choice["message"]:
                            content = choice["message"]["content"]
                            if content:
                                content = self._clean_reasoning_content(content)
                                choice["message"]["content"] = content
                
                return result
                
            except json.JSONDecodeError as first_error:
                # Step 4: Try reasoning-specific parsing methods
                if is_reasoning_model:
                    return self._parse_chunked_reasoning_response(cleaned_text, first_error)
                else:
                    raise first_error
                    
        except Exception as e:
            return {
                "error": f"Failed to parse response: {str(e)}", 
                "raw_response": response_text[:1000] + "..." if len(response_text) > 1000 else response_text
            }

    def _parse_chunked_reasoning_response(self, response_text: str, original_error) -> dict:
        """Handle chunked or malformed reasoning responses"""
        try:
            # Method 1: Try to find JSON within the response
            json_pattern = r'\{.*\}'
            json_matches = re.findall(json_pattern, response_text, re.DOTALL)
            
            for match in json_matches:
                try:
                    result = json.loads(match)
                    if "choices" in result or "error" in result:
                        print(f"✅ Successfully parsed reasoning response using pattern matching")
                        return result
                except:
                    continue
            
            # Method 2: Try line-by-line parsing
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and line.startswith('{') and line.endswith('}'):
                    try:
                        result = json.loads(line)
                        if "choices" in result or "error" in result:
                            print(f"✅ Successfully parsed reasoning response using line parsing")
                            return result
                    except:
                        continue
            
            # Method 3: Try to extract content between reasoning tokens
            reasoning_pattern = r'<\|reasoning\|>(.*?)<\|/reasoning\|>(.*?)$'
            reasoning_match = re.search(reasoning_pattern, response_text, re.DOTALL)
            
            if reasoning_match:
                reasoning_content = reasoning_match.group(1).strip()
                main_content = reasoning_match.group(2).strip()
                
                return {
                    "choices": [{
                        "message": {
                            "content": main_content,
                            "role": "assistant"
                        },
                        "reasoning": reasoning_content,
                        "finish_reason": "stop"
                    }],
                    "usage": {"total_tokens": len(response_text) // 4}
                }
            
            # If all methods fail, return the original error with context
            raise original_error
            
        except Exception as e:
            return {
                "error": f"Reasoning response parsing failed: {str(e)}", 
                "original_error": str(original_error),
                "response_preview": response_text[:500] + "..." if len(response_text) > 500 else response_text
            }

    def process_prompt(self, model_id: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Process a prompt through the selected model with enhanced reasoning support"""
        is_reasoning_model = self._is_reasoning_model(model_id)
        
        payload = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", 1.0),
            "max_tokens": kwargs.get("max_tokens", 9000),
            "stream": False
        }
        
        # Add reasoning parameter for thinking models
        if is_reasoning_model:
            payload["include_reasoning"] = True
            print(f"🧠 Detected reasoning model: {model_id} (enabling reasoning mode)")

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=300
            )

            if response.status_code != 200:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")

            # Print response info (reduced verbosity)
            print(f"📊 Response status: {response.status_code}")
            print(f"📊 Response headers: {dict(response.headers)}")
            print(f"📊 Response size: {len(response.text)} characters")

            # Enhanced parsing for reasoning models
            result = self._parse_reasoning_response(response.text, is_reasoning_model)
            
            # Check if parsing failed
            if "error" in result:
                print(f"❌ Parsing error: {result['error']}")
                # Save debug info
                debug_file = f"debug_response_{model_id.replace('/', '_')}.txt"
                with open(debug_file, 'w') as f:
                    f.write(response.text)
                print(f"🐛 Raw response saved to: {debug_file}")
                raise Exception(f"Error processing prompt: {result['error']}")
            
            return result

        except requests.exceptions.Timeout:
            raise Exception("Request timed out - model may be taking too long to respond")
        except Exception as e:
            raise Exception(f"Error processing prompt: {e}")

    def read_prompt_from_file(self, file_path: str = "prompt/generate.txt") -> str:
        """Read prompt from the specified file"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Prompt file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            raise Exception(f"Error reading prompt file: {e}")

    def extract_code_blocks(self, response_content: str) -> Tuple[str, str]:
        """
        Extract Python and text code blocks from the response
        Args:
            response_content: The response content from the LLM
        Returns:
            Tuple of (python_code, text_content)
        """
        python_code = ""
        text_content = ""
        
        # Extract Python code blocks
        python_pattern = r'```python\s*\n(.*?)\n```'
        python_matches = re.findall(python_pattern, response_content, re.DOTALL)
        if python_matches:
            python_code = python_matches[0].strip()
        
        # Extract text blocks (non-Python code blocks)
        text_pattern = r'```text\s*\n(.*?)\n```'
        text_matches = re.findall(text_pattern, response_content, re.DOTALL)
        if text_matches:
            text_content = text_matches[0].strip()
        
        # If no text block found, try to extract any non-Python code block
        if not text_content:
            # Find all code blocks
            all_blocks_pattern = r'```(\w+)\s*\n(.*?)\n```'
            all_blocks = re.findall(all_blocks_pattern, response_content, re.DOTALL)
            for lang, content in all_blocks:
                if lang.lower() != 'python':
                    text_content = content.strip()
                    break
        
        return python_code, text_content

    def create_tar_stream(self, player_code: str, requirements_content: str) -> io.BytesIO:
        """Create a tar stream with player.py and requirements.txt"""
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w:gz') as tar:
            # Add player.py
            if player_code:
                player_info = tarfile.TarInfo(name="player.py")
                player_info.size = len(player_code.encode('utf-8'))
                tar.addfile(player_info, io.BytesIO(player_code.encode('utf-8')))
            
            # Add requirements.txt
            if requirements_content:
                req_info = tarfile.TarInfo(name="requirements.txt")
                req_info.size = len(requirements_content.encode('utf-8'))
                tar.addfile(req_info, io.BytesIO(requirements_content.encode('utf-8')))
        
        tar_stream.seek(0)
        return tar_stream

    def cleanup_containers(self, test_client_container_name=None, server_container_name=None, port=None, release_port=True):
        """Helper function to clean up containers and optionally release port"""
        print("🧹 Cleaning up containers...")
        if test_client_container_name:
            self.docker_service.stop_and_remove_container(test_client_container_name)
        if server_container_name:
            self.docker_service.stop_and_remove_container(server_container_name)
        if port:
            self.docker_service.cleanup_containers_by_port(port)
            if release_port and port:
                self.docker_service.release_port(port)

    def test_generated_code(self, bot_dir: str, model_id: str, iteration: int = 1, port: Optional[int] = None) -> Tuple[bool, str]:
        """
        Test the generated code by running a game with Docker
        FIXED: Better success detection logic
        """
        if not self.docker_service:
            return False, "Docker service not available"

        # Create verified directory with iteration subdirectory
        verified_dir = os.path.join(bot_dir, "verified", f"{iteration}_iteration")
        os.makedirs(verified_dir, exist_ok=True)
        error_log_path = os.path.join(verified_dir, "error.log")

        def log_error(error_message: str):
            """Helper function to log errors to error.log"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(error_log_path, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {error_message}\n")

        # Initialize variables for cleanup
        test_client_container_name = None
        server_container_name = None
        local_port = port is None
        if port is None:
            port = self.docker_service.generate_random_port()

        try:
            print(f"🧪 Testing generated code from {model_id} (Iteration {iteration}) on port {port}...")

            # Clean up any orphaned containers from previous runs
            print("🧹 Cleaning up orphaned containers...")
            self.docker_service.cleanup_orphaned_containers()

            # Read the generated files
            player_path = os.path.join(bot_dir, "player.py")
            requirements_path = os.path.join(bot_dir, "requirements.txt")

            if not os.path.exists(player_path):
                error_msg = "player.py not found"
                log_error(error_msg)
                return False, error_msg

            with open(player_path, 'r', encoding='utf-8') as f:
                player_code = f.read()

            requirements_content = ""
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    requirements_content = f.read()

            # Create tar stream with the files
            tar_stream = self.create_tar_stream(player_code, requirements_content)

            # Generate a unique test ID
            sanitized_model_id = model_id.replace("/", "_").replace("-", "_").replace(":", "_").replace("\\", "_").replace("*", "_").replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")
            test_id = f"test_{sanitized_model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_iter{iteration}"

            # Start game server
            server_container_name = self.docker_service.get_game_server_container_name(port)
            print(f"🚀 Starting game server on port {port}...")
            if not self.docker_service.start_game_server(port, sim=True, num_bot=1):
                error_msg = "Failed to start game server"
                log_error(error_msg)
                self.cleanup_containers(server_container_name=server_container_name, port=port, release_port=local_port)
                return False, error_msg

            # Wait for server to be ready
            import time
            time.sleep(5)

            # Start default client
            print("🤖 Starting default client...")
            if not self.docker_service.start_client_container(server_container_name, port, "default", sim=True):
                error_msg = "Failed to start default client"
                log_error(error_msg)
                self.cleanup_containers(server_container_name=server_container_name, port=port, release_port=local_port)
                return False, error_msg

            # Start test client with our code
            print("🧪 Starting test client with generated code...")
            test_client_name = f"test_client_{test_id}"
            if not self.docker_service.start_client_container(server_container_name, port, test_client_name, sim=True):
                error_msg = "Failed to start test client"
                log_error(error_msg)
                self.cleanup_containers(server_container_name=server_container_name, port=port, release_port=local_port)
                return False, error_msg

            # Get test client container name using the correct pattern
            formatted_test_id = self.docker_service.format_username(test_client_name)
            test_client_container_name = f"client_container_{port}_{formatted_test_id}"

            # Load our code into the test client
            print("📦 Loading generated code into test client...")
            if not self.docker_service.load_file_into_container(test_client_container_name, tar_stream):
                error_msg = "Failed to load code into test client"
                log_error(error_msg)
                self.cleanup_containers(test_client_container_name, server_container_name, port, release_port=local_port)
                return False, error_msg

            # Install requirements (simplified logic)
            print("📦 Installing requirements...")
            container = self.docker_service._get_container(test_client_container_name)
            if container:
                exit_code, output = container.exec_run("test -s requirements.txt")
                if exit_code != 0:
                    print("ℹ️  No dependencies to install (empty requirements.txt)")
                else:
                    install_result = self.docker_service.install_python_package(test_client_container_name)
                    if install_result != "success":
                        error_msg = f"Failed to install requirements: {install_result}"
                        log_error(error_msg)
                        self.cleanup_containers(test_client_container_name, server_container_name, port, release_port=local_port)
                        return False, error_msg
                    else:
                        print("✅ Requirements installed successfully")
            else:
                error_msg = "Container not found for requirements installation"
                log_error(error_msg)
                self.cleanup_containers(test_client_container_name, server_container_name, port, release_port=local_port)
                return False, error_msg

            # Validate the code
            print("🔍 Validating generated code...")
            validation_result = self.docker_service.malform_file_client_check(test_client_container_name)
            if validation_result != "success":
                error_msg = f"Code validation failed: {validation_result}"
                log_error(error_msg)
                self.cleanup_containers(test_client_container_name, server_container_name, port, release_port=local_port)
                return False, error_msg

            # Wait for game to complete
            print("⏳ Waiting for game to complete...")
            max_wait_time = 60  # 1 minute
            wait_time = 0
            while wait_time < max_wait_time:
                status = self.docker_service.check_game_container_status(port, sim=True)
                if status.value == "DONE":
                    break
                time.sleep(10)
                wait_time += 10
                print(f"⏳ Game status: {status.value} ({wait_time}s elapsed)")

            if wait_time >= max_wait_time:
                error_msg = "Game timed out"
                log_error(error_msg)
                try:
                    poker_client_log = self.docker_service.get_poker_client_log(test_client_container_name)
                    log_error(f"Poker client log content:\n{poker_client_log}")
                    error_msg += f"\n\nPoker client log details:\n{poker_client_log}"
                except Exception as e:
                    log_error(f"Error reading poker client log: {str(e)}")
                    error_msg += f"\n\nError reading logs: {str(e)}"

                self.cleanup_containers(test_client_container_name, server_container_name, port, release_port=local_port)
                return False, error_msg

            # Collect results
            print("📊 Collecting game results...")
            success, error_msg = self.collect_game_results(
                verified_dir, port, test_client_container_name, server_container_name, iteration
            )

            # Cleanup
            self.cleanup_containers(test_client_container_name, server_container_name, port, release_port=local_port)
            return success, error_msg

        except Exception as e:
            error_msg = f"Game test failed with exception: {str(e)}"
            log_error(error_msg)
            self.cleanup_containers(test_client_container_name, server_container_name, port, release_port=local_port)
            return False, error_msg

    def collect_game_results(self, verified_dir: str, port: int, test_client_container: str, server_container: str, iteration: int) -> Tuple[bool, str]:
        """Collect game results and save to verified directory - FIXED success detection"""
        try:
            error_log_path = os.path.join(verified_dir, "error.log")
            errors = []
            game_logs_found = False
            game_logs_saved_count = 0

            try:
                # Get container logs for debugging but don't treat warnings as errors
                logs = self.docker_service.get_container_logs(test_client_container, tail=100)
                
                # Only treat actual errors as problems (not warnings)
                if any(keyword in logs.lower() for keyword in ['fatal', 'traceback', 'syntaxerror', 'importerror']):
                    errors.append(f"Container logs contain critical errors:\n{logs}")

                # Get poker client log for information (not necessarily errors)
                try:
                    poker_client_log = self.docker_service.get_poker_client_log(test_client_container)
                    if poker_client_log.strip():
                        # Only include if it has actual errors, not just info logs
                        poker_log_lower = poker_client_log.lower()
                        if any(error_keyword in poker_log_lower for error_keyword in 
                              ['error', 'exception', 'failed', 'timeout', 'invalid', 'syntax']):
                            errors.append(f"Poker client log:\n{poker_client_log}")
                            print("🎯 Poker client logs contain errors - including in error log")
                        else:
                            print("📝 Poker client logs contain no critical errors")
                except Exception as e:
                    errors.append(f"Error reading poker client log: {str(e)}")

            except Exception as e:
                errors.append(f"Error collecting logs: {str(e)}")

            # Create username to player ID mapping using actual connection logs
            username_to_player_id = {}

            # Handle default client
            default_formatted_username = self.docker_service.format_username("default")
            default_container_name = f"client_container_{port}_{default_formatted_username}"
            default_player_id = self.docker_service.extract_player_id_from_log(default_container_name)
            if default_player_id is not None:
                username_to_player_id["default"] = default_player_id
                print(f"Player ID: default -> {default_player_id}")
            else:
                print(f"Failed to extract player ID for default")

            # Handle test client
            test_player_id = self.docker_service.extract_player_id_from_log(test_client_container)
            if test_player_id is not None:
                username_to_player_id[test_client_container] = test_player_id
                print(f"Player ID: {test_client_container} -> {test_player_id}")
            else:
                print(f"Failed to extract player ID for {test_client_container}")

            # Try to get game logs from server container
            try:
                container = self.docker_service._get_container(server_container)
                if not container:
                    errors.append(f"Container '{server_container}' not found.")
                else:
                    ls_command = "ls /app/output"
                    exit_code, output = container.exec_run(cmd=ls_command)
                    if exit_code != 0:
                        errors.append(f"Could not list files in /app/output: {output.decode()}")
                    else:
                        files = output.decode().splitlines()
                        game_log_files = [f for f in files if f.startswith("game_log_") and f.endswith(".json")]
                        
                        if not game_log_files:
                            errors.append("No game log files found in container output.")
                        else:
                            print(f"Found {len(game_log_files)} game log files: {game_log_files}")
                            game_logs_found = True

                            # Read all game log files and create a mapping
                            games_map = {}
                            for log_filename in game_log_files:
                                try:
                                    # Extract game number from filename
                                    parts = log_filename.split("_")
                                    if len(parts) >= 3:
                                        game_num = int(parts[2])
                                    else:
                                        game_num = len(games_map) + 1

                                    log_filepath = f"/app/output/{log_filename}"
                                    bits, stat = container.get_archive(log_filepath)
                                    file_obj = io.BytesIO()
                                    for chunk in bits:
                                        file_obj.write(chunk)
                                    file_obj.seek(0)

                                    with tarfile.open(fileobj=file_obj) as tar:
                                        member = tar.getmembers()[0]
                                        extracted_file = tar.extractfile(member)
                                        if not extracted_file:
                                            print(f"Failed to extract {log_filename}")
                                            continue

                                        game_data = json.loads(extracted_file.read().decode('utf-8'))
                                        games_map[game_num] = game_data

                                except Exception as e:
                                    print(f"Failed to process {log_filename}: {e}")
                                    continue

                            if games_map:
                                print(f"Successfully read {len(games_map)} games: {sorted(games_map.keys())}")

                                # Save each game log to verified directory
                                for i, (game_num, game_data) in enumerate(sorted(games_map.items()), 1):
                                    # Create reverse mapping
                                    player_id_to_username = {str(player_id): username for username, player_id in username_to_player_id.items()}
                                    game_data["usernameMapping"] = username_to_player_id
                                    game_data["playerIdToUsername"] = player_id_to_username

                                    # Save to verified iteration directory
                                    game_log_path = os.path.join(verified_dir, f"gamelog_{i}.json")
                                    with open(game_log_path, 'w', encoding='utf-8') as f:
                                        json.dump(game_data, f, indent=2)
                                    print(f"✅ Saved game log {i} to {game_log_path}")
                                    game_logs_saved_count += 1
                            else:
                                errors.append("No valid game data found in log files.")

            except Exception as e:
                errors.append(f"Exception getting game log: {str(e)}")

            # Save error log with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write(f"Game Test Results for Iteration {iteration} - {timestamp}\n")
                f.write("=" * 60 + "\n\n")

                if errors:
                    f.write("ERRORS DETECTED:\n")
                    f.write("-" * 20 + "\n")
                    for error in errors:
                        f.write(f"{error}\n\n")
                else:
                    f.write("No errors detected during game test.\n")

                # Add container logs for debugging
                f.write("\nCONTAINER LOGS:\n")
                f.write("-" * 20 + "\n")
                try:
                    container_logs = self.docker_service.get_container_logs(test_client_container, tail=50)
                    f.write(f"Test Client Logs:\n{container_logs}\n\n")
                except Exception as e:
                    f.write(f"Failed to get container logs: {str(e)}\n")

                f.write("\nPOKER CLIENT LOGS:\n")
                f.write("-" * 20 + "\n")
                try:
                    poker_client_log = self.docker_service.get_poker_client_log(test_client_container)
                    if poker_client_log:
                        poker_log_lower = poker_client_log.lower()
                        if any(error_keyword in poker_log_lower for error_keyword in 
                              ['error', 'exception', 'failed', 'timeout', 'invalid', 'syntax']):
                            f.write(f"Poker Client Log:\n{poker_client_log}\n\n")
                        else:
                            f.write("Poker Client Log: No critical errors detected in poker client logs\n\n")
                    else:
                        f.write("Poker Client Log: No poker client logs available\n\n")
                except Exception as e:
                    f.write(f"Failed to get poker client logs: {str(e)}\n")

            # FIXED: Better success detection logic
            # Success if we found and saved game logs, regardless of minor warnings
            is_successful = game_logs_found and game_logs_saved_count >= 10 and len([e for e in errors if 'critical' in e.lower() or 'fatal' in e.lower()]) == 0
            
            status_msg = "Game test completed successfully" if is_successful else "Game test completed with issues"
            return is_successful, status_msg

        except Exception as e:
            return False, f"Failed to collect results: {str(e)}"

    def save_code_blocks_to_bot_directory(self, python_code: str, text_content: str, model_id: str, existing_dir: str = None) -> str:
        """Save extracted code blocks to bot directory"""
        try:
            if existing_dir and os.path.exists(existing_dir):
                dir_path = existing_dir
                print(f"📁 Updating existing directory: {dir_path}")
            else:
                if not os.path.exists("bot"):
                    os.makedirs("bot")

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                model_name = model_id.replace("/", "_").replace("-", "_").replace(":", "_").replace("\\", "_").replace("*", "_").replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")
                dir_name = f"{model_name}_{timestamp}"
                dir_path = os.path.join("bot", dir_name)
                os.makedirs(dir_path, exist_ok=True)
                print(f"📁 Created new directory: {dir_path}")

            # Save player.py
            player_path = os.path.join(dir_path, "player.py")
            with open(player_path, 'w', encoding='utf-8') as f:
                f.write(python_code)
            print(f"✅ Python code saved to: {player_path}")

            # Save requirements.txt
            requirements_path = os.path.join(dir_path, "requirements.txt")
            with open(requirements_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            print(f"✅ Text content saved to: {requirements_path}")

            return dir_path

        except Exception as e:
            print(f"Error saving code blocks: {e}")
            return ""

    def save_result_to_log(self, result: Dict[str, Any], model_id: str, prompt: str, output_file: str = "output.log", save_code_blocks: bool = True) -> None:
        """Save the result to output.log with timestamp and metadata"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Extract the response content
            response_content = ""
            if "choices" in result and len(result["choices"]) > 0:
                response_content = result["choices"][0]["message"]["content"]

            # Prepare log entry
            log_entry = f"""
{'='*80}
TIMESTAMP: {timestamp}
MODEL: {model_id}
PROMPT LENGTH: {len(prompt)} characters
RESPONSE LENGTH: {len(response_content)} characters
USAGE: {json.dumps(result.get('usage', {}), indent=2)}

PROMPT:
{prompt}

RESPONSE:
{response_content}

RAW API RESPONSE:
{json.dumps(result, indent=2)}
{'='*80}
"""

            # Write to log file
            with open(output_file, 'a', encoding='utf-8') as file:
                file.write(log_entry)

            print(f"✅ Result saved to {output_file}")
            print(f"📝 Response length: {len(response_content)} characters")
            print(f"💾 Usage: {result.get('usage', {})}")

            # Extract and save code blocks (only if requested)
            if save_code_blocks and response_content:
                python_code, text_content = self.extract_code_blocks(response_content)
                if python_code or text_content:
                    bot_dir = self.save_code_blocks_to_bot_directory(python_code, text_content, model_id)
                    if bot_dir:
                        print(f"📁 Code blocks saved to: {bot_dir}")

                        # Test the generated code
                        if self.docker_service:
                            test_success, test_error = self.test_generated_code(bot_dir, model_id)
                            if test_success:
                                print("✅ Game test completed successfully!")
                            else:
                                print(f"⚠️ Game test failed: {test_error}")
                        else:
                            print("⚠️ Docker service not available - skipping game test")
                else:
                    print("⚠️ No code blocks found in response")

        except Exception as e:
            print(f"Error saving to log: {e}")

def main():
    """Main function to run the prompt processor"""
    print("🤖 OpenRouter Prompt Processor")
    print("=" * 50)

    try:
        # Initialize processor
        processor = OpenRouterPromptProcessor()

        # Get available models
        print("📡 Fetching available models...")
        models = processor.get_available_models()
        if not models:
            print("❌ No models available. Check your API key and internet connection.")
            return

        # Display models
        processor.display_models(models)

        # Select model
        selected_model = processor.select_model(models)
        if not selected_model:
            print("👋 Goodbye!")
            return

        # Read prompt from file
        print("\n📖 Reading prompt from generate.txt...")
        try:
            prompt = processor.read_prompt_from_file("prompt/generate.txt")
            print(f"✅ Prompt loaded ({len(prompt)} characters)")
        except Exception as e:
            print(f"❌ Error reading prompt: {e}")
            return

        # Get processing parameters
        print("\n⚙️  Processing Parameters:")
        try:
            temperature = float(input("Temperature (0.0-2.0, default 1.0): ") or "1.0")
            max_tokens = int(input("Max tokens (default 9000): ") or "9000")
        except ValueError:
            print("Using default parameters...")
            temperature = 1.0
            max_tokens = 9000

        # Process the prompt
        print(f"\n🚀 Processing prompt with {selected_model['id']}...")
        print("⏳ This may take a moment...")

        result = processor.process_prompt(
            model_id=selected_model['id'],
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Save result
        processor.save_result_to_log(result, selected_model['id'], prompt)

        # Show preview
        if "choices" in result and len(result["choices"]) > 0:
            response_content = result["choices"][0]["message"]["content"]
            print(f"\n📋 Response Preview (first 200 chars):")
            print(f"{response_content[:200]}...")

        print("\n🎉 Processing complete!")

    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
OpenAI Direct API Client - FIXED for Responses API
Properly handles the nested output structure from OpenAI's Responses API
"""

import os
import json
import requests
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class OpenAIDirectProcessor:
    """OpenAI Direct API processor with proper Responses API parsing"""
    
    def __init__(self, api_key: Optional[str] = None, docker_service=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file")
        
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.docker_service = docker_service
        
        # Models that use Responses API vs Chat Completions
        self.responses_api_models = ['gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'o3-pro', 'o3', 'o4-mini']
        self.reasoning_model_keywords = ['o1', 'o3', 'o4']

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available OpenAI models"""
        return [
            {
                "id": "openai/gpt-5",
                "provider": {"id": "openai"},
                "context_length": 400000,
                "pricing": {"prompt": "0.005", "completion": "0.015"}
            },
            {
                "id": "openai/o3-pro", 
                "provider": {"id": "openai"},
                "context_length": 200000,
                "pricing": {"prompt": "0.020", "completion": "0.080"}
            }
        ]

    def _is_reasoning_model(self, model_id: str) -> bool:
        """Check if the model is a reasoning model"""
        return any(keyword in model_id.lower() for keyword in self.reasoning_model_keywords)

    def _map_model_id(self, model_id: str) -> str:
        """Map our model_id format to OpenAI's actual model names"""
        if "gpt-5" in model_id:
            return "gpt-5"
        elif "o3-pro" in model_id:
            return "o3-pro"
        elif "o3" in model_id:
            return "o3"
        else:
            return "gpt-4"

    def _uses_responses_api(self, openai_model: str) -> bool:
        """Check if model uses Responses API instead of Chat Completions"""
        return any(model in openai_model for model in self.responses_api_models)

    def _parse_responses_api_output(self, result: dict) -> dict:
        """FIXED: Parse the actual OpenAI Responses API format"""
        if 'output' not in result:
            raise Exception(f"No 'output' field found in Responses API response: {result}")
        
        outputs = result['output']
        message_part = None
        reasoning_part = None
        
        # Find the message and reasoning parts in the output array
        for output_item in outputs:
            if output_item.get('type') == 'message':
                message_part = output_item
            elif output_item.get('type') == 'reasoning':
                reasoning_part = output_item
        
        if message_part is None:
            raise Exception(f"No message output found in response. Available types: {[item.get('type') for item in outputs]}")
        
        # Extract text content from the message part
        content_items = message_part.get('content', [])
        text_content = ''
        
        for content_item in content_items:
            if content_item.get('type') == 'output_text':
                text_content = content_item.get('text', '')
                break
        
        if not text_content:
            available_types = [item.get('type') for item in content_items]
            raise Exception(f"No output_text found in message content. Available types: {available_types}")
        
        # Convert to Chat Completions format for compatibility
        converted_result = {
            "choices": [{
                "message": {
                    "content": text_content,
                    "role": "assistant"
                },
                "finish_reason": "stop"
            }],
            "usage": result.get("usage", {}),
            "model": result.get("model", ""),
            "id": result.get("id", ""),
            "object": "chat.completion"
        }
        
        # Include reasoning if available
        if reasoning_part:
            converted_result["reasoning"] = reasoning_part
        
        return converted_result

    def process_prompt(self, model_id: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Process prompt with OpenAI Direct API - FIXED for Responses API"""
        is_reasoning_model = self._is_reasoning_model(model_id)
        openai_model = self._map_model_id(model_id)
        uses_responses_api = self._uses_responses_api(openai_model)
        
        # FIXED: Use different API endpoints and payloads
        if uses_responses_api:
            # Use Responses API for GPT-5, O3-Pro, etc.
            endpoint = f"{self.base_url}/responses"
            payload = {
                "model": openai_model,
                "input": prompt,  # Use 'input' instead of 'messages'
            }
            
            # Add reasoning configuration for reasoning models
            if is_reasoning_model:
                payload["reasoning"] = {"effort": "medium"}
                print(f"🧠 Using Responses API with reasoning for: {openai_model}")
            else:
                # Add text configuration for non-reasoning models
                payload["text"] = {"verbosity": "medium"}
                print(f"🤖 Using Responses API for: {openai_model}")
            
        else:
            # Fallback to Chat Completions API for older models
            endpoint = f"{self.base_url}/chat/completions"
            payload = {
                "model": openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 9000),
                "stream": False
            }
            
            if not is_reasoning_model:
                payload["temperature"] = kwargs.get("temperature", 1.0)
            
            print(f"🤖 Using Chat Completions API for: {openai_model}")

        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=600  # Longer timeout for reasoning models
            )

            if response.status_code != 200:
                raise Exception(f"OpenAI API request failed: {response.status_code} - {response.text}")

            print(f"📊 Response status: {response.status_code}")
            print(f"📊 Response size: {len(response.text)} characters")

            result = response.json()
            
            # FIXED: Handle different response formats
            if uses_responses_api:
                # Parse the new Responses API format
                return self._parse_responses_api_output(result)
            else:
                # Standard Chat Completions format
                return result

        except requests.exceptions.Timeout:
            raise Exception("OpenAI Direct API request timed out - reasoning models may take several minutes")
        except Exception as e:
            raise Exception(f"Error processing OpenAI Direct prompt: {e}")

    def read_prompt_from_file(self, file_path: str = "prompt/generate.txt") -> str:
        """Read prompt from file"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Prompt file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            raise Exception(f"Error reading prompt file: {e}")

    def extract_code_blocks(self, response_content: str) -> Tuple[str, str]:
        """FIXED: Extract Python and text code blocks with correct regex patterns"""
        python_code = ""
        text_content = ""
        
        # FIXED: Correct regex patterns matching the working OpenRouter version
        python_pattern = r'```python\s*\n(.*?)\n```'
        python_matches = re.findall(python_pattern, response_content, re.DOTALL)
        if python_matches:
            python_code = python_matches[0].strip()
        
        # FIXED: Extract text/requirements blocks with proper patterns
        text_patterns = [
            r'```text\s*\n(.*?)\n``````'
            r'``````',       # ```
            r'```\s*\n(.*?)\n``````'
        ]
        
        for pattern in text_patterns:
            text_matches = re.findall(pattern, response_content, re.DOTALL)
            if text_matches:
                # Take the first match that doesn't start with 'python'
                for match in text_matches:
                    if match.strip() and not match.strip().lower().startswith('python'):
                        text_content = match.strip()
                        break
                if text_content:
                    break
        
        return python_code, text_content

    def save_result_to_log(self, result: Dict[str, Any], model_id: str, prompt: str, output_file: str = "output.log", save_code_blocks: bool = True) -> None:
        """Save result to log"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            response_content = ""
            
            # FIXED: Access list with numeric index [0], not string key ["message"]
            if "choices" in result and len(result["choices"]) > 0:
                response_content = result["choices"][0]["message"]["content"]  # ✅ CORRECT
            
            log_entry = f"""
    {'='*80}
    TIMESTAMP: {timestamp}
    MODEL: {model_id} (OpenAI Direct API)
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

            with open(output_file, 'a', encoding='utf-8') as file:
                file.write(log_entry)

            print(f"✅ Result saved to {output_file}")
            print(f"📝 Response length: {len(response_content)} characters")
            print(f"💾 Usage: {result.get('usage', {})}")

        except Exception as e:
            print(f"Error saving to log: {e}")

    # Delegate methods remain the same...
    def test_generated_code(self, bot_dir: str, model_id: str, iteration: int = 1, port: Optional[int] = None):
        """Delegate to OpenRouter processor's Docker testing logic"""
        if not self.docker_service:
            return False, "Docker service not available"
        
        from llm.prompt_processor import OpenRouterPromptProcessor
        temp_processor = OpenRouterPromptProcessor(docker_service=self.docker_service)
        return temp_processor.test_generated_code(bot_dir, model_id, iteration, port)

    def save_code_blocks_to_bot_directory(self, python_code: str, text_content: str, model_id: str, existing_dir: str = None) -> str:
        """Delegate to OpenRouter processor's directory creation logic"""
        from llm.prompt_processor import OpenRouterPromptProcessor
        temp_processor = OpenRouterPromptProcessor()
        return temp_processor.save_code_blocks_to_bot_directory(python_code, text_content, model_id, existing_dir)

    def create_tar_stream(self, player_code: str, requirements_content: str):
        """Delegate to OpenRouter processor"""
        from llm.prompt_processor import OpenRouterPromptProcessor
        temp_processor = OpenRouterPromptProcessor()
        return temp_processor.create_tar_stream(player_code, requirements_content)

    def cleanup_containers(self, test_client_container_name=None, server_container_name=None, port=None, release_port=True):
        """Delegate to OpenRouter processor"""
        from llm.prompt_processor import OpenRouterPromptProcessor
        temp_processor = OpenRouterPromptProcessor(docker_service=self.docker_service)
        return temp_processor.cleanup_containers(test_client_container_name, server_container_name, port, release_port)

#!/usr/bin/env python3
"""
Quick Prompt Runner for OpenRouter API

Usage:
    python llm/run_prompt.py                    # Interactive mode
    python llm/run_prompt.py --list             # List models only
    python llm/run_prompt.py --model <model_id> # Use specific model
    python llm/run_prompt.py --help             # Show help
"""

import os
import sys
import argparse
import re
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import requests
from datetime import datetime

# Load environment variables
load_dotenv()

class QuickPromptRunner:
    """Quick prompt runner for OpenRouter API"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/gambling-with-bot",
            "X-Title": "Quick Prompt Runner"
        }
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Get available models"""
        try:
            response = requests.get(f"{self.base_url}/models", headers=self.headers)
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"Error fetching models: {e}")
            return []
    
    def list_models(self):
        """List available models"""
        models = self.get_models()
        if not models:
            print("No models available")
            return
        
        print("\nAvailable Models:")
        print(f"{'#':<3} {'Model ID':<35} {'Provider':<12} {'Context':<8}")
        print("-" * 60)
        
        for i, model in enumerate(models, 1):
            model_id = model.get("id", "Unknown")
            provider = model.get("provider", {}).get("id", "Unknown")
            context = model.get("context_length", "N/A")
            print(f"{i:<3} {model_id:<35} {provider:<12} {context:<8}")
    
    def process_prompt(self, model_id: str, prompt: str, temperature: float = 1.0, max_tokens: int = 9000) -> Dict[str, Any]:
        """Process prompt with specified model"""
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "include_reasoning": True
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
        
        return response.json()
    
    def read_prompt_file(self, file_path: str = "prompt/generate.txt") -> str:
        """Read prompt from file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
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
    
    def save_code_blocks_to_bot_directory(self, python_code: str, text_content: str, model_id: str) -> str:
        """
        Save extracted code blocks to bot directory with specified structure
        
        Args:
            python_code: Python code to save as player.py
            text_content: Text content to save as requirements.txt
            model_id: Model ID for directory naming
            
        Returns:
            Path to the created directory
        """
        try:
            # Create bot directory if it doesn't exist
            if not os.path.exists("bot"):
                os.makedirs("bot")
            
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Clean model name for directory
            model_name = model_id.replace("/", "_").replace("-", "_")
            
            # Create directory name
            dir_name = f"{model_name}_{timestamp}"
            dir_path = os.path.join("bot", dir_name)
            
            # Create directory
            os.makedirs(dir_path, exist_ok=True)
            
            # Save player.py
            if python_code:
                player_path = os.path.join(dir_path, "player.py")
                with open(player_path, 'w', encoding='utf-8') as f:
                    f.write(python_code)
                print(f"✅ Python code saved to: {player_path}")
            
            # Save requirements.txt
            if text_content:
                requirements_path = os.path.join(dir_path, "requirements.txt")
                with open(requirements_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                print(f"✅ Text content saved to: {requirements_path}")
            
            return dir_path
            
        except Exception as e:
            print(f"Error saving code blocks: {e}")
            return ""
    
    def save_to_log(self, result: Dict[str, Any], model_id: str, prompt: str, output_file: str = "output.log"):
        """Save result to log file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        response_content = ""
        if "choices" in result and len(result["choices"]) > 0:
            response_content = result["choices"][0]["message"]["content"]
        
        log_entry = f"""
{'='*80}
TIMESTAMP: {timestamp}
MODEL: {model_id}
PROMPT LENGTH: {len(prompt)} characters
RESPONSE LENGTH: {len(response_content)} characters
USAGE: {result.get('usage', {})}

PROMPT:
{prompt}

RESPONSE:
{response_content}

RAW API RESPONSE:
{result}
{'='*80}

"""
        
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(f"✅ Result saved to {output_file}")
        print(f"📝 Response length: {len(response_content)} characters")
        
        # Extract and save code blocks
        if response_content:
            python_code, text_content = self.extract_code_blocks(response_content)
            
            if python_code or text_content:
                bot_dir = self.save_code_blocks_to_bot_directory(python_code, text_content, model_id)
                if bot_dir:
                    print(f"📁 Code blocks saved to: {bot_dir}")
            else:
                print("⚠️  No code blocks found in response")
        
        # Show preview
        if response_content:
            print(f"\n📋 Preview (first 300 chars):")
            print(f"{response_content[:300]}...")
    
    def interactive_mode(self):
        """Run in interactive mode"""
        print("🤖 Quick Prompt Runner - Interactive Mode")
        print("=" * 50)
        
        # List models
        self.list_models()
        
        # Get model selection
        models = self.get_models()
        if not models:
            return
        
        while True:
            try:
                choice = input(f"\nSelect model (1-{len(models)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q':
                    return
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(models):
                    selected_model = models[choice_num - 1]
                    break
                else:
                    print(f"Please enter 1-{len(models)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                return
        
        # Read prompt
        try:
            prompt = self.read_prompt_file()
            print(f"✅ Prompt loaded ({len(prompt)} characters)")
        except Exception as e:
            print(f"❌ Error reading prompt: {e}")
            return
        
        # Process
        print(f"\n🚀 Processing with {selected_model['id']}...")
        try:
            result = self.process_prompt(selected_model['id'], prompt)
            self.save_to_log(result, selected_model['id'], prompt)
            print("🎉 Complete!")
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Quick Prompt Runner for OpenRouter")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--model", type=str, help="Model ID to use")
    parser.add_argument("--prompt-file", type=str, default="prompt/generate.txt", help="Prompt file path")
    parser.add_argument("--output", type=str, default="output.log", help="Output log file")
    parser.add_argument("--temperature", type=float, default=1.0, help="Temperature (0.0-2.0)")
    parser.add_argument("--max-tokens", type=int, default=9000, help="Max tokens")
    
    args = parser.parse_args()
    
    try:
        runner = QuickPromptRunner()
        
        if args.list:
            runner.list_models()
            return
        
        if args.model:
            # Non-interactive mode with specific model
            try:
                prompt = runner.read_prompt_file(args.prompt_file)
                print(f"Processing with {args.model}...")
                result = runner.process_prompt(args.model, prompt, args.temperature, args.max_tokens)
                runner.save_to_log(result, args.model, prompt, args.output)
                print("🎉 Complete!")
            except Exception as e:
                print(f"❌ Error: {e}")
                sys.exit(1)
        else:
            # Interactive mode
            runner.interactive_mode()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
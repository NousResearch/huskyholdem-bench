"""
OpenRouter API Chat Completion Example
"""

import os
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

class OpenRouterClient:
    """Client for interacting with OpenRouter API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://openrouter.ai/api/v1"):
        """
        Initialize the OpenRouter client
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: Base URL for OpenRouter API
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY in .env file")
        
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional: for analytics
            "X-Title": "OpenRouter Example"  # Optional: for analytics
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        include_reasoning: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to OpenRouter
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use for completion
            temperature: Controls randomness (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            API response as dictionary
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            "include_reasoning": include_reasoning,
            **kwargs
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_models(self) -> Dict[str, Any]:
        """Get list of available models"""
        response = requests.get(
            f"{self.base_url}/models",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get models: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific model"""
        models = self.get_models()
        for model in models.get("data", []):
            if model["id"] == model_id:
                return model
        raise ValueError(f"Model {model_id} not found")
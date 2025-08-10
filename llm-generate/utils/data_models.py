from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ProcessingConfig:
    """Configuration for processing parameters"""
    temperature: float = 1.0
    max_tokens: int = 30000
    k_iterations: int = 5
    prompt_file: str = "prompt/generate.txt"

@dataclass
class IterationResult:
    """Result of a single iteration"""
    iteration: int
    bot_dir: Optional[str]
    success: bool
    error: str
    result: Optional[Dict[str, Any]]
    code: Optional[str] = None
    requirements: Optional[str] = None
    error_log: Optional[str] = None

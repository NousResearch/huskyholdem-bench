class TokenCalculator:
    """Handles dynamic token calculation for iterative generation"""
    
    @staticmethod
    def count_tokens_estimate(text: str) -> int:
        """Rough token estimation (4 characters per token average)"""
        return len(text) // 4
    
    @staticmethod
    def calculate_safe_max_tokens(current_prompt: str, iteration: int, 
                                 max_iterations: int = 5, context_limit: int = 400000) -> int:
        """Calculate safe max tokens for remaining iterations"""
        current_tokens = TokenCalculator.count_tokens_estimate(current_prompt)
        estimated_growth_per_remaining_iteration = 8000
        remaining_iterations = max_iterations - iteration
        
        estimated_final_input = current_tokens + (remaining_iterations * estimated_growth_per_remaining_iteration)
        
        # Fixed bug: Better calculation with proper safety margin
        available_tokens = context_limit - estimated_final_input
        safe_max_tokens = min(
            int(available_tokens / 1.2),  # 20% safety buffer
            128000  # Model's max output limit
        )
        
        return max(safe_max_tokens, 10000)  # Minimum 10k tokens

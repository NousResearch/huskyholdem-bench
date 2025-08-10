import json
from typing import List, Dict, Any, Optional
from .feedback_analyzer import FeedbackAnalyzer

class PromptBuilder:
    """Handles creation of feedback prompts for iterative generation"""
    
    @staticmethod
    def create_feedback_prompt(original_prompt: str, iteration: int, feedback_data: Dict[str, Any],
                             previous_code: Optional[str] = None,
                             previous_requirements: Optional[str] = None) -> str:
        """Create an improved prompt based on feedback from previous iteration"""
        
        # Build base prompt
        feedback_prompt = f"""
{original_prompt}

ITERATION {iteration} FEEDBACK AND IMPROVEMENT REQUEST:
You are now working on iteration {iteration}. Based on the previous iteration results and code, please improve the implementation.

PREVIOUS RESULTS:
- Success: {feedback_data.get('success', False)}
- Error Message: {feedback_data.get('error_message', 'None')}
"""
        
        # Include errors
        if feedback_data.get('errors'):
            feedback_prompt += f"""
ERRORS ENCOUNTERED:
{feedback_data['errors']}

Please fix these specific errors in your implementation.
"""
        
        # Include error lines with context
        if feedback_data.get('error_lines_with_context'):
            feedback_prompt += f"""
ERROR LINES WITH CONTEXT:
{feedback_data['error_lines_with_context']}

Please investigate these specific error lines in your code.
"""
        
        # Include game performance data
        if feedback_data.get('game_logs'):
            bot_player_ids, bot_id_info, bot_performance_summary = FeedbackAnalyzer.extract_bot_performance(feedback_data['game_logs'])
            
            feedback_prompt += f"""
GAME PERFORMANCE DATA:
{bot_id_info}
{bot_performance_summary}
{json.dumps(feedback_data['game_logs'], indent=2)}

IMPORTANT: When analyzing the game performance data above, focus on the player ID that corresponds to YOUR bot implementation.
Look for your bot's performance in the 'gameScores' field, which shows the delta gain/loss for each individual game.

PERFORMANCE METRICS EXPLANATION:
- 'gameScores': Shows the profit/loss for each individual game (this is what matters most)
- Positive gameScore = Profit in that game
- Negative gameScore = Loss in that game
- Focus on improving your strategy to achieve positive gameScores consistently

Please analyze YOUR bot's gameScore performance and improve the strategy based on these results.
"""
        
        # Include validation errors
        if feedback_data.get('validation_errors'):
            feedback_prompt += f"""
CODE VALIDATION ERRORS:
{feedback_data['validation_errors']}

Please fix these validation issues in your code.
"""
        
        # Include poker client errors
        if feedback_data.get('poker_client_errors'):
            feedback_prompt += f"""
POKER CLIENT ERRORS:
{feedback_data['poker_client_errors']}

Please investigate these errors in your poker client logs and fix any issues in your implementation.
"""
        
        # Add improvement instructions
        feedback_prompt += f"""
IMPROVEMENT INSTRUCTIONS:
1. You are on iteration {iteration} - build upon the previous code
2. Analyze the errors and game performance data above
3. Fix any syntax, import, or runtime errors from the previous iteration
4. Improve the poker strategy based on game results
5. Ensure the code follows the exact template requirements
6. Return the improved implementation in the same format (Python code block + requirements.txt block)

Focus on making the bot more competitive and error-free. You can see exactly what was wrong with the previous version and should fix those specific issues.
"""
        
        return feedback_prompt

import os
import json
import time
from typing import Dict, List, Tuple, Any

class FeedbackAnalyzer:
    """Handles analysis and collection of feedback data from iterations"""
    
    @staticmethod
    def extract_bot_performance(game_logs: List[Dict]) -> Tuple[List[str], str, str]:
        """Extract bot player IDs and create performance summary"""
        bot_player_ids = []
        for game in game_logs:
            if 'botPlayerId' in game:
                bot_player_ids.append(game['botPlayerId'])
        
        bot_id_info = ""
        bot_performance_summary = ""
        
        if bot_player_ids:
            unique_bot_ids = list(set(bot_player_ids))
            bot_id_info = f"""
YOUR BOT PLAYER IDS: {unique_bot_ids}
When analyzing the game data below, focus on these player IDs as they represent YOUR bot's performance.
"""
            
            # Calculate bot performance metrics
            if game_logs:
                total_score = 0
                game_count = 0
                for game in game_logs:
                    if 'botPerformance' in game:
                        perf = game['botPerformance']
                        total_score += perf.get('gameScore', 0)
                        game_count += 1
                
                if game_count > 0:
                    avg_score = total_score / game_count
                    bot_performance_summary = f"""
YOUR BOT PERFORMANCE SUMMARY (across {game_count} games):
- Average Game Score (Delta per Game): {avg_score:.2f}
- Total Game Score: {total_score:.2f}
- Total Games Played: {game_count}

Performance Analysis:
- Positive scores indicate profit per game
- Negative scores indicate losses per game
- Focus on improving average game score for better performance
"""
        
        return bot_player_ids, bot_id_info, bot_performance_summary
    
    @staticmethod
    def collect_feedback_data(bot_dir: str, iteration: int) -> Dict[str, Any]:
        """Collect feedback data from the verified iteration directory"""
        feedback_data = {
            'success': False,
            'error_message': '',
            'errors': '',
            'game_logs': [],
            'validation_errors': ''
        }
        
        if not bot_dir or not os.path.exists(bot_dir):
            feedback_data['error_message'] = f"Bot directory not found: {bot_dir}"
            return feedback_data
        
        verified_dir = os.path.join(bot_dir, "verified", f"{iteration}_iteration")
        
        # Read current code from iteration-specific directory
        FeedbackAnalyzer._read_iteration_code(verified_dir, feedback_data, iteration)
        
        if not os.path.exists(verified_dir):
            feedback_data['error_message'] = f"Verified directory for iteration {iteration} not found: {verified_dir}"
            print(f"⚠️ Verified directory not found: {verified_dir}")
            FeedbackAnalyzer._read_game_logs(bot_dir, feedback_data, iteration)
            return feedback_data
        
        # Read error log and game logs
        FeedbackAnalyzer._read_error_log(verified_dir, feedback_data)
        FeedbackAnalyzer._read_game_logs(verified_dir, feedback_data, iteration)
        
        print(f"✅ Feedback data collection completed for iteration {iteration}")
        return feedback_data
    
    @staticmethod
    def _read_iteration_code(verified_dir: str, feedback_data: Dict[str, Any], iteration: int) -> None:
        """Read iteration-specific code files"""
        try:
            player_path = os.path.join(verified_dir, "player.py")
            requirements_path = os.path.join(verified_dir, "requirements.txt")
            
            if os.path.exists(player_path):
                with open(player_path, 'r', encoding='utf-8') as f:
                    feedback_data['current_code'] = f.read()
            
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    feedback_data['current_requirements'] = f.read()
        except Exception as e:
            print(f"Warning: Could not read iteration {iteration} code for feedback: {e}")
    
    @staticmethod
    def _read_error_log(verified_dir: str, feedback_data: Dict[str, Any]) -> None:
        """Read and parse error log"""
        error_log_path = os.path.join(verified_dir, "error.log")
        if os.path.exists(error_log_path):
            time.sleep(0.5)  # Ensure file is fully written
            
            try:
                with open(error_log_path, 'r', encoding='utf-8') as f:
                    error_content = f.read()
                
                # Fixed bug: Better error detection logic
                if "No errors detected" in error_content and len(error_content.strip()) < 200:
                    feedback_data['success'] = True
                else:
                    feedback_data['errors'] = error_content
                    error_lines_with_context = FeedbackAnalyzer._extract_error_lines_with_context(error_content)
                    if error_lines_with_context:
                        feedback_data['error_lines_with_context'] = error_lines_with_context
                
                # Extract specific error types
                if "Code validation failed" in error_content:
                    lines = error_content.split('\n')
                    validation_lines = [line for line in lines if any(keyword in line.lower() 
                                      for keyword in ['validation', 'syntax', 'import'])]
                    feedback_data['validation_errors'] = '\n'.join(validation_lines)
                
                # Extract poker client errors
                if "POKER CLIENT LOGS:" in error_content:
                    poker_log_section = error_content.split("POKER CLIENT LOGS:")[1]
                    if "Poker Client Log:" in poker_log_section:
                        poker_log_content = poker_log_section.split("Poker Client Log:")[1].split("\n\n")[0]
                        if poker_log_content.strip():
                            poker_log_lines = poker_log_content.lower()
                            if any(error_keyword in poker_log_lines for error_keyword in 
                                  ['error', 'exception', 'failed', 'timeout', 'invalid', 'syntax']):
                                feedback_data['poker_client_errors'] = poker_log_content.strip()
                                print(f"🎯 Found poker client errors in iteration log")
                
            except Exception as e:
                print(f"⚠️ Error reading error log: {e}")
                feedback_data['errors'] = f"Error reading error log: {str(e)}"
        else:
            feedback_data['errors'] = f"Error log file not found for iteration in {verified_dir}"
    
    @staticmethod
    def _extract_error_lines_with_context(error_content: str) -> str:
        """Extract error lines with 10 lines of context after each error"""
        lines = error_content.split('\n')
        error_sections = []
        
        for i, line in enumerate(lines):
            if any(keyword in line.lower() and "detected" not in line.lower() 
                  for keyword in ['error', 'exception', 'failed', 'timeout', 'invalid', 'syntax']):
                
                error_section = [line]
                for j in range(1, 11):
                    if i + j < len(lines):
                        error_section.append(lines[i + j])
                    else:
                        break
                
                error_sections.append('\n'.join(error_section))
        
        return '\n\n--- NEXT ERROR ---\n\n'.join(error_sections) if error_sections else ""
    
    @staticmethod
    def _read_game_logs(verified_dir: str, feedback_data: Dict[str, Any], iteration: int) -> None:
        """Read and parse game log files"""
        try:
            if not os.path.exists(verified_dir):
                print(f"⚠️ Verified directory not found for iteration {iteration}: {verified_dir}")
                return
            
            game_log_files = [f for f in os.listdir(verified_dir)
                             if f.startswith("gamelog_") and f.endswith(".json")]
            
            print(f"🎮 Found {len(game_log_files)} game log files in iteration {iteration}: {game_log_files}")
            
            if not game_log_files:
                print(f"📝 No game log files found in iteration {iteration} directory")
                return
            
            for log_file in sorted(game_log_files):
                log_path = os.path.join(verified_dir, log_file)
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        game_data = json.load(f)
                    
                    game_summary = FeedbackAnalyzer._extract_game_summary(game_data)
                    feedback_data['game_logs'].append(game_summary)
                    print(f"✅ Successfully read game log: {log_file}")
                    
                except Exception as e:
                    print(f"⚠️ Error reading game log {log_file}: {str(e)}")
                    feedback_data['errors'] += f"\nError reading game log {log_file}: {str(e)}"
            
            print(f"🎯 Total game logs loaded for iteration {iteration}: {len(feedback_data['game_logs'])}")
            
        except Exception as e:
            print(f"⚠️ Error listing game log files in iteration {iteration}: {str(e)}")
            feedback_data['errors'] += f"\nError listing game log files: {str(e)}"
    
    @staticmethod
    def _extract_game_summary(game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key performance metrics from game data"""
        game_summary = {
            'gameId': game_data.get('gameId', 'unknown'),
            'players': game_data.get('usernameMapping', {}),
            'playerNames': game_data.get('playerNames', {}),
            'finalMoney': game_data.get('playerMoney', {}).get('finalMoney', {}),
            'finalDelta': game_data.get('playerMoney', {}).get('finalDelta', {}),
            'gameScores': game_data.get('playerMoney', {}).get('gameScores', {}),
            'rounds': len(game_data.get('rounds', {})),
            'finalBoard': game_data.get('finalBoard', []),
            'playerHands': game_data.get('playerHands', {}),
            'blinds': game_data.get('blinds', {})
        }
        
        # Extract bot player ID for this game
        username_mapping = game_data.get('usernameMapping', {})
        bot_player_id = None
        for username, player_id in username_mapping.items():
            if 'test_client' in username or 'iter' in username:
                bot_player_id = player_id
                break
        
        if bot_player_id:
            game_summary['botPlayerId'] = bot_player_id
            game_summary['botPerformance'] = {
                'finalMoney': game_data.get('playerMoney', {}).get('finalMoney', {}).get(str(bot_player_id), 0),
                'finalDelta': game_data.get('playerMoney', {}).get('finalDelta', {}).get(str(bot_player_id), 0),
                'gameScore': game_data.get('playerMoney', {}).get('gameScores', {}).get(str(bot_player_id), 0)
            }
        
        return game_summary

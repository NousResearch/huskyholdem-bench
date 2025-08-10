import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from .data_models import ProcessingConfig, IterationResult
from .feedback_analyzer import FeedbackAnalyzer
from .prompt_builder import PromptBuilder
from .token_calculator import TokenCalculator

class IterativeGenerator:
    """Handles iterative generation with feedback loops"""
    
    def __init__(self, processor):
        self.processor = processor
        self.feedback_analyzer = FeedbackAnalyzer()
        self.prompt_builder = PromptBuilder()
        self.token_calculator = TokenCalculator()
    
    def run_iterations(self, selected_model: Dict[str, Any], original_prompt: str,
                      config: ProcessingConfig) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Run iterative generation for k iterations with feedback"""
        print(f"\n🔄 Starting iterative generation for {config.k_iterations} iterations...")
        
        current_prompt = original_prompt
        best_result = None
        best_bot_dir = None
        all_results: List[IterationResult] = []
        
        # Create main bot directory
        main_bot_dir = self._create_main_bot_directory(selected_model)
        
        # Fixed bug: Generate port once and reuse it
        port = self.processor.docker_service.generate_random_port()
        
        try:
            for iteration in range(1, config.k_iterations + 1):
                print(f"\n{'='*60}")
                print(f"🔄 ITERATION {iteration}/{config.k_iterations}")
                print(f"{'='*60}")
                
                # Calculate dynamic max tokens
                dynamic_max_tokens = self.token_calculator.calculate_safe_max_tokens(
                    current_prompt, iteration, config.k_iterations
                )
                print(f"🧮 Dynamic max tokens for iteration {iteration}: {dynamic_max_tokens:,}")
                
                # Process iteration
                iteration_result = self._process_single_iteration(
                    iteration, selected_model, current_prompt, config, 
                    main_bot_dir, dynamic_max_tokens, port
                )
                
                all_results.append(iteration_result)
                
                if iteration_result.success:
                    best_result = iteration_result.result
                    best_bot_dir = iteration_result.bot_dir
                
                # Create feedback prompt for next iteration
                if iteration < config.k_iterations:
                    try:
                        current_prompt = self._create_next_iteration_prompt(
                            original_prompt, iteration, iteration_result
                        )
                    except Exception as e:
                        print(f"⚠️ Error creating feedback prompt: {e}")
                        current_prompt = original_prompt
                
                print(f"✅ Iteration {iteration} completed. Success: {iteration_result.success}")
            
            # Display summary
            self._display_iteration_summary(config.k_iterations, main_bot_dir, all_results)
            self._create_summary_log(main_bot_dir, config.k_iterations, all_results, selected_model)
            
            return best_result, best_bot_dir
            
        finally:
            # Fixed bug: Always cleanup port
            self.processor.docker_service.release_port(port)
            self.processor.docker_service.cleanup_containers_by_port(port)
    
    def _create_main_bot_directory(self, selected_model: Dict[str, Any]) -> str:
        """Create main bot directory for all iterations"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Fixed bug: Better sanitization of model name
        model_name = selected_model["id"]
        for char in ['/', '-', ':', '\\', '*', '?', '"', '<', '>', '|', ' ']:
            model_name = model_name.replace(char, '_')
        
        dir_name = f"{model_name}_{timestamp}"
        dir_path = os.path.join("bot", dir_name)
        
        os.makedirs(dir_path, exist_ok=True)
        print(f"📁 Created new directory: {dir_path}")
        
        return dir_path
    
    def _process_single_iteration(self, iteration: int, selected_model: Dict[str, Any],
                                 current_prompt: str, config: ProcessingConfig,
                                 main_bot_dir: str, max_tokens: int, port: int) -> IterationResult:
        """Process a single iteration"""
        print(f"🚀 Processing prompt with {selected_model['id']}...")
        print("⏳ This may take a moment...")
        
        try:
            # Process the prompt
            result = self.processor.process_prompt(
                model_id=selected_model['id'],
                prompt=current_prompt,
                temperature=config.temperature,
                max_tokens=max_tokens
            )
            
            # Save to main bot directory
            bot_output_file = os.path.join(main_bot_dir, f"output_iteration_{iteration}.log")
            self.processor.save_result_to_log(result, selected_model['id'], current_prompt, bot_output_file, save_code_blocks=False)
            
            # Extract and save code
            if "choices" in result and len(result["choices"]) > 0:
                response_content = result["choices"][0]["message"]["content"]
                python_code, text_content = self.processor.extract_code_blocks(response_content)
                
                if not python_code:
                    return IterationResult(
                        iteration=iteration,
                        bot_dir=main_bot_dir,
                        success=False,
                        error="No code blocks found in response",
                        result=result,
                        code=python_code,
                        requirements=text_content
                    )
                
                # Save and test code
                self._save_and_test_code(iteration, selected_model, python_code, text_content, main_bot_dir, port)
                
                # Check for errors
                error_log_path = os.path.join(main_bot_dir, "verified", f"{iteration}_iteration", "error.log")
                if os.path.exists(error_log_path):
                    with open(error_log_path, 'r', encoding='utf-8') as f:
                        error_log_content = f.read()
                    
                    indicators_of_success = [
                        "Found 10 game log files",
                        "Successfully read 10 games",
                        "Saved game log 10 to",
                        "No errors detected"
                    ]
                    
                    # Check if any success indicators are present
                    has_success_indicators = any(indicator in error_log_content for indicator in indicators_of_success)
                    
                    # Check for critical failures (these would indicate real problems)
                    critical_failures = [
                        "Code validation failed",
                        "Import error",
                        "Syntax error", 
                        "Container failed to start",
                        "No code blocks found"
                    ]
                    
                    has_critical_failures = any(failure in error_log_content for failure in critical_failures)
                    
                    # Success if we have success indicators AND no critical failures
                    is_successful = has_success_indicators and not has_critical_failures
                    
                    return IterationResult(
                        iteration=iteration,
                        bot_dir=main_bot_dir,
                        success=is_successful,
                        error="" if is_successful else "Critical errors in game testing",
                        result=result,
                        code=python_code,
                        requirements=text_content,
                        error_log=error_log_content
                    )
                else:
                    return IterationResult(
                        iteration=iteration,
                        bot_dir=main_bot_dir,
                        success=False,
                        error="Error log not found",
                        result=result,
                        code=python_code,
                        requirements=text_content
                    )
                
        except Exception as e:
            print(f"❌ Error in iteration {iteration}: {e}")
            return IterationResult(
                iteration=iteration,
                bot_dir=main_bot_dir,
                success=False,
                error=str(e),
                result=None
            )
    
    def _save_and_test_code(self, iteration: int, selected_model: Dict[str, Any],
                           python_code: str, text_content: str, main_bot_dir: str, port: int) -> None:
        """Save code to main directory and iteration-specific directory, then test"""
        print(f"🔧 Saving code for iteration {iteration}")
        
        # Save to main directory
        player_path = os.path.join(main_bot_dir, "player.py")
        requirements_path = os.path.join(main_bot_dir, "requirements.txt")
        
        with open(player_path, 'w', encoding='utf-8') as f:
            f.write(python_code)
        
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        print(f"✅ Python code saved to: {player_path}")
        print(f"✅ Requirements saved to: {requirements_path}")
        
        # Save iteration-specific code
        iteration_dir = os.path.join(main_bot_dir, "verified", f"{iteration}_iteration")
        os.makedirs(iteration_dir, exist_ok=True)
        
        iteration_player_path = os.path.join(iteration_dir, "player.py")
        iteration_requirements_path = os.path.join(iteration_dir, "requirements.txt")
        
        with open(iteration_player_path, 'w', encoding='utf-8') as f:
            f.write(python_code)
        
        with open(iteration_requirements_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        print(f"✅ Iteration {iteration} code saved to: {iteration_dir}")
        
        # Test the generated code
        if self.processor.docker_service:
            test_success, test_error = self.processor.test_generated_code(
                main_bot_dir, f"{selected_model['id']}_iter_{iteration}", iteration, port=port
            )

            if test_success:
                print("✅ Game test completed successfully!")
            elif test_error and "Game test completed" in test_error:
                # This is actually success - the game completed properly
                print("✅ Game test completed successfully!")
            else:
                print(f"⚠️ Game test failed: {test_error}")
        else:
            print("⚠️ Docker service not available - skipping game test")
      
    def _create_next_iteration_prompt(self, original_prompt: str, iteration: int,
                                     iteration_result: IterationResult) -> str:
        """Create prompt for next iteration based on current results"""
        if iteration_result.success and iteration_result.bot_dir:
            feedback_data = self.feedback_analyzer.collect_feedback_data(iteration_result.bot_dir, iteration)
            feedback_data['success'] = True
            print("📈 Creating improvement prompt based on successful game results...")
        else:
            feedback_data = {
                'success': False,
                'error_message': iteration_result.error,
                'errors': iteration_result.error_log if iteration_result.error_log else iteration_result.error,
                'game_logs': [],
                'validation_errors': ''
            }
            print("🔧 Creating correction prompt based on errors...")
        
        return self.prompt_builder.create_feedback_prompt(
            original_prompt, iteration + 1, feedback_data,
            iteration_result.code, iteration_result.requirements
        )
    
    def _display_iteration_summary(self, k_iterations: int, main_bot_dir: str, all_results: List[IterationResult]) -> None:
        """Display summary of all iterations"""
        print(f"\n{'='*60}")
        print("🎯 ITERATIVE GENERATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total iterations: {k_iterations}")
        print(f"📁 Bot directory: {main_bot_dir}")
        
        for result in all_results:
            status = "✅ SUCCESS" if result.success else "❌ FAILED"
            print(f"Iteration {result.iteration}: {status}")
            if not result.success:
                print(f"  ⚠️ Error: {result.error}")
        
        successful_count = sum(1 for result in all_results if result.success)
        print(f"\nSuccess rate: {successful_count}/{k_iterations} ({(successful_count/k_iterations)*100:.1f}%)")
    
    def _create_summary_log(self, main_bot_dir: str, k_iterations: int, 
                           all_results: List[IterationResult], selected_model: Dict[str, Any]) -> None:
        """Create a summary log file in the main bot directory"""
        try:
            summary_log_path = os.path.join(main_bot_dir, "iteration_summary.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(summary_log_path, 'w', encoding='utf-8') as f:
                f.write(f"Iterative Generation Summary - {timestamp}\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Model: {selected_model['id']}\n")
                f.write(f"Total Iterations: {k_iterations}\n")
                f.write(f"Bot Directory: {main_bot_dir}\n\n")
                
                f.write("ITERATION RESULTS:\n")
                f.write("-" * 20 + "\n")
                for result in all_results:
                    status = "SUCCESS" if result.success else "FAILED"
                    f.write(f"Iteration {result.iteration}: {status}\n")
                    if not result.success:
                        f.write(f"  Error: {result.error}\n")
                
                successful_count = sum(1 for result in all_results if result.success)
                f.write(f"\nSUMMARY:\n")
                f.write(f"- Successful iterations: {successful_count}/{k_iterations}\n")
                f.write(f"- Success rate: {(successful_count/k_iterations)*100:.1f}%\n")
            
            print(f"📄 Summary log created: {summary_log_path}")
            
        except Exception as e:
            print(f"⚠️ Error creating summary log: {e}")

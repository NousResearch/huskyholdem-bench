import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
from .data_models import ProcessingConfig
from .iterative_generator import IterativeGenerator

class AutomatedPromptProcessor:
    """Automated prompt processor with OpenAI Direct API routing"""
    
    OPENAI_DIRECT_MODELS = ["openai/gpt-5", "openai/o3-pro"]
    def __init__(self, TARGET_MODELS):
        from utils.docker_service import DockerService
        from llm.prompt_processor import OpenRouterPromptProcessor
        from llm.openai_client import OpenAIDirectProcessor
        
        self.docker_service = DockerService()
        self.TARGET_MODELS = TARGET_MODELS
        
        # Initialize both processors
        self.openrouter_processor = OpenRouterPromptProcessor(docker_service=self.docker_service)
        self.openai_processor = OpenAIDirectProcessor(docker_service=self.docker_service)


    
    def _get_processor_for_model(self, model_id: str):
        """Get the appropriate processor for a given model"""
        if model_id in self.OPENAI_DIRECT_MODELS:
            print(f"🤖 Using OpenAI Direct API for: {model_id}")
            return self.openai_processor
        else:
            print(f"🌐 Using OpenRouter for: {model_id}")
            return self.openrouter_processor
    
    def run(self) -> None:
        """Main automated processing entry point"""
        print("🤖 Automated OpenRouter + OpenAI Direct Prompt Processor")
        print("=" * 60)
        print(f"📋 Processing {len(self.TARGET_MODELS)} models with smart API routing")
        print(f"🌐 OpenRouter models: {len([m for m in self.TARGET_MODELS if m not in self.OPENAI_DIRECT_MODELS])}")
        print(f"🤖 OpenAI Direct models: {len(self.OPENAI_DIRECT_MODELS)}")
        print("=" * 60)
        
        try:
            # Get available models from both sources
            print("📡 Fetching available models from OpenRouter...")
            openrouter_models = self.openrouter_processor.get_available_models()
            
            print("📡 Getting OpenAI Direct API models...")
            openai_models = self.openai_processor.get_available_models()
            
            # Combine all available models
            all_available_models = openrouter_models + openai_models
            
            if not all_available_models:
                print("❌ No models available. Check your API keys and internet connection.")
                return
            
            # Filter to only target models that are available
            available_model_ids = {model.get("id", "") for model in all_available_models}
            selected_models = []
            
            for target_model in self.TARGET_MODELS:
                if target_model in available_model_ids:
                    for model in all_available_models:
                        if model.get("id") == target_model:
                            selected_models.append(model)
                            if target_model in self.OPENAI_DIRECT_MODELS:
                                print(f"✅ Found OpenAI Direct model: {target_model}")
                            else:
                                print(f"✅ Found OpenRouter model: {target_model}")
                            break
                elif target_model in self.OPENAI_DIRECT_MODELS:
                    # Create synthetic entry for OpenAI Direct models
                    synthetic_model = {
                        "id": target_model,
                        "provider": {"id": "openai"},
                        "context_length": 200000
                    }
                    selected_models.append(synthetic_model)
                    print(f"✅ Added OpenAI Direct model: {target_model}")
                else:
                    print(f"⚠️ Target model not available: {target_model}")
            
            if not selected_models:
                print("❌ None of the target models are available.")
                return
            
            print(f"\n🎯 Processing {len(selected_models)} available target models")
            
            # Read prompt
            print("\n📖 Reading prompt from generate.txt...")
            try:
                prompt = self.openrouter_processor.read_prompt_from_file("prompt/generate.txt")
                print(f"✅ Prompt loaded ({len(prompt)} characters)")
            except Exception as e:
                print(f"❌ Error reading prompt: {e}")
                return
            
            # Create processing configuration
            config = ProcessingConfig(
                temperature=1.0,
                max_tokens=30000,
                k_iterations=5,
                prompt_file="prompt/generate.txt"
            )
            
            # Process models in parallel
            print(f"\n🚀 Starting parallel processing of {len(selected_models)} models...")
            
            completed_models = []
            failed_models = []
            
            with ThreadPoolExecutor(max_workers=min(len(selected_models), 4)) as executor:
                futures = {}
                for model in selected_models:
                    future = executor.submit(self._process_model_safely, model, prompt, config)
                    futures[future] = model['id']
                
                for future in as_completed(futures):
                    model_id = futures[future]
                    try:
                        result = future.result()
                        if result:
                            print(f"✅ Completed processing for {model_id}")
                            completed_models.append(model_id)
                        else:
                            print(f"⚠️ Processing failed for {model_id}")
                            failed_models.append(model_id)
                    except Exception as e:
                        print(f"❌ Error in {model_id}: {e}")
                        failed_models.append(model_id)
            
            # Summary
            print(f"\n🎉 Multi-API processing complete!")
            print(f"✅ Successfully processed: {len(completed_models)}/{len(selected_models)} models")
            if failed_models:
                print(f"❌ Failed models: {', '.join(failed_models)}")
            print("📁 Check the 'bot/' directory for generated results")
            
        except KeyboardInterrupt:
            print("\n\n👋 Operation cancelled by user.")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    def _process_model_safely(self, selected_model: Dict[str, Any], prompt: str, config: ProcessingConfig) -> bool:
        """Process a single model with the appropriate processor"""
        # Create dedicated instances for thread safety
        from utils.docker_service import DockerService
        from llm.prompt_processor import OpenRouterPromptProcessor
        from llm.openai_client import OpenAIDirectProcessor
        
        docker_service = DockerService()
        model_id = selected_model['id']
        
        # Choose the right processor for this model
        if model_id in self.OPENAI_DIRECT_MODELS:
            processor = OpenAIDirectProcessor(docker_service=docker_service)
            print(f"\n🤖 Starting OpenAI Direct processing for: {model_id}")
        else:
            processor = OpenRouterPromptProcessor(docker_service=docker_service)
            print(f"\n🌐 Starting OpenRouter processing for: {model_id}")
        
        # Create iterative generator with the right processor
        iterative_generator = IterativeGenerator(processor)
        
        try:
            best_result, best_bot_dir = iterative_generator.run_iterations(
                selected_model, prompt, config
            )
            
            if best_result and best_bot_dir:
                print(f"✅ Successfully completed iterative generation for {model_id}")
                return True
            else:
                print(f"⚠️ No successful iterations for {model_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error in processing {model_id}: {e}")
            return False
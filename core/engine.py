import ollama
from config import DEFAULT_MODEL, MEMORY_LIMIT
from .memory import MemoryManager
from .personality import PersonalityManager
from .instructions import InstructionManager

class AIEngine:
    def __init__(self, default_model=DEFAULT_MODEL, skills=None):
        self.current_model = default_model
        self.memory = MemoryManager(default_model=default_model, limit=MEMORY_LIMIT)
        self.personality = PersonalityManager()
        self.instructions = InstructionManager()
        from core.skills import SkillManager
        self.skills = SkillManager(skills=skills)
        self.client = ollama.AsyncClient()
        self._model_cache = []
        self._last_cache_update = 0

    def get_cached_models(self):
        """Synchronous access to models for Discord autocomplete (must be fast)."""
        return self._model_cache

    async def list_models(self, force_refresh=False):
        """Retrieves and caches the list of models."""
        import time
        now = time.time()
        if not force_refresh and self._model_cache and (now - self._last_cache_update < 60):
            return self._model_cache
        try:
            response = await self.client.list()
            self._model_cache = [m.model for m in response.models]
            self._last_cache_update = now
            return self._model_cache
        except Exception as e:
            print(f"[AI Engine] Could not list models: {e}")
            return self._model_cache

    async def chat(self, channel_id, user_message, extra_context="", bot_identity=""):
        """Sends a chat request to Ollama with optional extra context and identity."""
        try:
            # Prepare System Prompt: Personality + Active Instructions
            active_instructions = self.instructions.get_active_content()
            
            # Core personality
            system_prompt = f"### YOUR CORE PERSONALITY:\n{self.personality.current_personality}"
            
            # Identity injection
            if bot_identity:
                system_prompt += f"\n\n### YOUR IDENTITY:\n{bot_identity}"

            # Global instructions
            if active_instructions:
                system_prompt += f"\n\n### MANDATORY INSTRUCTIONS TO FOLLOW:\n{active_instructions}"

            # Discord-specific context (members, channel info, etc.)
            if extra_context:
                system_prompt += f"\n\n{extra_context}"
            
            # Crucial meta-instruction for Discord interactions
            skills_prompt = self.skills.get_active_prompts()
            if skills_prompt:
                system_prompt += f"\n\n{skills_prompt}"

            # Retrieve memory and format context
            full_context = await self.memory.get_context(channel_id, system_prompt, user_message)
            
            response = await self.client.chat(model=self.current_model, messages=full_context)
            return response['message']['content']
        except Exception as e:
            print(f"[AI Engine] Error during Ollama call: {e}")
            return "An error occurred during the AI call."

    async def get_model_info(self):
        """Fetches detailed information about the current model from Ollama."""
        try:
            info = await self.client.show(model=self.current_model)
            # Use model_dump for newer pydantic-based Ollama library
            data = info.model_dump() if hasattr(info, 'model_dump') else info
            
            parameters = data.get('parameters', "") or ""
            modelfile = data.get('modelfile', "") or ""
            modelinfo = data.get('modelinfo', {}) or {}
            
            # Default to 2048 if not found (standard Ollama default)
            context_limit = 2048
            
            # 1. Check in modelinfo for architecture-specific context length (e.g., 'gemma3n.context_length')
            # Search for any key ending in '.context_length'
            for key, value in modelinfo.items():
                if key.endswith('.context_length') and isinstance(value, int):
                    context_limit = value
                    break
            else:
                # 2. Check in parameters
                import re
                match = re.search(r'num_ctx\s+(\d+)', str(parameters))
                if match:
                    context_limit = int(match.group(1))
                else:
                    # 3. Fallback to modelfile search: "PARAMETER num_ctx 4096"
                    match = re.search(r'PARAMETER\s+num_ctx\s+(\d+)', modelfile)
                    if match:
                        context_limit = int(match.group(1))
            
            return {
                "model": self.current_model,
                "context_limit": context_limit,
                "details": data.get('details', {})
            }
        except Exception as e:
            print(f"[AI Engine] Could not fetch model info: {e}")
            return {"model": self.current_model, "context_limit": 2048, "details": {}}

    def get_system_stats(self):
        """Calculates the current size of persistent memory components."""
        personality = self.personality.current_personality
        instructions = self.instructions.get_active_content()
        
        return {
            "personality_name": self.personality.current_name,
            "personality_chars": len(personality),
            "instructions_chars": len(instructions),
            "total_persistent_chars": len(personality) + len(instructions)
        }

    def change_model(self, new_model):
        self.current_model = new_model
        self.memory.default_model = new_model

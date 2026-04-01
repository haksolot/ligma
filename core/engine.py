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
        self.last_metrics = {}

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

    async def chat(self, channel_id, user_message, extra_context="", bot_identity="", interim_messages=None):
        """Sends a chat request to Ollama with optional extra context and interim thoughts."""
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

            # Discord-specific behavior instruction
            discord_behavior = (
                "\n\n### DISCORD CONTEXTUAL BEHAVIOR:\n"
                "- You are a participant in a Discord conversation. Respond naturally and concisely.\n"
                "- DO NOT speak for other users or imitate them in your response.\n"
                "- DO NOT start a dialogue with yourself. Provide only YOUR response.\n"
                "- ALWAYS accompany technical tags (like [SEARCH] or [READ]) with a brief natural sentence for the user (e.g., 'Let me look that up for you...').\n"
                "- Focus on the most recent context while keeping in mind the history provided above."
            )
            system_prompt += discord_behavior

            # Discord-specific context (members, channel info, etc.)
            if extra_context:
                system_prompt += f"\n\n{extra_context}"
            
            # Crucial meta-instruction for Discord interactions
            skills_prompt = self.skills.get_active_prompts()
            if skills_prompt:
                system_prompt += f"\n\n{skills_prompt}"

            # Retrieve memory and format context
            full_context = await self.memory.get_context(channel_id, system_prompt, user_message)
            
            # Inject interim messages (assistant thoughts/actions) before the final user message
            if interim_messages:
                # full_context[-1] is the current user_message
                full_context = full_context[:-1] + interim_messages + [full_context[-1]]

            # Logging for debugging (before call)
            self._log_conversation(channel_id, full_context, "REQUEST_SENT")

            response = await self.client.chat(model=self.current_model, messages=full_context)
            
            # Store metrics for performance tracking
            self.last_metrics = {
                "total_duration": response.get("total_duration"),
                "load_duration": response.get("load_duration"),
                "prompt_eval_count": response.get("prompt_eval_count"),
                "prompt_eval_duration": response.get("prompt_eval_duration"),
                "eval_count": response.get("eval_count"),
                "eval_duration": response.get("eval_duration"),
                "model": self.current_model
            }

            content = response['message']['content']
            self._log_conversation(channel_id, [{"role": "assistant", "content": content}], "RESPONSE_RECEIVED")
            
            return content
        except Exception as e:
            print(f"[AI Engine] Error during Ollama call: {e}")
            return "An error occurred during the AI call."

    def _log_conversation(self, channel_id, messages, tag):
        """Saves conversation context or response to a log file."""
        import os
        import json
        import time
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            filename = f"{log_dir}/chat_{channel_id}.log"
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            with open(filename, "a", encoding="utf-8") as f:
                f.write(f"\n--- {tag} | {timestamp} ---\n")
                f.write(json.dumps(messages, indent=2, ensure_ascii=False))
                f.write("\n")
        except Exception as e:
            print(f"[AI Engine] Logging error: {e}")

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

from config import (
    LLM_PROVIDER,
    DEFAULT_MODEL,
    MEMORY_LIMIT,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)
from .memory import MemoryManager
from .personality import PersonalityManager
from .instructions import InstructionManager
from .providers import OllamaProvider, OpenRouterProvider


class AIEngine:
    def __init__(self, default_model=DEFAULT_MODEL, skills=None):
        self.current_model = default_model
        self.memory = MemoryManager(default_model=default_model, limit=MEMORY_LIMIT)
        self.personality = PersonalityManager()
        self.instructions = InstructionManager()
        from core.skills import SkillManager

        self.skills = SkillManager(skills=skills)

        self._init_provider()

        self._model_cache = []
        self._last_cache_update = 0
        self.last_metrics = {}

    def _init_provider(self):
        if LLM_PROVIDER == "openrouter":
            if not OPENROUTER_API_KEY:
                print(
                    "[AI Engine] Warning: OPENROUTER_API_KEY not set, falling back to Ollama"
                )
                self.provider = OllamaProvider()
            else:
                self.provider = OpenRouterProvider(
                    api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL
                )
                print("[AI Engine] Using OpenRouter provider")
        else:
            self.provider = OllamaProvider()
            print("[AI Engine] Using Ollama provider")

        self.memory.set_provider(self.provider)

    def get_cached_models(self):
        return self._model_cache

    async def list_models(self, force_refresh=False):
        import time

        now = time.time()
        if (
            not force_refresh
            and self._model_cache
            and (now - self._last_cache_update < 60)
        ):
            return self._model_cache
        try:
            self._model_cache = await self.provider.list_models()
            self._last_cache_update = now
            return self._model_cache
        except Exception as e:
            print(f"[AI Engine] Could not list models: {e}")
            return self._model_cache

    async def chat(
        self,
        channel_id,
        user_message,
        extra_context="",
        bot_identity="",
        interim_messages=None,
        author_name=None,
    ):
        try:
            active_instructions = self.instructions.get_active_content()

            system_prompt = (
                f"### YOUR CORE PERSONALITY:\n{self.personality.current_personality}"
            )

            if bot_identity:
                system_prompt += f"\n\n### YOUR IDENTITY:\n{bot_identity}"

            if active_instructions:
                system_prompt += (
                    f"\n\n### MANDATORY INSTRUCTIONS TO FOLLOW:\n{active_instructions}"
                )

            discord_behavior = (
                "\n\n### DISCORD CONTEXTUAL BEHAVIOR:\n"
                "- You are a participant in a Discord conversation. Respond naturally and concisely.\n"
                "- DO NOT speak for other users or imitate them in your response.\n"
                "- DO NOT start a dialogue with yourself. Provide only YOUR response.\n"
                "- DO NOT include any ID prefix like '(ID: ...)' in your output. These are for your reference only.\n"
                "- ALWAYS accompany technical tags (like [SEARCH] or [READ]) with a brief natural sentence for the user (e.g., 'Let me look that up for you...').\n"
                "- SILENCE IS OK: If an event (like a reaction) or a message doesn't require a response, you MUST return exactly '[IGNORE]' and nothing else.\n"
                "- Focus on the most recent context while keeping in mind the history provided above."
            )
            system_prompt += discord_behavior

            if extra_context:
                system_prompt += f"\n\n{extra_context}"

            skills_prompt = self.skills.get_active_prompts()
            if skills_prompt:
                system_prompt += f"\n\n{skills_prompt}"

            full_context = await self.memory.get_context(
                channel_id, system_prompt, user_message, author_name=author_name
            )

            if interim_messages:
                full_context = full_context[:-1] + interim_messages + [full_context[-1]]

            self._log_conversation(channel_id, full_context, "REQUEST_SENT")

            response = await self.provider.chat(
                model=self.current_model, messages=full_context
            )

            self.last_metrics = {
                "total_duration": response.get("total_duration"),
                "load_duration": response.get("load_duration"),
                "prompt_eval_count": response.get("prompt_eval_count"),
                "prompt_eval_duration": response.get("prompt_eval_duration"),
                "eval_count": response.get("eval_count"),
                "eval_duration": response.get("eval_duration"),
                "model": self.current_model,
            }

            content = response["message"]["content"]
            self._log_conversation(
                channel_id,
                [{"role": "assistant", "content": content}],
                "RESPONSE_RECEIVED",
            )

            return content
        except Exception as e:
            print(f"[AI Engine] Error during LLM call: {e}")
            return "An error occurred during the AI call."

    def _log_conversation(self, channel_id, messages, tag):
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
        try:
            return await self.provider.get_model_info(self.current_model)
        except Exception as e:
            print(f"[AI Engine] Could not fetch model info: {e}")
            return {"model": self.current_model, "context_limit": 2048, "details": {}}

    def get_system_stats(self):
        personality = self.personality.current_personality
        instructions = self.instructions.get_active_content()

        return {
            "personality_name": self.personality.current_name,
            "personality_chars": len(personality),
            "instructions_chars": len(instructions),
            "total_persistent_chars": len(personality) + len(instructions),
        }

    def change_model(self, new_model):
        self.current_model = new_model
        self.memory.default_model = new_model

    def get_provider_name(self):
        return self.provider.get_provider_name()

    def switch_provider(self, provider_type: str, model: str = None):
        from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

        if provider_type == "openrouter":
            if not OPENROUTER_API_KEY:
                return False, "OPENROUTER_API_KEY not set"
            self.provider = OpenRouterProvider(
                api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL
            )
            print("[AI Engine] Switched to OpenRouter provider")
        else:
            self.provider = OllamaProvider()
            print("[AI Engine] Switched to Ollama provider")

        if model:
            self.current_model = model

        self.memory.set_provider(self.provider)
        return True, f"Switched to {provider_type}"

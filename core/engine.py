import ollama
from config import DEFAULT_MODEL, MEMORY_LIMIT
from .memory import MemoryManager
from .personality import PersonalityManager
from .instructions import InstructionManager

class AIEngine:
    def __init__(self, default_model=DEFAULT_MODEL):
        self.current_model = default_model
        self.memory = MemoryManager(default_model=default_model, limit=MEMORY_LIMIT)
        self.personality = PersonalityManager()
        self.instructions = InstructionManager()
        self.client = ollama.AsyncClient()

    async def list_models(self):
        """Retrieves the list of installed Ollama models."""
        try:
            response = await self.client.list()
            return [m.model for m in response.models]
        except Exception as e:
            print(f"[AI Engine] Could not list models: {e}")
            return []

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
            system_prompt += """
### DISCORD PROTOCOL (STRICT):
1. **PINGING**: Use <@USER_ID> syntax only.
2. **GIFS**: If you want to show a GIF, you MUST append `[GIF: keywords]` at the end of your message.
   - Example User: "Show me a cat."
   - Example Assistant: "Here is a cute cat! [GIF: cute cat]"
   - NEVER say "Here is a GIF" without adding the `[GIF: ...]` tag.
   - The tag MUST be in brackets: [GIF: your search query]
"""
            # Retrieve memory and format context
            full_context = await self.memory.get_context(channel_id, system_prompt, user_message)
            
            response = await self.client.chat(model=self.current_model, messages=full_context)
            return response['message']['content']
        except Exception as e:
            print(f"[AI Engine] Error during Ollama call: {e}")
            return "An error occurred during the AI call."

    def change_model(self, new_model):
        self.current_model = new_model
        self.memory.default_model = new_model

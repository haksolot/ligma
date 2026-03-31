import ollama
from .memory import MemoryManager
from .personality import PersonalityManager
from .instructions import InstructionManager

class AIEngine:
    def __init__(self, default_model="llama3.2:3b"):
        self.current_model = default_model
        self.memory = MemoryManager()
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

    async def chat(self, channel_id, user_message):
        """Sends a chat request to Ollama."""
        try:
            # Prepare System Prompt: Personality + Active Instructions
            active_instructions = self.instructions.get_active_content()
            
            # Formating a clear system prompt with explicit headers
            system_prompt = f"### YOUR CORE PERSONALITY:\n{self.personality.current_personality}"
            
            if active_instructions:
                system_prompt += f"\n\n### MANDATORY INSTRUCTIONS TO FOLLOW:\n{active_instructions}"

            # Retrieve memory and format context
            full_context = await self.memory.get_context(channel_id, system_prompt, user_message)
            
            response = await self.client.chat(model=self.current_model, messages=full_context)
            return response['message']['content']
        except Exception as e:
            print(f"[AI Engine] Error during Ollama call: {e}")
            return "An error occurred during the AI call."

    def change_model(self, new_model):
        self.current_model = new_model

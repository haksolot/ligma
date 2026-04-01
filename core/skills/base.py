import discord
from typing import Optional, Tuple, Dict, Any

class BaseSkill:
    name: str = "Base"
    description: str = "Base skill description"
    is_active: bool = True

    def get_prompt_injection(self) -> str:
        """Returns the specific instructions for this skill to be appended to the system prompt."""
        return ""

    async def execute_reflection(self, response: str, message: discord.Message) -> Optional[str]:
        """
        Parses the AI response for specific tags.
        If a tag is found, executes the reflection action and returns a string context.
        If no tag is found, returns None.
        """
        return None

    async def execute_action(self, response: str, message: discord.Message) -> Tuple[str, Dict[str, Any]]:
        """
        Parses the AI final response for tags.
        Executes the action or returns parameters for the main loop to execute.
        Returns a tuple: (cleaned_response, context_dict)
        """
        return response, {}

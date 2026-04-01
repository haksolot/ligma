import discord
import re
from typing import Optional, Tuple, Dict, Any
from .base import BaseSkill

class GifSkill(BaseSkill):
    name = "Gifs"
    description = "Allows the AI to attach GIFs from Giphy."
    is_active = True

    def get_prompt_injection(self) -> str:
        return "**GIFS**: To show a GIF, append `[GIF: keywords]` at the end."

    async def execute_action(self, response: str, message: discord.Message) -> Tuple[str, Dict[str, Any]]:
        gif_query = None
        gif_match = re.search(r'\[GIF: (.*?)\]', response)
        if gif_match:
            gif_query = gif_match.group(1)
        
        cleaned_response = re.sub(r'\[GIF: (.*?)\]', '', response)
        return cleaned_response, {'gif_query': gif_query}

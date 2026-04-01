import re
from typing import Optional, Tuple, Dict, Any
from .base import BaseSkill

class GifSkill(BaseSkill):
    name = "Gifs"
    description = "Allows the AI to attach GIFs from Giphy."
    is_active = True

    def get_prompt_injection(self) -> str:
        return "**GIFS**: To show a GIF, append `[GIF: keywords]` at the end."

    async def execute_action(self, response: str, message: Any) -> Tuple[str, Dict[str, Any]]:
        gif_query = None
        # Robust detection for GIFF, Giphy, etc. and case-insensitivity
        gif_match = re.search(r'\[GI+F:?\s*(.*?)\]', response, re.IGNORECASE)
        if gif_match:
            gif_query = gif_match.group(1).strip()
        
        cleaned_response = re.sub(r'\[GI+F:?.*?\]', '', response, flags=re.IGNORECASE)
        return cleaned_response.strip(), {'gif_query': gif_query}

import discord
import re
from typing import Optional, Tuple, Dict, Any
from core.skills.base import BaseSkill
from platforms.discord.context import DiscordContextFetcher

class HistorySkill(BaseSkill):
    name = "History"
    description = "Allows the AI to fetch recent messages when missing context."
    is_active = True

    def get_prompt_injection(self) -> str:
        return "**HISTORY**: If you lack context, include `[HISTORY: count]` (max 25).\n   - You will then see message IDs in the history and can use them in REACT/REPLY tags.\n   - USE THIS SPARINGLY."

    async def execute_reflection(self, response: str, message: discord.Message) -> Optional[str]:
        history_match = re.search(r'\[HISTORY: (\d+)\]', response)
        if history_match:
            limit = int(history_match.group(1))
            if limit <= 0:
                return "### SYSTEM: History request ignored because limit was 0 or invalid. Use a positive number up to 25."
            
            limit = min(limit, 25)
            history_text = await DiscordContextFetcher.get_recent_history(message.channel, limit, exclude_id=message.id)
            history_prompt = f"\n\n### CHANNEL HISTORY DATA (Excluded current message):\n{history_text}\n\n"
            history_prompt += "### MANDATORY INSTRUCTIONS:\n1. Use the IDs provided above to perform targeted REACT or REPLY actions.\n2. DO NOT include another [HISTORY: ...] tag for this query. The history is FETCHED."
            
            # We must NOT return the original tag in the next prompt, or it might loop
            return history_prompt
        return None

    async def execute_action(self, response: str, message: discord.Message) -> Tuple[str, Dict[str, Any]]:
        # Robustly remove any version of the tag
        cleaned_response = re.sub(r'\[HIST?OR[Y|I]E?:? \d+\]', '', response, flags=re.IGNORECASE)
        return cleaned_response.strip(), {}

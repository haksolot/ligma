import discord
import re
from typing import Optional, Tuple, Dict, Any
from core.skills.base import BaseSkill

class ReplySkill(BaseSkill):
    name = "Replies"
    description = "Allows the AI to reply directly to specific messages."
    is_active = True

    def get_prompt_injection(self) -> str:
        return "**REPLIES**: To reply to a specific message, include `[REPLY: target_id]`.\n   - Use the ID found in the history."

    async def execute_action(self, response: str, message: discord.Message) -> Tuple[str, Dict[str, Any]]:
        target_reply_msg = None
        reply_match = re.search(r'\[REPLY:? ?(\d+)?\]', response)
        if reply_match:
            # Default to the message that triggered the bot
            target_reply_msg = message
            
            # If a specific ID is provided, try to find it
            target_id_str = reply_match.group(1)
            if target_id_str:
                try:
                    target_id = int(target_id_str)
                    if target_id != message.id:
                        # Attempt to fetch, but fallback if it fails
                        try:
                            target_reply_msg = await message.channel.fetch_message(target_id)
                        except discord.NotFound:
                            print(f"[ReplySkill] Target ID {target_id} not found. Falling back to current message.")
                            target_reply_msg = message
                except ValueError:
                    pass
        
        cleaned_response = re.sub(r'\[REPLY:? ?(\d+)?\]', '', response)
        return cleaned_response, {'target_reply_msg': target_reply_msg}

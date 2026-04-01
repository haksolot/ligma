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
        # Robustly detect REPLY tags (including REPLYY, reply, etc.)
        reply_match = re.search(r'\[RE*PL*Y:?\s*(\d+)?\]', response, re.IGNORECASE)
        if reply_match:
            target_reply_msg = message
            target_id_str = reply_match.group(1)
            if target_id_str:
                try:
                    target_id = int(target_id_str)
                    if target_id != message.id:
                        try:
                            target_reply_msg = await message.channel.fetch_message(target_id)
                        except discord.NotFound:
                            print(f"[ReplySkill] Target ID {target_id} not found. Falling back to current message.")
                            target_reply_msg = message
                except ValueError:
                    pass
        
        cleaned_response = re.sub(r'\[RE*PL*Y:?.*?\]', '', response, flags=re.IGNORECASE)
        return cleaned_response.strip(), {'target_reply_msg': target_reply_msg}

import discord
import re
from typing import Optional, Tuple, Dict, Any
from core.skills.base import BaseSkill

class ReactionSkill(BaseSkill):
    name = "Reactions"
    description = "Allows the AI to react to messages with emojis."
    is_active = True

    def get_prompt_injection(self) -> str:
        return "**REACTIONS**: To react to a message with an emoji, append `[REACT: emoji_char, target_id]`.\n   - You MUST find the `target_id` in the history provided (format: `(ID: 123456789) Name: content`).\n   - If you want to react to someone else, use THEIR message ID.\n   - Example: \"I like that! [REACT: 👍, 123456789]\""

    async def execute_action(self, response: str, message: discord.Message) -> Tuple[str, Dict[str, Any]]:
        react_matches = re.findall(r'\[REACT: (.*?)\]', response)
        for react_content in react_matches:
            parts = [p.strip() for p in react_content.split(',')]
            emoji = parts[0]
            target_msg = message
            
            if len(parts) > 1:
                try:
                    raw_id = re.sub(r'[^0-9]', '', parts[1])
                    if raw_id:
                        target_id = int(raw_id)
                        if target_id == message.id:
                            target_msg = message
                        else:
                            target_msg = await message.channel.fetch_message(target_id)
                except Exception as e:
                    print(f"[ReactionSkill] Failed to fetch target message {parts[1]}: {e}")
                    continue
            
            try:
                await target_msg.add_reaction(emoji)
            except Exception as e:
                print(f"[ReactionSkill] Failed to react with {emoji}: {e}")

        cleaned_response = re.sub(r'\[REACT: (.*?)\]', '', response)
        return cleaned_response, {}

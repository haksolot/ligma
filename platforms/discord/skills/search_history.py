import re
from typing import Optional, Tuple, Dict, Any
import discord
from core.skills.base import BaseSkill


class SearchHistorySkill(BaseSkill):
    name = "SearchHistory"
    description = "Allows the AI to search past messages in the Discord channel by keyword."
    is_active = True

    def get_prompt_injection(self) -> str:
        return (
            "**DISCORD_SEARCH**: To search for past messages in this channel, use `[DISCORD_SEARCH: query]`. "
            "You will receive matching messages with timestamps, authors, and IDs. "
            "Use this when asked about past conversations or specific topics discussed earlier."
        )

    async def execute_reflection(self, response: str, message) -> Optional[str]:
        if not message:
            return None
        match = re.search(r'\[DISCORD_SEARCH:\s*(.*?)\]', response, re.IGNORECASE)
        if not match:
            return None

        query = match.group(1).strip()
        if not query:
            return "### SYSTEM: DISCORD_SEARCH query was empty."

        query_lower = query.lower()
        results = []
        try:
            async for msg in message.channel.history(limit=100):
                if msg.id == message.id:
                    continue
                if query_lower in msg.clean_content.lower():
                    ts = msg.created_at.strftime("%Y-%m-%d %H:%M")
                    results.append(
                        f"[{ts}] (ID: {msg.id}) {msg.author.display_name}: {msg.clean_content[:200]}"
                    )
                    if len(results) >= 15:
                        break
        except Exception as e:
            return f"### SYSTEM: Could not search history: {e}"

        if not results:
            return (
                f"### DISCORD_SEARCH RESULTS for '{query}':\n"
                f"No messages matched your query in the last 100 messages."
            )

        result_text = "\n".join(reversed(results))
        injection = (
            f"\n\n### DISCORD_SEARCH RESULTS for '{query}' ({len(results)} found):\n"
            f"{result_text}\n\n"
            f"### MANDATORY INSTRUCTIONS:\n"
            f"1. Use these results to answer the user's question.\n"
            f"2. DO NOT include another [DISCORD_SEARCH:] tag for this query. Search is COMPLETE."
        )
        return injection

    async def execute_action(self, response: str, message: Any) -> Tuple[str, Dict[str, Any]]:
        cleaned = re.sub(r'\[DISCORD_SEARCH:.*?\]', '', response, flags=re.IGNORECASE)
        return cleaned.strip(), {}

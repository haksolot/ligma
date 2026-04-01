import discord
import re
import time
from difflib import SequenceMatcher
from discord.ext import commands
from platforms.discord.context import DiscordContextFetcher
from core.utils.gifs import GiphyFetcher

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Format: {channel_id: {"user_id": int, "timestamp": float}}
        self.last_interactions = {}

    def _process_mentions(self, content, channel):
        """Replaces @Name or @DisplayName with <@ID> if they match a member in the channel."""
        if not hasattr(channel, "members") or "@" not in content:
            return content

        # Find all potential mentions in the content: @ followed by non-whitespace
        # We handle multi-word names by trying to match longer strings first
        # But for simplicity and performance, we'll use a mapping of known names
        
        # Build a mapping of name -> ID for all members in this channel
        # We only do this once per call
        name_to_id = {}
        for m in channel.members:
            name_to_id[m.display_name.lower()] = m.id
            name_to_id[m.name.lower()] = m.id
            
        # Sort names by length (longest first) to avoid partial matches
        sorted_names = sorted(name_to_id.keys(), key=len, reverse=True)
        
        processed_content = content
        
        # Build a single regex for all names in the channel that start with @
        # We escape names and join them with |
        if not sorted_names:
            return content
            
        # We only care about names that are actually preceded by @ in the content
        # To be even faster, we filter sorted_names to only those found in content (case-insensitive)
        content_lower = content.lower()
        relevant_names = [n for n in sorted_names if f"@{n}" in content_lower]
        
        if not relevant_names:
            return content

        pattern = re.compile(
            "|".join(rf"@{re.escape(name)}(?!\w)" for name in relevant_names),
            re.IGNORECASE
        )
        
        def sub_func(match):
            matched_text = match.group(0).lower().lstrip('@')
            user_id = name_to_id.get(matched_text)
            if user_id:
                return f"<@{user_id}>"
            return match.group(0)

        return pattern.sub(sub_func, processed_content)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        channel_id_str = str(message.channel.id)
        now = time.time()

        # --- DETECTION LOGIC ---
        bot_name = self.bot.user.name.lower()
        bot_display = self.bot.user.display_name.lower()
        bot_id = self.bot.user.id
        
        content_lower = message.content.lower()
        
        # 1. Direct Mention
        is_mentioned = self.bot.user.mentioned_in(message)
        
        # 2. Name cited (Substring + Fuzzy)
        is_named = False
        if bot_name in content_lower or bot_display in content_lower:
            is_named = True
        
        # Optimization: Only do fuzzy search if the message is short or 
        # if we haven't found the name yet and it's a potential call.
        if not is_named and len(content_lower) < 100:
            words = re.findall(r'\b\w+\b', content_lower)
            for word in words:
                if len(word) < 3: continue 
                # Quick check before SequenceMatcher
                if word[0] not in (bot_name[0], bot_display[0]): continue
                
                name_sim = SequenceMatcher(None, word, bot_name).ratio()
                display_sim = SequenceMatcher(None, word, bot_display).ratio()
                
                if name_sim > 0.85 or display_sim > 0.85:
                    is_named = True
                    break
        
        # 3. Discord Reply to the bot
        is_reply = False
        if message.reference and message.reference.message_id:
            # Optimization: check resolved message if available to avoid API call
            if message.reference.resolved and isinstance(message.reference.resolved, discord.Message):
                if message.reference.resolved.author.id == bot_id:
                    is_reply = True
            else:
                try:
                    # Fallback to fetch (rare)
                    replied_to = await message.channel.fetch_message(message.reference.message_id)
                    if replied_to.author.id == bot_id:
                        is_reply = True
                except: pass

        # 4. Sticky Conversation (Follow-up)
        is_followup = False
        last_interaction = self.last_interactions.get(channel_id_str)
        if last_interaction:
            if (last_interaction["user_id"] == message.author.id and 
                now - last_interaction["timestamp"] < 45):
                is_followup = True

        # --- DECISION ---
        if is_mentioned or is_named or is_reply or is_followup:
            async with message.channel.typing():
                try:
                    # Clean the content for the AI
                    clean_content = message.content.replace(f'<@!{bot_id}>', '').replace(f'<@{bot_id}>', '').strip()
                    
                    if not clean_content and (is_mentioned or is_reply):
                        await message.channel.send("Did you call me?")
                        return
                    elif not clean_content:
                        return

                    # Update memory
                    await self.bot.ai.memory.add_message(channel_id_str, "user", clean_content)

                    # Get Discord Context
                    members_list = await DiscordContextFetcher.get_channel_members(message.channel)
                    discord_context = f"\n\n### DISCORD ENVIRONMENT\nChannel: #{message.channel.name}\nCurrent Members in this channel:\n{members_list}\n\n"
                    discord_context += f"You are talking to: {message.author.display_name} (ID: {message.author.id})"

                    # Build Identity
                    identity = f"You are currently logged into Discord as: {bot_display} (Username: {bot_name}). "
                    identity += f"Your Discord ID is {bot_id}. You are in a conversation with {message.author.display_name}."

                    # Call AI
                    response = await self.bot.ai.chat(channel_id_str, clean_content, extra_context=discord_context, bot_identity=identity)

                    # Save response
                    await self.bot.ai.memory.add_message(channel_id_str, "assistant", response)

                    # Update sticky interaction state
                    self.last_interactions[channel_id_str] = {
                        "user_id": message.author.id,
                        "timestamp": time.time()
                    }

                    # Extract GIF
                    gif_query = None
                    gif_match = re.search(r'\[GIF: (.*?)\]', response)
                    if gif_match:
                        gif_query = gif_match.group(1)
                        response = response.replace(gif_match.group(0), "").strip()

                    # Mentions processing (Optimized)
                    response = self._process_mentions(response, message.channel)

                    # Send message
                    if response:
                        if len(response) > 2000:
                            for i in range(0, len(response), 2000):
                                await message.channel.send(response[i:i+2000])
                        else:
                            await message.channel.send(response)

                    # Send GIF
                    if gif_query:
                        gif_url = await GiphyFetcher.get_gif_url(gif_query)
                        if gif_url:
                            await message.channel.send(gif_url)

                except Exception as e:
                    print(f"[ChatCog] Error: {e}")
                    # Only one exception handler needed
                    try:
                        await message.channel.send(f"Oops, system error: {e}")
                    except: pass

async def setup(bot):
    await bot.add_cog(ChatCog(bot))

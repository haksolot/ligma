import discord
import re
from discord.ext import commands
from platforms.discord.context import DiscordContextFetcher
from core.utils.gifs import GiphyFetcher

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Format: {channel_id: {"user_id": int, "timestamp": float, "message_id": int}}
        self.last_interactions = {}

    def _process_mentions(self, content, channel):
        # ... (logic remains same, shortened for replace context)
        processed_content = content
        if not hasattr(channel, "members"): return processed_content
        members = sorted(channel.members, key=lambda m: len(m.display_name), reverse=True)
        for member in members:
            escaped_display = re.escape(member.display_name)
            escaped_name = re.escape(member.name)
            pattern_display = re.compile(rf'@{escaped_display}(?!\w)', re.IGNORECASE)
            processed_content = pattern_display.sub(f'<@{member.id}>', processed_content)
            if member.name.lower() != member.display_name.lower():
                pattern_name = re.compile(rf'@{escaped_name}(?!\w)', re.IGNORECASE)
                processed_content = pattern_name.sub(f'<@{member.id}>', processed_content)
        return processed_content

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        import time
        channel_id_str = str(message.channel.id)
        now = time.time()

        # --- DETECTION LOGIC ---
        bot_name = self.bot.user.name
        bot_display = self.bot.user.display_name
        bot_id = self.bot.user.id
        
        # 1. Direct Mention
        is_mentioned = self.bot.user.mentioned_in(message)
        
        # 2. Name cited in text
        is_named = re.search(rf'\b({re.escape(bot_name)}|{re.escape(bot_display)})\b', message.content, re.IGNORECASE)
        
        # 3. Discord Reply to the bot
        is_reply = False
        if message.reference and message.reference.message_id:
            try:
                # We check if the replied message was from our bot
                replied_to = await message.channel.fetch_message(message.reference.message_id)
                if replied_to.author.id == bot_id:
                    is_reply = True
            except: pass

        # 4. Sticky Conversation (Follow-up)
        is_followup = False
        last_interaction = self.last_interactions.get(channel_id_str)
        if last_interaction:
            # If same user, within 45 seconds, and no one else spoke (roughly)
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

                    # Mentions processing
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

                except Exception as e:
                    await message.channel.send(f"Oops, system error: {e}")

async def setup(bot):
    await bot.add_cog(ChatCog(bot))

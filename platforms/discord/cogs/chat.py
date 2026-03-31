import discord
import re
from discord.ext import commands
from platforms.discord.context import DiscordContextFetcher

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _process_mentions(self, content, channel):
        """Replaces @username or @Display Name with <@ID> if the user exists in the channel."""
        processed_content = content
        
        # In a guild, we have access to all members if intents are correct
        if not hasattr(channel, "members"):
            return processed_content

        # Sort members by display name length descending to avoid partial matches
        members = sorted(channel.members, key=lambda m: len(m.display_name), reverse=True)
        
        for member in members:
            # Escape to handle special characters in names
            escaped_display = re.escape(member.display_name)
            escaped_name = re.escape(member.name)
            
            # Pattern for @Display Name (handles names with spaces)
            # We look for @ followed by the exact name, ensuring it's not preceded/followed by letters
            # unless it's the start/end of the name itself.
            pattern_display = re.compile(rf'@{escaped_display}(?!\w)', re.IGNORECASE)
            processed_content = pattern_display.sub(f'<@{member.id}>', processed_content)
            
            # Pattern for @Username
            if member.name.lower() != member.display_name.lower():
                pattern_name = re.compile(rf'@{escaped_name}(?!\w)', re.IGNORECASE)
                processed_content = pattern_name.sub(f'<@{member.id}>', processed_content)
        
        return processed_content

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Only respond if mentioned
        if self.bot.user.mentioned_in(message):
            async with message.channel.typing():
                try:
                    clean_content = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()
                    
                    if not clean_content:
                        await message.channel.send("Did you call me?")
                        return

                    channel_id = str(message.channel.id)

                    # 1. Update memory
                    await self.bot.ai.memory.add_message(channel_id, "user", clean_content)

                    # 2. Get Discord Context (Members, etc.)
                    members_list = await DiscordContextFetcher.get_channel_members(message.channel)
                    discord_context = f"\n\n### DISCORD ENVIRONMENT\nChannel: #{message.channel.name}\nCurrent Members in this channel:\n{members_list}\n\n"
                    discord_context += f"You are talking to: {message.author.display_name} (ID: {message.author.id})"

                    # 3. Call AI with injected context
                    response = await self.bot.ai.chat(channel_id, clean_content, extra_context=discord_context)

                    # 4. Save response
                    await self.bot.ai.memory.add_message(channel_id, "assistant", response)

                    # 5. Post-process mentions in response
                    response = self._process_mentions(response, message.channel)

                    # 6. Split and send if too long
                    if len(response) > 2000:
                        for i in range(0, len(response), 2000):
                            await message.channel.send(response[i:i+2000])
                    else:
                        await message.channel.send(response)

                except Exception as e:
                    await message.channel.send(f"Oops, system error: {e}")

async def setup(bot):
    await bot.add_cog(ChatCog(bot))

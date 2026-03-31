import discord
from discord.ext import commands

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

                    # 2. Prepare Ollama context
                    # (Handled inside AIEngine)
                    
                    # 3. Call AI
                    response = await self.bot.ai.chat(channel_id, clean_content)

                    # 4. Save response
                    await self.bot.ai.memory.add_message(channel_id, "assistant", response)

                    # 5. Split and send if too long
                    if len(response) > 2000:
                        for i in range(0, len(response), 2000):
                            await message.channel.send(response[i:i+2000])
                    else:
                        await message.channel.send(response)

                except Exception as e:
                    await message.channel.send(f"Oops, system error: {e}")

async def setup(bot):
    await bot.add_cog(ChatCog(bot))

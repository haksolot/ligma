import discord
from discord.ext import commands
from core.engine import AIEngine
from config import DISCORD_TOKEN

class LigmaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.ai = AIEngine()

    async def setup_hook(self):
        # Load cogs
        await self.load_extension("platforms.discord.cogs.chat")
        await self.load_extension("platforms.discord.cogs.ai")
        
        # Sync slash commands
        await self.tree.sync()

    async def on_ready(self):
        # Load Ollama models on startup
        models = await self.ai.list_models()
        
        print(f"Logged in as {self.user}!")
        print(f"Ollama models loaded: {', '.join(models)}")
        print(f"Active model: {self.ai.current_model}")
        print("L.I.G.M.A. is ready!")

def run_bot():
    bot = LigmaBot()
    bot.run(DISCORD_TOKEN)

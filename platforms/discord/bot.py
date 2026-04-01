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
        
        # Inject Discord-specific skills
        from core.skills import GifSkill
        from platforms.discord.skills.history import HistorySkill
        from platforms.discord.skills.reactions import ReactionSkill
        from platforms.discord.skills.replies import ReplySkill
        
        discord_skills = [
            GifSkill(),
            HistorySkill(),
            ReactionSkill(),
            ReplySkill()
        ]
        
        self.ai = AIEngine(skills=discord_skills)

    async def update_presence(self):
        """Updates the bot's status with current model and personality."""
        model = self.ai.current_model
        personality = self.ai.personality.current_name
        status_text = f"{model} | {personality}"
        await self.change_presence(activity=discord.Game(name=status_text))

    async def setup_hook(self):
        # Load cogs
        await self.load_extension("platforms.discord.cogs.chat")
        await self.load_extension("platforms.discord.cogs.ai")
        
        # Global error handler for the command tree
        @self.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
            if isinstance(error, discord.app_commands.errors.CommandInvokeError):
                real_error = error.original
                if isinstance(real_error, discord.NotFound) and real_error.code == 10062:
                    # Silence the "Unknown interaction" timeout error
                    return
            
            print(f"[Bot] Tree Error: {error}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"System error: {error}", ephemeral=True)
                else:
                    await interaction.followup.send(f"System error: {error}", ephemeral=True)
            except: pass

        # Sync slash commands
        await self.tree.sync()

    async def on_ready(self):
        # Load Ollama models on startup
        models = await self.ai.list_models()
        
        # Update status
        await self.update_presence()
        
        print(f"Logged in as {self.user}!")
        print(f"Ollama models loaded: {', '.join(models)}")
        print(f"Active model: {self.ai.current_model}")
        print("L.I.G.M.A. is ready!")

def run_bot():
    bot = LigmaBot()
    bot.run(DISCORD_TOKEN)

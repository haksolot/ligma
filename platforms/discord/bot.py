import discord
import asyncio
from discord.ext import commands, tasks
from core.engine import AIEngine
from config import DISCORD_TOKEN

class LigmaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        
        # Inject Discord-specific skills
        from core.skills import GifSkill, SearchSkill
        from platforms.discord.skills.history import HistorySkill
        from platforms.discord.skills.reactions import ReactionSkill
        from platforms.discord.skills.replies import ReplySkill
        
        discord_skills = [
            GifSkill(),
            SearchSkill(),
            HistorySkill(),
            ReactionSkill(),
            ReplySkill()
        ]
        
        self.ai = AIEngine(skills=discord_skills)

    async def update_presence(self):
        """Updates the bot's status with current model and personality."""
        try:
            model = self.ai.current_model
            personality = self.ai.personality.current_name
            status_text = f"{model} | {personality}"
            await self.change_presence(activity=discord.Game(name=status_text))
        except: pass

    @tasks.loop(minutes=5)
    async def refresh_model_cache_task(self):
        """Periodically refreshes the Ollama model list in the background."""
        await self.ai.list_models(force_refresh=True)

    async def setup_hook(self):
        # 1. Start background tasks
        self.refresh_model_cache_task.start()

        # 2. Pre-load critical data before syncing commands
        print("[Bot] Pre-loading models cache...")
        await self.ai.list_models()

        # 3. Load cogs
        await self.load_extension("platforms.discord.cogs.chat")
        await self.load_extension("platforms.discord.cogs.ai")
        
        # 4. Global error handler for the command tree
        @self.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
            # Handle interaction timeouts (404/10062) gracefully
            if isinstance(error, discord.app_commands.errors.CommandInvokeError):
                real_error = error.original
                if isinstance(real_error, discord.NotFound) and real_error.code == 10062:
                    return
            
            error_str = str(error)
            if "10062" in error_str or "Unknown interaction" in error_str:
                return

            print(f"[Bot] Tree Error: {error}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"System error: {error}", ephemeral=True)
                else:
                    await interaction.followup.send(f"System error: {error}", ephemeral=True)
            except: pass

        # 5. Sync slash commands
        await self.tree.sync()

    async def on_ready(self):
        # Final status update
        await self.update_presence()
        
        print(f"Logged in as {self.user}!")
        print(f"Ollama models loaded: {', '.join(self.ai.get_cached_models())}")
        print(f"Active model: {self.ai.current_model}")
        print("L.I.G.M.A. is ready!")

def run_bot():
    bot = LigmaBot()
    bot.run(DISCORD_TOKEN)

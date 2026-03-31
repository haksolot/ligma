import discord
from discord import app_commands
from discord.ext import commands
from config import CREATOR_ID

class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_creator(self, interaction: discord.Interaction) -> bool:
        """Check if the user is the authorized creator."""
        return interaction.user.id == CREATOR_ID

    # --- AUTOCOMPLETION ---
    async def model_autocomplete(self, interaction: discord.Interaction, current: str):
        if not self.is_creator(interaction):
            return []
        try:
            models = await self.bot.ai.list_models()
            return [
                app_commands.Choice(name=m, value=m)
                for m in models if current.lower() in m.lower()
            ][:25]
        except:
            return []

    async def personality_autocomplete(self, interaction: discord.Interaction, current: str):
        if not self.is_creator(interaction):
            return []
        try:
            personalities = self.bot.ai.personality.list_all()
            return [
                app_commands.Choice(name=p, value=p)
                for p in personalities if current.lower() in p.lower()
            ][:25]
        except:
            return []

    async def instruction_autocomplete(self, interaction: discord.Interaction, current: str):
        if not self.is_creator(interaction):
            return []
        try:
            instructions = self.bot.ai.instructions.list_all()
            return [
                app_commands.Choice(name=name, value=name)
                for name, active in instructions if current.lower() in name.lower()
            ][:25]
        except:
            return []

    @app_commands.command(name="model", description="Change the Ollama model used (Creator Only).")
    @app_commands.autocomplete(model_name=model_autocomplete)
    async def change_model(self, interaction: discord.Interaction, model_name: str):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
            
        try:
            self.bot.ai.change_model(model_name)
            self.bot.ai.memory.clear(str(interaction.channel_id))
            await interaction.response.send_message(f"**Brain replaced!** I am now using `{model_name}`.\n*(Memory reset).*", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error changing model: {e}", ephemeral=True)

    @app_commands.command(name="reset", description="Clear the memory of this channel (Creator Only).")
    async def reset_memory(self, interaction: discord.Interaction):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
            
        try:
            self.bot.ai.memory.clear(str(interaction.channel_id))
            await interaction.response.send_message("**Memory formatted!** Starting from scratch here.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error resetting memory: {e}", ephemeral=True)

    # --- PERSONALITY GROUP ---
    personality_group = app_commands.Group(name="personality", description="Manage bot personality.")

    @personality_group.command(name="view", description="Show current personality (Creator Only).")
    async def view_personality(self, interaction: discord.Interaction):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        try:
            name = self.bot.ai.personality.current_name
            content = self.bot.ai.personality.current_personality
            await interaction.response.send_message(f"Current personality: **{name}**\n>>> {content}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error viewing personality: {e}", ephemeral=True)

    @personality_group.command(name="select", description="Switch personality from library (Creator Only).")
    @app_commands.autocomplete(name=personality_autocomplete)
    async def select_personality(self, interaction: discord.Interaction, name: str):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        try:
            self.bot.ai.personality.load(name)
            self.bot.ai.memory.clear(str(interaction.channel_id))
            await interaction.response.send_message(f"Switched to personality: **{name}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to load personality: {e}", ephemeral=True)

    @personality_group.command(name="create", description="Save current or create new personality (Creator Only).")
    async def create_personality(self, interaction: discord.Interaction, name: str, content: str):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        try:
            self.bot.ai.personality.save(name, content)
            await interaction.response.send_message(f"Personality **{name}** saved/updated!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error saving personality: {e}", ephemeral=True)

    @personality_group.command(name="delete", description="Delete personality from library (Creator Only).")
    @app_commands.autocomplete(name=personality_autocomplete)
    async def delete_personality(self, interaction: discord.Interaction, name: str):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        try:
            if self.bot.ai.personality.delete(name):
                await interaction.response.send_message(f"Personality **{name}** deleted.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Could not delete **{name}** (it might not exist or is protected).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error deleting personality: {e}", ephemeral=True)

    # --- INSTRUCTION GROUP ---
    instruction_group = app_commands.Group(name="instructions", description="Manage global instructions.")

    @instruction_group.command(name="list", description="List all instructions and their status (Creator Only).")
    async def list_instructions(self, interaction: discord.Interaction):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        try:
            instructions = self.bot.ai.instructions.list_all()
            if not instructions:
                await interaction.response.send_message("No instructions found.", ephemeral=True)
                return
                
            lines = []
            for name, active in instructions:
                status = "✅ Active" if active else "❌ Inactive"
                lines.append(f"- **{name}**: {status}")
            
            await interaction.response.send_message("### Global Instructions:\n" + "\n".join(lines), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error listing instructions: {e}", ephemeral=True)

    @instruction_group.command(name="create", description="Create or update an instruction (Creator Only).")
    async def create_instruction(self, interaction: discord.Interaction, name: str, content: str):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        try:
            self.bot.ai.instructions.create_or_update(name, content)
            await interaction.response.send_message(f"Instruction **{name}** saved/updated.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error saving instruction: {e}", ephemeral=True)

    @instruction_group.command(name="toggle", description="Activate or deactivate an instruction (Creator Only).")
    @app_commands.autocomplete(name=instruction_autocomplete)
    async def toggle_instruction(self, interaction: discord.Interaction, name: str, active: bool):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        try:
            if self.bot.ai.instructions.toggle(name, active):
                status = "activated" if active else "deactivated"
                await interaction.response.send_message(f"Instruction **{name}** {status}.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Instruction **{name}** not found.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error toggling instruction: {e}", ephemeral=True)

    @instruction_group.command(name="delete", description="Delete an instruction (Creator Only).")
    @app_commands.autocomplete(name=instruction_autocomplete)
    async def delete_instruction(self, interaction: discord.Interaction, name: str):
        if not self.is_creator(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        try:
            if self.bot.ai.instructions.delete(name):
                await interaction.response.send_message(f"Instruction **{name}** deleted.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Instruction **{name}** not found.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error deleting instruction: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AICog(bot))

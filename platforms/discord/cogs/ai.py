import discord
from discord import app_commands, ui
from discord.ext import commands
from config import CREATOR_ID

# --- MODALS ---

class CreateModal(ui.Modal):
    def __init__(self, title, callback_func, is_instruction=False):
        super().__init__(title=title)
        self.callback_func = callback_func
        
        self.name_input = ui.TextInput(
            label="Name",
            placeholder="Enter a unique name...",
            min_length=2,
            max_length=50
        )
        self.content_input = ui.TextInput(
            label="Content / Prompt",
            style=discord.TextStyle.paragraph,
            placeholder="Enter the detailed content here...",
            min_length=5,
            max_length=2000
        )
        self.add_item(self.name_input)
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.name_input.value, self.content_input.value)

# --- VIEWS ---

class PersonalityView(ui.View):
    def __init__(self, bot, cog):
        super().__init__(timeout=180)
        self.bot = bot
        self.cog = cog

    @ui.button(label="View Current", style=discord.ButtonStyle.primary)
    async def view_current(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        name = self.bot.ai.personality.current_name
        content = self.bot.ai.personality.current_personality
        await interaction.followup.send(f"### Current Personality: **{name}**\n>>> {content}", ephemeral=True)

    @ui.button(label="Switch", style=discord.ButtonStyle.secondary)
    async def switch_personality(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        options = [
            discord.SelectOption(label=p, value=p, default=(p == self.bot.ai.personality.current_name))
            for p in self.bot.ai.personality.list_all()
        ][:25]
        
        select = ui.Select(placeholder="Choose a personality...", options=options)
        
        async def select_callback(inter: discord.Interaction):
            await inter.response.defer(ephemeral=True)
            name = select.values[0]
            self.bot.ai.personality.load(name)
            self.bot.ai.memory.clear(str(inter.channel_id))
            await self.bot.update_presence()
            await inter.followup.send(f"Switched to personality: **{name}**", ephemeral=True)
            
        select.callback = select_callback
        view = ui.View()
        view.add_item(select)
        await interaction.followup.send("Select a new personality:", view=view, ephemeral=True)

    @ui.button(label="Create/Update", style=discord.ButtonStyle.success)
    async def create_new(self, interaction: discord.Interaction, button: ui.Button):
        # Modals can't be deferred before being sent
        async def callback(inter, name, content):
            await inter.response.defer(ephemeral=True)
            self.bot.ai.personality.save(name, content)
            await inter.followup.send(f"Personality **{name}** saved/updated!", ephemeral=True)

        await interaction.response.send_modal(CreateModal("Create Personality", callback))

    @ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_personality(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        options = [
            discord.SelectOption(label=p, value=p)
            for p in self.bot.ai.personality.list_all() if p != "default"
        ][:25]
        
        if not options:
            await interaction.followup.send("No custom personalities to delete.", ephemeral=True)
            return

        select = ui.Select(placeholder="Select personality to delete...", options=options)
        
        async def delete_callback(inter: discord.Interaction):
            await inter.response.defer(ephemeral=True)
            name = select.values[0]
            if self.bot.ai.personality.delete(name):
                await inter.followup.send(f"Personality **{name}** deleted.", ephemeral=True)
            else:
                await inter.followup.send("Failed to delete.", ephemeral=True)
            
        select.callback = delete_callback
        view = ui.View()
        view.add_item(select)
        await interaction.followup.send("Select a personality to **permanently delete**:", view=view, ephemeral=True)

class InstructionView(ui.View):
    def __init__(self, bot, cog):
        super().__init__(timeout=180)
        self.bot = bot
        self.cog = cog

    @ui.button(label="List & Toggle", style=discord.ButtonStyle.primary)
    async def list_toggle(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        instructions = self.bot.ai.instructions.list_all()
        if not instructions:
            await interaction.followup.send("No instructions found.", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=name, 
                value=name, 
                description="Active" if active else "Inactive"
            )
            for name, active in instructions
        ][:25]
        
        select = ui.Select(
            placeholder="Select instruction to TOGGLE state...",
            options=options
        )
        
        async def toggle_callback(inter: discord.Interaction):
            await inter.response.defer(ephemeral=True)
            name = select.values[0]
            # Find current status to flip it
            current_status = next(active for n, active in instructions if n == name)
            new_status = not current_status
            
            if self.bot.ai.instructions.toggle(name, new_status):
                status_text = "activated" if new_status else "deactivated"
                await inter.followup.send(f"Instruction **{name}** {status_text}.", ephemeral=True)
            else:
                await inter.followup.send("Error toggling instruction.", ephemeral=True)
            
        select.callback = toggle_callback
        view = ui.View()
        view.add_item(select)
        
        status_list = "\n".join([f"- {'(OK)' if a else '(X)'} **{n}**" for n, a in instructions])
        await interaction.followup.send(f"### Current Instructions:\n{status_list}\n\nSelect one to flip its state:", view=view, ephemeral=True)

    @ui.button(label="Create/Update", style=discord.ButtonStyle.success)
    async def create_new(self, interaction: discord.Interaction, button: ui.Button):
        async def callback(inter, name, content):
            await inter.response.defer(ephemeral=True)
            self.bot.ai.instructions.create_or_update(name, content)
            await inter.followup.send(f"Instruction **{name}** saved/updated.", ephemeral=True)

        await interaction.response.send_modal(CreateModal("Create Instruction", callback, True))

    @ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_instr(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        instructions = self.bot.ai.instructions.list_all()
        options = [discord.SelectOption(label=name, value=name) for name, active in instructions][:25]
        
        if not options:
            await interaction.followup.send("No instructions to delete.", ephemeral=True)
            return

        select = ui.Select(placeholder="Select instruction to delete...", options=options)
        
        async def delete_callback(inter: discord.Interaction):
            await inter.response.defer(ephemeral=True)
            name = select.values[0]
            if self.bot.ai.instructions.delete(name):
                await inter.followup.send(f"Instruction **{name}** deleted.", ephemeral=True)
            else:
                await inter.followup.send("Failed to delete.", ephemeral=True)
            
        select.callback = delete_callback
        view = ui.View()
        view.add_item(select)
        await interaction.followup.send("Select an instruction to **permanently delete**:", view=view, ephemeral=True)

class SkillView(ui.View):
    def __init__(self, bot, cog):
        super().__init__(timeout=180)
        self.bot = bot
        self.cog = cog

    @ui.button(label="List & Toggle Skills", style=discord.ButtonStyle.primary)
    async def list_toggle(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        skills = self.bot.ai.skills.list_all()
        if not skills:
            await interaction.followup.send("No skills found.", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=name, 
                value=name, 
                description=f"{'Active' if active else 'Inactive'} - {desc[:50]}"
            )
            for name, active, desc in skills
        ][:25]
        
        select = ui.Select(
            placeholder="Select skill to TOGGLE state...",
            options=options
        )
        
        async def toggle_callback(inter: discord.Interaction):
            await inter.response.defer(ephemeral=True)
            name = select.values[0]
            current_status = next(active for n, active, desc in skills if n == name)
            new_status = not current_status
            
            if self.bot.ai.skills.toggle_skill(name, new_status):
                status_text = "activated" if new_status else "deactivated"
                await inter.followup.send(f"Skill **{name}** {status_text}.", ephemeral=True)
            else:
                await inter.followup.send("Error toggling skill.", ephemeral=True)
            
        select.callback = toggle_callback
        view = ui.View()
        view.add_item(select)
        
        status_list = "\n".join([f"- {'(OK)' if a else '(X)'} **{n}** - {d}" for n, a, d in skills])
        await interaction.followup.send(f"### Current Skills:\n{status_list}\n\nSelect one to flip its state:", view=view, ephemeral=True)


# --- COG ---

class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_creator(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == CREATOR_ID

    # --- STANDALONE COMMANDS ---

    async def model_autocomplete(self, interaction: discord.Interaction, current: str):
        if not self.is_creator(interaction): return []
        # Zero-latency access to pre-cached model list
        models = self.bot.ai.get_cached_models()
        return [
            app_commands.Choice(name=m, value=m) 
            for m in models if current.lower() in m.lower()
        ][:25]

    @app_commands.command(name="model", description="Change the Ollama model used (Creator Only).")
    @app_commands.autocomplete(model_name=model_autocomplete)
    async def change_model(self, interaction: discord.Interaction, model_name: str):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return
        self.bot.ai.change_model(model_name)
        self.bot.ai.memory.clear(str(interaction.channel_id))
        await self.bot.update_presence()
        await interaction.followup.send(f"**Brain replaced!** Using `{model_name}`.", ephemeral=True)

    @app_commands.command(name="reset", description="Clear memory of this channel (Creator Only).")
    async def reset_memory(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return
        self.bot.ai.memory.clear(str(interaction.channel_id))
        await interaction.followup.send("**Memory formatted!**", ephemeral=True)

    @app_commands.command(name="memory", description="Check current memory usage and context stats.")
    async def memory_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return
        
        channel_id = str(interaction.channel_id)
        sys_stats = self.bot.ai.get_system_stats()
        mem_stats = self.bot.ai.memory.get_stats(channel_id)
        model_info = await self.bot.ai.get_model_info()
        
        total_chars = sys_stats["total_persistent_chars"] + mem_stats["total_volatile_chars"]
        
        # Approximate tokens (1 token ~ 4 chars for English/French)
        est_tokens = total_chars // 4 
        capacity = model_info["context_limit"]
        percent = (est_tokens / capacity) * 100

        embed = discord.Embed(
            title="Memory and Context Diagnostics",
            description=f"Active Model: `{model_info['model']}`",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Persistent Memory (Static)", 
            value=f"- **Personality:** `{sys_stats['personality_name']}` ({sys_stats['personality_chars']} chars)\n"
                  f"- **Active Instructions:** {sys_stats['instructions_chars']} chars\n"
                  f"**Total:** {sys_stats['total_persistent_chars']} chars",
            inline=False
        )
        
        embed.add_field(
            name="Compressible Memory (Volatile)", 
            value=f"- **History:** {mem_stats['history_count']} messages ({mem_stats['history_chars']} chars)\n"
                  f"- **Context Summary:** {mem_stats['summary_chars']} chars\n"
                  f"**Total:** {mem_stats['total_volatile_chars']} chars",
            inline=False
        )
        
        details_text = f"**Estimated Usage:** ~{est_tokens} / {capacity} tokens ({percent:.1f}%)\n"
        details_text += f"*Limit based on current model's configuration.*"
        
        embed.add_field(
            name="Resource Quota",
            value=details_text,
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    # --- CONSOLIDATED COMMANDS ---

    @app_commands.command(name="personality", description="Open the Personality Management dashboard.")
    async def manage_personality(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return
        await interaction.followup.send(
            "## Personality Management\nSelect an action below to view, switch, or modify personalities.",
            view=PersonalityView(self.bot, self),
            ephemeral=True
        )

    @app_commands.command(name="instructions", description="Open the Global Instructions dashboard.")
    async def manage_instructions(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return
        await interaction.followup.send(
            "## Global Instructions\nManage the rules that all personalities must follow.",
            view=InstructionView(self.bot, self),
            ephemeral=True
        )

    @app_commands.command(name="skills", description="Open the Skills Management dashboard.")
    async def manage_skills(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return
        await interaction.followup.send(
            "## Skills Management\nManage the modular capabilities of your AI.",
            view=SkillView(self.bot, self),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(AICog(bot))

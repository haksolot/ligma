import discord
from discord import app_commands, ui
from discord.ext import commands
from config import CREATOR_ID, LLM_PROVIDER, DEFAULT_MODEL

# ─────────────────────────────────────────────────────────────────────────────
# MODALS
# ─────────────────────────────────────────────────────────────────────────────


class CreateModal(ui.Modal):
    def __init__(self, title, callback_func):
        super().__init__(title=title)
        self.callback_func = callback_func

        self.name_input = ui.TextInput(
            label="Name",
            placeholder="Enter a unique name...",
            min_length=2,
            max_length=50,
        )
        self.content_input = ui.TextInput(
            label="Content / Prompt",
            style=discord.TextStyle.paragraph,
            placeholder="Enter the detailed content here...",
            min_length=5,
            max_length=2000,
        )
        self.add_item(self.name_input)
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(
            interaction, self.name_input.value, self.content_input.value
        )


# ─────────────────────────────────────────────────────────────────────────────
# SUB-VIEWS (accessed from PanelView)
# ─────────────────────────────────────────────────────────────────────────────


class BackButton(ui.Button):
    def __init__(self, panel_view_factory):
        super().__init__(label="← Back", style=discord.ButtonStyle.secondary, row=4)
        self.panel_view_factory = panel_view_factory

    async def callback(self, interaction: discord.Interaction):
        view, embed = await self.panel_view_factory()
        await interaction.response.edit_message(embed=embed, view=view)


class ModelView(ui.View):
    def __init__(self, bot, make_panel):
        super().__init__(timeout=180)
        self.bot = bot
        self.make_panel = make_panel
        self.add_item(BackButton(make_panel))

    @ui.button(label="Change Model", style=discord.ButtonStyle.primary)
    async def change_model_btn(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.defer(ephemeral=False)
        models = self.bot.ai.get_cached_models()
        if not models:
            await interaction.followup.send("No models available.", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=m[:100], value=m, default=(m == self.bot.ai.current_model)
            )
            for m in models[:25]
        ]
        select = ui.Select(placeholder="Choose a model...", options=options)

        async def select_cb(inter: discord.Interaction):
            await inter.response.defer()
            chosen = select.values[0]
            self.bot.ai.change_model(chosen)
            self.bot.ai.memory.clear(str(inter.channel_id))
            await self.bot.update_presence()
            view, embed = await self.make_panel()
            await inter.edit_original_response(embed=embed, view=view)

        select.callback = select_cb
        v = ui.View()
        v.add_item(select)
        embed = discord.Embed(
            title="🤖 Change Model",
            description=f"Current: `{self.bot.ai.current_model}`",
            color=discord.Color.blue(),
        )
        await interaction.edit_original_response(embed=embed, view=v)


class PersonalityView(ui.View):
    def __init__(self, bot, make_panel):
        super().__init__(timeout=180)
        self.bot = bot
        self.make_panel = make_panel
        self.add_item(BackButton(make_panel))

    @ui.button(label="View Current", style=discord.ButtonStyle.primary)
    async def view_current(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        name = self.bot.ai.personality.current_name
        content = self.bot.ai.personality.current_personality
        embed = discord.Embed(
            title=f"🎭 Personality: {name}",
            description=f"```{content[:2000]}```",
            color=discord.Color.purple(),
        )
        await interaction.edit_original_response(embed=embed, view=self)

    @ui.button(label="Switch", style=discord.ButtonStyle.secondary)
    async def switch_personality(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.defer()
        options = [
            discord.SelectOption(
                label=p, value=p, default=(p == self.bot.ai.personality.current_name)
            )
            for p in self.bot.ai.personality.list_all()
        ][:25]
        select = ui.Select(placeholder="Choose a personality...", options=options)

        async def select_cb(inter: discord.Interaction):
            await inter.response.defer()
            name = select.values[0]
            self.bot.ai.personality.load(name)
            self.bot.ai.memory.clear(str(inter.channel_id))
            await self.bot.update_presence()
            embed = discord.Embed(
                title="🎭 Personality",
                description=f"Switched to **{name}**.",
                color=discord.Color.purple(),
            )
            await inter.edit_original_response(embed=embed, view=self)

        select.callback = select_cb
        v = ui.View()
        v.add_item(select)
        embed = discord.Embed(
            title="🎭 Switch Personality", color=discord.Color.purple()
        )
        await interaction.edit_original_response(embed=embed, view=v)

    @ui.button(label="Create / Update", style=discord.ButtonStyle.success)
    async def create_new(self, interaction: discord.Interaction, button: ui.Button):
        async def callback(inter, name, content):
            await inter.response.defer()
            self.bot.ai.personality.save(name, content)
            self.bot.ai.personality.refresh_cache()
            embed = discord.Embed(
                title="🎭 Personality",
                description=f"**{name}** saved.",
                color=discord.Color.purple(),
            )
            await inter.edit_original_response(embed=embed, view=self)

        await interaction.response.send_modal(
            CreateModal("Create / Update Personality", callback)
        )

    @ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_personality(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.defer()
        options = [
            discord.SelectOption(label=p, value=p)
            for p in self.bot.ai.personality.list_all()
            if p != "default"
        ][:25]
        if not options:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="🎭 Personality",
                    description="No custom personalities to delete.",
                    color=discord.Color.red(),
                ),
                view=self,
            )
            return
        select = ui.Select(placeholder="Select to delete...", options=options)

        async def delete_cb(inter: discord.Interaction):
            await inter.response.defer()
            name = select.values[0]
            self.bot.ai.personality.delete(name)
            self.bot.ai.personality.refresh_cache()
            embed = discord.Embed(
                title="🎭 Personality",
                description=f"**{name}** deleted.",
                color=discord.Color.red(),
            )
            await inter.edit_original_response(embed=embed, view=self)

        select.callback = delete_cb
        v = ui.View()
        v.add_item(select)
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="🎭 Delete Personality", color=discord.Color.red()
            ),
            view=v,
        )


class InstructionView(ui.View):
    def __init__(self, bot, make_panel):
        super().__init__(timeout=180)
        self.bot = bot
        self.make_panel = make_panel
        self.add_item(BackButton(make_panel))

    @ui.button(label="List & Toggle", style=discord.ButtonStyle.primary)
    async def list_toggle(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        instructions = self.bot.ai.instructions.list_all()
        if not instructions:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="📋 Instructions",
                    description="No instructions found.",
                    color=discord.Color.orange(),
                ),
                view=self,
            )
            return

        options = [
            discord.SelectOption(
                label=name, value=name, description="Active" if active else "Inactive"
            )
            for name, active in instructions
        ][:25]
        select = ui.Select(placeholder="Toggle an instruction...", options=options)

        async def toggle_cb(inter: discord.Interaction):
            await inter.response.defer()
            name = select.values[0]
            current_status = next(a for n, a in instructions if n == name)
            self.bot.ai.instructions.toggle(name, not current_status)
            status = "activated" if not current_status else "deactivated"
            embed = discord.Embed(
                title="📋 Instructions",
                description=f"**{name}** {status}.",
                color=discord.Color.orange(),
            )
            await inter.edit_original_response(embed=embed, view=self)

        select.callback = toggle_cb
        status_list = "\n".join(
            [f"{'🟢' if a else '🔴'} **{n}**" for n, a in instructions]
        )
        v = ui.View()
        v.add_item(select)
        embed = discord.Embed(
            title="📋 Instructions",
            description=status_list + "\n\nSelect one to toggle:",
            color=discord.Color.orange(),
        )
        await interaction.edit_original_response(embed=embed, view=v)

    @ui.button(label="Create / Update", style=discord.ButtonStyle.success)
    async def create_new(self, interaction: discord.Interaction, button: ui.Button):
        async def callback(inter, name, content):
            await inter.response.defer()
            self.bot.ai.instructions.create_or_update(name, content)
            self.bot.ai.instructions.refresh_cache()
            embed = discord.Embed(
                title="📋 Instructions",
                description=f"**{name}** saved.",
                color=discord.Color.orange(),
            )
            await inter.edit_original_response(embed=embed, view=self)

        await interaction.response.send_modal(
            CreateModal("Create / Update Instruction", callback)
        )

    @ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_instr(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        instructions = self.bot.ai.instructions.list_all()
        options = [
            discord.SelectOption(label=name, value=name) for name, _ in instructions
        ][:25]
        if not options:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="📋 Instructions",
                    description="No instructions to delete.",
                    color=discord.Color.red(),
                ),
                view=self,
            )
            return
        select = ui.Select(placeholder="Select to delete...", options=options)

        async def delete_cb(inter: discord.Interaction):
            await inter.response.defer()
            name = select.values[0]
            self.bot.ai.instructions.delete(name)
            self.bot.ai.instructions.refresh_cache()
            embed = discord.Embed(
                title="📋 Instructions",
                description=f"**{name}** deleted.",
                color=discord.Color.red(),
            )
            await inter.edit_original_response(embed=embed, view=self)

        select.callback = delete_cb
        v = ui.View()
        v.add_item(select)
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="📋 Delete Instruction", color=discord.Color.red()
            ),
            view=v,
        )


class SkillView(ui.View):
    def __init__(self, bot, make_panel):
        super().__init__(timeout=180)
        self.bot = bot
        self.make_panel = make_panel
        self.add_item(BackButton(make_panel))

    @ui.button(label="List & Toggle", style=discord.ButtonStyle.primary)
    async def list_toggle(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        skills = self.bot.ai.skills.list_all()
        if not skills:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="🔧 Skills",
                    description="No skills loaded.",
                    color=discord.Color.teal(),
                ),
                view=self,
            )
            return

        options = [
            discord.SelectOption(
                label=name,
                value=name,
                description=f"{'Active' if active else 'Inactive'} — {desc[:50]}",
            )
            for name, active, desc in skills
        ][:25]
        select = ui.Select(placeholder="Toggle a skill...", options=options)

        async def toggle_cb(inter: discord.Interaction):
            await inter.response.defer()
            name = select.values[0]
            current_status = next(a for n, a, _ in skills if n == name)
            self.bot.ai.skills.toggle_skill(name, not current_status)
            status = "activated" if not current_status else "deactivated"
            embed = discord.Embed(
                title="🔧 Skills",
                description=f"**{name}** {status}.",
                color=discord.Color.teal(),
            )
            await inter.edit_original_response(embed=embed, view=self)

        select.callback = toggle_cb
        status_list = "\n".join(
            [f"{'🟢' if a else '🔴'} **{n}** — {d}" for n, a, d in skills]
        )
        v = ui.View()
        v.add_item(select)
        embed = discord.Embed(
            title="🔧 Skills",
            description=status_list + "\n\nSelect one to toggle:",
            color=discord.Color.teal(),
        )
        await interaction.edit_original_response(embed=embed, view=v)


class StatsView(ui.View):
    def __init__(self, bot, make_panel, channel_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.make_panel = make_panel
        self.channel_id = channel_id
        self.add_item(BackButton(make_panel))

    @ui.button(label="Refresh", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        embed = await self._build_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    async def _build_embed(self) -> discord.Embed:
        channel_id = str(self.channel_id)
        sys_stats = self.bot.ai.get_system_stats()
        mem_stats = self.bot.ai.memory.get_stats(channel_id)
        model_info = await self.bot.ai.get_model_info()
        metrics = self.bot.ai.last_metrics

        total_chars = (
            sys_stats["total_persistent_chars"] + mem_stats["total_volatile_chars"]
        )
        est_tokens = total_chars // 4
        capacity = model_info["context_limit"]
        percent = (est_tokens / capacity) * 100

        embed = discord.Embed(
            title="📊 Status & Performance",
            description=f"Model: `{model_info['model']}`",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Memory",
            value=(
                f"Personality: `{sys_stats['personality_name']}` ({sys_stats['personality_chars']} chars)\n"
                f"Instructions: {sys_stats['instructions_chars']} chars\n"
                f"History: {mem_stats['history_count']} messages\n"
                f"Usage: ~{est_tokens}/{capacity} tokens ({percent:.1f}%)"
            ),
            inline=True,
        )
        if metrics:
            total_sec = (metrics.get("total_duration") or 0) / 1e9
            eval_count = metrics.get("eval_count") or 0
            eval_sec = (metrics.get("eval_duration") or 0) / 1e9
            tps = eval_count / eval_sec if eval_sec > 0 else 0
            embed.add_field(
                name="Last Generation",
                value=(
                    f"Speed: **{tps:.1f} t/s**\n"
                    f"Tokens: {eval_count}\n"
                    f"Total time: {total_sec:.2f}s"
                ),
                inline=True,
            )
        return embed


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PANEL VIEW
# ─────────────────────────────────────────────────────────────────────────────


class PanelView(ui.View):
    def __init__(self, bot, channel_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.channel_id = channel_id

    async def _make_panel(self):
        """Factory: rebuilds a fresh PanelView + embed for 'Back' navigation."""
        view = PanelView(self.bot, self.channel_id)
        embed = await _build_panel_embed(self.bot, self.channel_id)
        return view, embed

    @ui.button(label="🤖 Model", style=discord.ButtonStyle.primary, row=0)
    async def model_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        view = ModelView(self.bot, self._make_panel)
        embed = discord.Embed(
            title="🤖 Model",
            description=f"Current: `{self.bot.ai.current_model}`\nSelect a model to switch:",
            color=discord.Color.blue(),
        )
        await interaction.edit_original_response(embed=embed, view=view)

    @ui.button(label="🔄 Reset Memory", style=discord.ButtonStyle.secondary, row=0)
    async def reset_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.bot.ai.memory.clear(str(self.channel_id))
        view, embed = await self._make_panel()
        embed.set_footer(text="✅ Memory cleared for this channel.")
        await interaction.edit_original_response(embed=embed, view=view)

    @ui.button(label="🎭 Personality", style=discord.ButtonStyle.secondary, row=0)
    async def personality_btn(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.defer()
        view = PersonalityView(self.bot, self._make_panel)
        embed = discord.Embed(
            title="🎭 Personality Management",
            description=f"Current: **{self.bot.ai.personality.current_name}**",
            color=discord.Color.purple(),
        )
        await interaction.edit_original_response(embed=embed, view=view)

    @ui.button(label="📋 Instructions", style=discord.ButtonStyle.secondary, row=1)
    async def instructions_btn(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.defer()
        view = InstructionView(self.bot, self._make_panel)
        instructions = self.bot.ai.instructions.list_all()
        active_count = sum(1 for _, a in instructions if a)
        embed = discord.Embed(
            title="📋 Instructions",
            description=f"{active_count}/{len(instructions)} active",
            color=discord.Color.orange(),
        )
        await interaction.edit_original_response(embed=embed, view=view)

    @ui.button(label="🔧 Skills", style=discord.ButtonStyle.secondary, row=1)
    async def skills_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        view = SkillView(self.bot, self._make_panel)
        skills = self.bot.ai.skills.list_all()
        active_count = sum(1 for _, a, _ in skills if a)
        embed = discord.Embed(
            title="🔧 Skills",
            description=f"{active_count}/{len(skills)} active",
            color=discord.Color.teal(),
        )
        await interaction.edit_original_response(embed=embed, view=view)

    @ui.button(label="📊 Stats", style=discord.ButtonStyle.secondary, row=1)
    async def stats_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        view = StatsView(self.bot, self._make_panel, self.channel_id)
        embed = await view._build_embed()
        await interaction.edit_original_response(embed=embed, view=view)


async def _build_panel_embed(bot, channel_id: int) -> discord.Embed:
    """Builds the main panel overview embed."""
    channel_id_str = str(channel_id)
    sys_stats = bot.ai.get_system_stats()
    mem_stats = bot.ai.memory.get_stats(channel_id_str)

    try:
        model_info = await bot.ai.get_model_info()
        capacity = model_info["context_limit"]
    except Exception:
        capacity = 2048

    total_chars = (
        sys_stats["total_persistent_chars"] + mem_stats["total_volatile_chars"]
    )
    est_tokens = total_chars // 4
    percent = (est_tokens / capacity) * 100

    skills = bot.ai.skills.list_all()
    active_skills = sum(1 for _, a, _ in skills if a)
    instructions = bot.ai.instructions.list_all()
    active_instr = sum(1 for _, a in instructions if a)
    is_blocked = getattr(bot, "is_blocked", False)

    embed = discord.Embed(
        title="⚙️ L.I.G.M.A. Control Panel",
        color=discord.Color.red() if is_blocked else discord.Color.green(),
    )
    embed.add_field(
        name="Provider", value=f"`{bot.ai.get_provider_name()}`", inline=True
    )
    embed.add_field(name="Model", value=f"`{bot.ai.current_model}`", inline=True)
    embed.add_field(
        name="Personality", value=f"`{sys_stats['personality_name']}`", inline=True
    )
    embed.add_field(
        name="Status", value="🔴 BLOCKED" if is_blocked else "🟢 ONLINE", inline=True
    )
    embed.add_field(
        name="Memory Usage", value=f"~{percent:.1f}% ({est_tokens} tokens)", inline=True
    )
    embed.add_field(
        name="Skills", value=f"{active_skills}/{len(skills)} active", inline=True
    )
    embed.add_field(
        name="Instructions",
        value=f"{active_instr}/{len(instructions)} active",
        inline=True,
    )
    return embed


# ─────────────────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────────────────


class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_creator(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == CREATOR_ID

    @app_commands.command(
        name="panel", description="Open the L.I.G.M.A. control panel (Creator Only)."
    )
    async def panel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return
        view = PanelView(self.bot, interaction.channel_id)
        embed = await _build_panel_embed(self.bot, interaction.channel_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(
        name="block", description="Toggle message handling on/off (Creator Only)."
    )
    async def toggle_block(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return
        self.bot.is_blocked = not self.bot.is_blocked
        state = "BLOCKED" if self.bot.is_blocked else "ONLINE"
        emoji = "🔴" if self.bot.is_blocked else "🟢"
        await interaction.followup.send(
            f"{emoji} Status is now **{state}**.", ephemeral=True
        )

    @app_commands.command(
        name="stop",
        description="Cancel the active AI generation in this channel (Creator Only).",
    )
    async def stop_generation(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return
        channel_id_str = str(interaction.channel_id)
        chat_cog = self.bot.get_cog("ChatCog")
        if chat_cog and channel_id_str in chat_cog.active_tasks:
            task = chat_cog.active_tasks[channel_id_str]
            if not task.done():
                task.cancel()
                await interaction.followup.send("Generation cancelled.", ephemeral=True)
                return
        await interaction.followup.send(
            "No active generation in this channel.", ephemeral=True
        )

    @app_commands.command(
        name="provider",
        description="Switch LLM provider or view current provider (Creator Only).",
    )
    @app_commands.describe(
        action="Action to perform: 'status' to see current, 'ollama' or 'openrouter' to switch"
    )
    async def provider_command(
        self, interaction: discord.Interaction, action: str = "status"
    ):
        await interaction.response.defer(ephemeral=True)
        if not self.is_creator(interaction):
            await interaction.followup.send("Unauthorized.", ephemeral=True)
            return

        if action == "status":
            provider_name = self.bot.ai.get_provider_name()
            model = self.bot.ai.current_model
            await interaction.followup.send(
                f"**Current Provider:** `{provider_name}`\n**Model:** `{model}`",
                ephemeral=True,
            )
            return

        new_model = None
        if action == "ollama":
            new_model = "llama3.2:3b"
        elif action == "openrouter":
            new_model = "openai/gpt-4o"
        else:
            await interaction.followup.send(
                f"Unknown provider: `{action}`. Use `ollama` or `openrouter`.",
                ephemeral=True,
            )
            return

        success, msg = self.bot.ai.switch_provider(action, new_model)
        if success:
            self.bot.ai.memory.clear(str(interaction.channel_id))
            await self.bot.update_presence()
            await interaction.followup.send(
                f"✅ {msg} | Model: `{new_model}`", ephemeral=True
            )
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AICog(bot))

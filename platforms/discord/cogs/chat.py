import discord
import re
import time
import asyncio
from discord import app_commands
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
        if not content or not hasattr(channel, "members") or "@" not in content:
            return content

        # Build mapping for members (limit to 100 most relevant for performance)
        name_to_id = {}
        content_lower = content.lower()
        
        # Only process members whose names are actually mentioned in the content
        for m in channel.members:
            disp_lower = m.display_name.lower()
            name_lower = m.name.lower()
            
            if f"@{disp_lower}" in content_lower:
                name_to_id[disp_lower] = m.id
            if f"@{name_lower}" in content_lower:
                name_to_id[name_lower] = m.id
            
            if len(name_to_id) >= 50: break # Safety cap
            
        if not name_to_id:
            return content
            
        sorted_names = sorted(name_to_id.keys(), key=len, reverse=True)
        pattern = re.compile(
            "|".join(rf"@{re.escape(name)}(?!\w)" for name in sorted_names),
            re.IGNORECASE
        )
        
        def sub_func(match):
            matched_text = match.group(0).lower().lstrip('@')
            user_id = name_to_id.get(matched_text)
            return f"<@{user_id}>" if user_id else match.group(0)

        return pattern.sub(sub_func, content)

    async def get_ai_response(self, channel, author, content, trigger_message=None, reaction_info=None):
        """
        Core logic to get AI response, handle skills, and update memory.
        Returns (final_text, target_reply_msg, gif_url)
        """
        channel_id_str = str(channel.id)
        bot_id = self.bot.user.id
        bot_name = self.bot.user.name.lower()
        bot_display = self.bot.user.display_name.lower()

        # Build specific context for reactions or replies
        extra_event_context = ""
        if reaction_info:
            emoji = reaction_info.get('emoji')
            msg_content = reaction_info.get('message_content')
            extra_event_context = f"\n\n### EVENT: REACTION\n{author.display_name} reacted with {emoji} to your message: \"{msg_content}\".\nYou can acknowledge this reaction or just continue the chat."
        elif trigger_message and trigger_message.reference and trigger_message.reference.resolved:
            ref = trigger_message.reference.resolved
            if isinstance(ref, discord.Message):
                extra_event_context = f"\n\n### EVENT: REPLY\n{author.display_name} is replying to your message (ID: {ref.id}): \"{ref.clean_content}\"."

        # Update memory with USER message (if it's a real message, not just a reaction trigger)
        if not reaction_info:
            msg_id = trigger_message.id if trigger_message else None
            await self.bot.ai.memory.add_message(channel_id_str, "user", content, message_id=msg_id, author_name=author.display_name)

        # Get Discord Context
        members_list = await DiscordContextFetcher.get_channel_members(channel)
        discord_context = f"\n\n### DISCORD ENVIRONMENT\nChannel: #{channel.name}\nCurrent Members:\n{members_list}\n\n"
        discord_context += f"You are talking to: {author.display_name} (ID: {author.id})"
        discord_context += extra_event_context

        # Build Identity
        identity = f"You are currently logged into Discord as: {bot_display} (Username: {bot_name}). "
        identity += f"Your Bot User ID is {bot_id} (Warning: NEVER use this ID for reacting or replying, it is NOT a message ID). "
        identity += f"You are in a conversation with {author.display_name}."

        # First Call to AI
        response = await self.bot.ai.chat(channel_id_str, content, extra_context=discord_context, bot_identity=identity, author_name=author.display_name)

        # --- REFLEXION LOOP ---
        max_steps = 2
        step = 0
        current_extra_context = discord_context
        interim_messages = []
        
        while step < max_steps:
            # Check if any skill needs a reflection (like Search or Browser)
            reflection_prompt = await self.bot.ai.skills.run_reflections(response, trigger_message)
            if not reflection_prompt:
                break
            
            # We add the assistant's previous message to interim_messages
            # so the model knows it already "thought" of this action.
            interim_messages.append({"role": "assistant", "content": response})
            
            # We add the result as a system message in the interim context
            interim_messages.append({"role": "system", "content": reflection_prompt})
            
            response = await self.bot.ai.chat(channel_id_str, content, 
                                            extra_context=current_extra_context, 
                                            bot_identity=identity,
                                            interim_messages=interim_messages,
                                            author_name=author.display_name)
            step += 1

        # --- FINAL ACTIONS ---
        final_text, context_dict = await self.bot.ai.skills.run_actions(response, trigger_message)
        
        target_reply_msg = context_dict.get('target_reply_msg')
        gif_query = context_dict.get('gif_query')
        gif_url = await GiphyFetcher.get_gif_url(gif_query) if gif_query else None

        # Clean final text
        final_text = final_text.replace('\u200b', '').strip()
        
        # Add indicators if performed
        indicators = []
        if context_dict.get('search_performed'): indicators.append("DuckDuckGo")
        if context_dict.get('read_performed'): indicators.append("Browser")
        
        if indicators and final_text:
            final_text += f"\n\n*(Sources: {', '.join(indicators)})*"

        if final_text:
            final_text = self._process_mentions(final_text, channel)

        return final_text, target_reply_msg, gif_url

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        channel_id_str = str(message.channel.id)
        now = time.time()

        # Detection logic
        bot_id = self.bot.user.id
        bot_name = self.bot.user.name.lower()
        bot_display = self.bot.user.display_name.lower()
        content_lower = message.content.lower()
        
        is_mentioned = self.bot.user.mentioned_in(message)
        is_named = bot_name in content_lower or bot_display in content_lower
        
        is_reply = False
        if message.reference and message.reference.resolved:
            if isinstance(message.reference.resolved, discord.Message):
                if message.reference.resolved.author.id == bot_id:
                    is_reply = True

        is_followup = False
        last_interaction = self.last_interactions.get(channel_id_str)
        if last_interaction:
            if (last_interaction["user_id"] == message.author.id and now - last_interaction["timestamp"] < 45):
                is_followup = True

        if is_mentioned or is_named or is_reply or is_followup:
            async with message.channel.typing():
                try:
                    clean_content = message.content.replace(f'<@!{bot_id}>', '').replace(f'<@{bot_id}>', '').strip()
                    if not clean_content and (is_mentioned or is_reply):
                        await message.channel.send("Did you call me?")
                        return
                    elif not clean_content:
                        return

                    final_text, target_reply, gif_url = await self.get_ai_response(message.channel, message.author, clean_content, trigger_message=message)

                    # Send responses
                    sent_msg = None
                    if final_text:
                        send_func = target_reply.reply if target_reply else message.channel.send
                        if len(final_text) > 2000:
                            for i in range(0, len(final_text), 2000):
                                sent_msg = await send_func(final_text[i:i+2000])
                        else:
                            sent_msg = await send_func(final_text)
                    
                    if gif_url:
                        await message.channel.send(gif_url)

                    # Update interaction state
                    self.last_interactions[channel_id_str] = {"user_id": message.author.id, "timestamp": time.time()}

                    # Save bot response to memory
                    if sent_msg:
                        await self.bot.ai.memory.add_message(channel_id_str, "assistant", final_text, message_id=sent_msg.id, author_name=self.bot.user.display_name)
                    # Note: We don't save empty/action-only responses to memory to keep history clean.

                except Exception as e:
                    print(f"[ChatCog] Error: {e}")
                    try: await message.channel.send(f"Oops, system error: {e}")
                    except: pass

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user:
            return

        # Check if the reaction is on a message sent by the bot
        if reaction.message.author.id == self.bot.user.id:
            async with reaction.message.channel.typing():
                try:
                    # Provide info about the reaction to the AI
                    reaction_info = {
                        "emoji": str(reaction.emoji),
                        "message_content": reaction.message.clean_content
                    }
                    
                    # Synthesize a prompt for the AI to react to the reaction
                    content = f"[REACTION: {reaction.emoji}]"
                    
                    final_text, target_reply, gif_url = await self.get_ai_response(
                        reaction.message.channel, 
                        user, 
                        content, 
                        trigger_message=reaction.message,
                        reaction_info=reaction_info
                    )

                    # Send responses
                    sent_msg = None
                    if final_text:
                        # For reactions, we reply to the reacted message or just send to channel
                        send_func = target_reply.reply if target_reply else reaction.message.channel.send
                        sent_msg = await send_func(final_text)
                    
                    if gif_url:
                        await reaction.message.channel.send(gif_url)

                    # Save bot response to memory if text was sent
                    if sent_msg and final_text:
                        channel_id_str = str(reaction.message.channel.id)
                        await self.bot.ai.memory.add_message(channel_id_str, "assistant", final_text, message_id=sent_msg.id, author_name=self.bot.user.display_name)

                except Exception as e:
                    print(f"[ChatCog] Reaction Error: {e}")

    @app_commands.command(name="hidden", description="Prompt the bot without showing your message in the chat history.")
    @app_commands.describe(prompt="The message to send to the AI.", private="If True, only you will see the response.")
    async def hidden_chat(self, interaction: discord.Interaction, prompt: str, private: bool = False):
        await interaction.response.defer(ephemeral=private)
        
        try:
            # Note: No trigger_message for slash commands, as there is no message object in history yet
            final_text, _, gif_url = await self.get_ai_response(interaction.channel, interaction.user, prompt)

            # Build full output
            output = final_text if final_text else ""
            if gif_url:
                output += f"\n{gif_url}" if output else gif_url

            if not output:
                output = "[Action Executed]"

            await interaction.followup.send(output, ephemeral=private)

            # Update interaction state for sticky conversation
            self.last_interactions[str(interaction.channel_id)] = {"user_id": interaction.user.id, "timestamp": time.time()}

            # Save assistant response to memory (we don't have an ID for ephemeral messages or slash responses easily, but we save the text)
            await self.bot.ai.memory.add_message(str(interaction.channel_id), "assistant", final_text or "[Action]", author_name=self.bot.user.display_name)

        except Exception as e:
            print(f"[ChatCog] Slash Error: {e}")
            await interaction.followup.send(f"Error processing hidden prompt: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChatCog(bot))

import discord
import re
import time
import asyncio
from discord import app_commands
from discord.ext import commands
from platforms.discord.context import DiscordContextFetcher
from core.utils.gifs import GiphyFetcher
from config import CREATOR_ID

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Format: {channel_id: {"user_id": int, "timestamp": float}}
        self.last_interactions = {}
        # Active asyncio tasks per channel for cancellation via /stop
        self.active_tasks: dict[str, asyncio.Task] = {}
        # Typing state: {channel_id: {user_id: timestamp}}
        self.typing_state: dict[str, dict[str, float]] = {}

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
            thread_context = reaction_info.get('thread_context', '')
            extra_event_context = (
                f"\n\n### EVENT: REACTION\n"
                f"{author.display_name} reacted with {emoji} to your message: \"{msg_content}\".\n"
            )
            if thread_context:
                extra_event_context += f"### SURROUNDING CONTEXT:\n{thread_context}\n"
            extra_event_context += "You can acknowledge this reaction or just continue the chat."
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
        
        # PROGRAMMATIC SAFETY: Strip any "(ID: 123456789) " prefix that might have leaked
        final_text = re.sub(r'^\(ID: \d+\)\s*', '', final_text)

        # CHECK FOR SILENCE REQUEST
        if "[IGNORE]" in final_text.upper():
            # Strip the tag
            final_text = re.sub(r'\[IGNORE\]', '', final_text, flags=re.IGNORECASE).strip()
            # If nothing left, stay silent
            if not final_text:
                return None, None, None

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

        if getattr(self.bot, 'is_blocked', False) and message.author.id != CREATOR_ID:
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
            async def _do_response():
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

                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        print(f"[ChatCog] Error: {e}")
                        try: await message.channel.send(f"Oops, system error: {e}")
                        except: pass

            task = asyncio.create_task(_do_response())
            self.active_tasks[channel_id_str] = task
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                self.active_tasks.pop(channel_id_str, None)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user:
            return

        if getattr(self.bot, 'is_blocked', False) and user.id != CREATOR_ID:
            return

        # Check if the reaction is on a message sent by the bot
        if reaction.message.author.id == self.bot.user.id:
            async with reaction.message.channel.typing():
                try:
                    # Fetch a few messages before the reacted message for context
                    thread_context = ""
                    try:
                        msgs = []
                        async for msg in reaction.message.channel.history(limit=5, before=reaction.message):
                            msgs.append(f"[{msg.created_at.strftime('%H:%M')}] {msg.author.display_name}: {msg.clean_content}")
                        thread_context = "\n".join(reversed(msgs))
                    except Exception:
                        pass

                    reaction_info = {
                        "emoji": str(reaction.emoji),
                        "message_content": reaction.message.clean_content,
                        "thread_context": thread_context,
                    }

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

    @commands.Cog.listener()
    async def on_typing(self, channel, user, when):
        if user == self.bot.user:
            return
        if getattr(self.bot, 'is_blocked', False) and user.id != CREATOR_ID:
            return
        channel_id_str = str(channel.id)
        last = self.last_interactions.get(channel_id_str)
        if last and last["user_id"] == user.id:
            # User is typing after bot just spoke to them — extend the followup window
            self.last_interactions[channel_id_str]["timestamp"] = time.time()

    @app_commands.command(name="think", description="Ask the AI to reason step-by-step before answering.")
    @app_commands.describe(prompt="The question or task for the AI to reason through.")
    async def think(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        if getattr(self.bot, 'is_blocked', False) and interaction.user.id != CREATOR_ID:
            await interaction.followup.send("The bot is currently blocked.", ephemeral=True)
            return

        augmented_prompt = (
            "Before answering, reason through this step by step inside a <thinking> block. "
            "Format your response as: <thinking>your reasoning here</thinking> then your actual answer.\n\n"
            + prompt
        )

        try:
            final_text, _, gif_url = await self.get_ai_response(
                interaction.channel, interaction.user, augmented_prompt
            )

            if not final_text:
                await interaction.followup.send("*(No response)*")
                return

            thinking_match = re.search(r'<thinking>(.*?)</thinking>', final_text, re.DOTALL | re.IGNORECASE)
            answer = re.sub(r'<thinking>.*?</thinking>', '', final_text, flags=re.DOTALL | re.IGNORECASE).strip()

            output_parts = []
            if thinking_match:
                reasoning = thinking_match.group(1).strip()
                if len(reasoning) > 1950:
                    reasoning = reasoning[:1950] + "..."
                output_parts.append(f"||{reasoning}||")

            if answer:
                output_parts.append(answer)
            elif not thinking_match:
                output_parts.append(final_text)

            output = "\n\n".join(output_parts)
            if gif_url:
                output += f"\n{gif_url}"

            if len(output) > 2000:
                for i in range(0, len(output), 2000):
                    await interaction.followup.send(output[i:i+2000])
            else:
                await interaction.followup.send(output)

            self.last_interactions[str(interaction.channel_id)] = {
                "user_id": interaction.user.id, "timestamp": time.time()
            }
            await self.bot.ai.memory.add_message(
                str(interaction.channel_id), "assistant", answer or final_text,
                author_name=self.bot.user.display_name
            )

        except Exception as e:
            print(f"[ChatCog] /think error: {e}")
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    @app_commands.command(name="hidden", description="Prompt the bot without showing your message in the chat history.")
    @app_commands.describe(prompt="The message to send to the AI.", private="If True, only you will see the response.")
    async def hidden_chat(self, interaction: discord.Interaction, prompt: str, private: bool = False):
        await interaction.response.defer(ephemeral=private)

        if getattr(self.bot, 'is_blocked', False) and interaction.user.id != CREATOR_ID:
            await interaction.followup.send("The bot is currently blocked.", ephemeral=True)
            return

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

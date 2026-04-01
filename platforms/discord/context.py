import discord

class DiscordContextFetcher:
    """Utility to fetch specific Discord data for the LLM context."""
    
    @staticmethod
    async def get_channel_members(channel: discord.TextChannel):
        """Returns a list of members in the channel with their display names and roles."""
        members_info = []
        # We limit to avoid huge prompts in giant servers
        if hasattr(channel, "members"):
            for member in channel.members[:50]: 
                roles = [r.name for r in member.roles if r.name != "@everyone"]
                info = f"- {member.display_name} (ID: {member.id})"
                if roles:
                    info += f" [Roles: {', '.join(roles)}]"
                members_info.append(info)
        
        return "\n".join(members_info)

    @staticmethod
    async def get_recent_history(channel: discord.TextChannel, limit: int = 10, exclude_id: int = None):
        """Fetches the last X messages in the channel, excluding a specific ID if provided."""
        try:
            print(f"[ContextFetcher] Fetching last {limit} messages from #{channel.name}...")
            history = []
            # We fetch a bit more to account for the excluded message
            async for msg in channel.history(limit=limit + 2):
                if exclude_id and msg.id == exclude_id:
                    continue
                
                author_name = msg.author.display_name
                content = msg.clean_content
                timestamp = msg.created_at.strftime("%H:%M")
                history.append(f"[{timestamp}] (ID: {msg.id}) {author_name}: {content}")
                
                if len(history) >= limit:
                    break
            
            print(f"[ContextFetcher] Successfully retrieved {len(history)} messages.")
            return "\n".join(reversed(history))
        except Exception as e:
            print(f"[ContextFetcher] Error fetching history: {e}")
            return "Could not retrieve history."

    @staticmethod
    def get_user_info(member: discord.Member):
        """Detailed info about a specific member."""
        roles = [r.name for r in member.roles if r.name != "@everyone"]
        return {
            "name": member.name,
            "display_name": member.display_name,
            "id": member.id,
            "top_role": member.top_role.name,
            "roles": roles,
            "joined_at": str(member.joined_at)
        }

import discord

class DiscordContextFetcher:
    """Utility to fetch specific Discord data for the LLM context."""
    
    @staticmethod
    async def get_channel_members(channel: discord.TextChannel):
        """Returns a list of members in the channel with their display names and roles."""
        members_info = []
        # We limit to avoid huge prompts in giant servers
        for member in channel.members[:50]: 
            roles = [r.name for r in member.roles if r.name != "@everyone"]
            info = f"- {member.display_name} (ID: {member.id})"
            if roles:
                info += f" [Roles: {', '.join(roles)}]"
            members_info.append(info)
        
        return "\n".join(members_info)

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

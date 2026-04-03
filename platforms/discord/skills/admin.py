import re
import datetime
from typing import Optional, Tuple, Dict, Any
import discord
from core.skills.base import BaseSkill

# Permission name → discord.Permissions attribute
PERM_MAP = {
    "send_messages": "send_messages",
    "read_messages": "read_messages",
    "manage_messages": "manage_messages",
    "manage_channels": "manage_channels",
    "manage_roles": "manage_roles",
    "kick_members": "kick_members",
    "ban_members": "ban_members",
    "attach_files": "attach_files",
    "embed_links": "embed_links",
    "mention_everyone": "mention_everyone",
    "add_reactions": "add_reactions",
    "use_voice_activation": "use_voice_activation",
    "speak": "speak",
    "mute_members": "mute_members",
    "deafen_members": "deafen_members",
    "move_members": "move_members",
    "administrator": "administrator",
    "view_channel": "view_channel",
    "connect": "connect",
    "stream": "stream",
    "use_embedded_activities": "use_embedded_activities",
    "create_instant_invite": "create_instant_invite",
}


def _parse_perms(perm_string: str) -> discord.Permissions:
    """Parse a '+'-separated permission string into a discord.Permissions object."""
    perms = discord.Permissions()
    for name in perm_string.split("+"):
        name = name.strip()
        attr = PERM_MAP.get(name)
        if attr:
            setattr(perms, attr, True)
    return perms


def _parse_named_args(arg_string: str) -> Dict[str, str]:
    """Parse 'key=value, key2=value2' into a dict."""
    result = {}
    for part in re.split(r',(?=\s*\w+=)', arg_string):
        part = part.strip()
        if '=' in part:
            k, _, v = part.partition('=')
            result[k.strip()] = v.strip()
    return result


class AdminSkill(BaseSkill):
    name = "Admin"
    description = "Full Discord server admin toolbox: roles, channels, members, permissions."
    is_active = True

    def get_prompt_injection(self) -> str:
        return (
            "**ADMIN**: You have full Discord server admin capabilities.\n"
            "## Query tags (use to fetch server data — reflection phase):\n"
            "- `[LIST_ROLES]` — list all roles with IDs\n"
            "- `[LIST_CHANNELS]` — list all channels with type, category, ID\n"
            "- `[LIST_MEMBERS]` — list first 50 members with ID and top role\n"
            "- `[LIST_CATEGORIES]` — list all categories and their channels\n"
            "- `[LIST_BANS]` — list banned users\n"
            "- `[GET_MEMBER: user_id]` — detailed member info\n"
            "- `[GET_ROLE: role_id]` — detailed role info\n"
            "## Action tags (execute after response):\n"
            "**Roles:** `[CREATE_ROLE: name]` | `[DELETE_ROLE: role_id]` | "
            "`[EDIT_ROLE: role_id, name=..., color=hex, hoist=true|false, mentionable=true|false]` | "
            "`[ASSIGN_ROLE: user_id, role_id]` | `[REMOVE_ROLE: user_id, role_id]`\n"
            "**Channels:** `[CREATE_CHANNEL: name, text|voice|forum|stage, category_id=optional]` | "
            "`[DELETE_CHANNEL: channel_id]` | "
            "`[EDIT_CHANNEL: channel_id, name=..., topic=..., slowmode=N, nsfw=true|false]` | "
            "`[MOVE_CHANNEL: channel_id, category_id]` | "
            "`[CREATE_CATEGORY: name]` | `[DELETE_CATEGORY: category_id]`\n"
            "**Permissions:** `[SET_PERM: channel_id, target_id, type=role|member, allow=perm1+perm2, deny=perm3]`\n"
            "  Available perms: send_messages, read_messages, manage_messages, manage_channels, "
            "manage_roles, kick_members, ban_members, attach_files, embed_links, mention_everyone, "
            "add_reactions, connect, speak, mute_members, deafen_members, move_members, view_channel, administrator\n"
            "**Members:** `[KICK: user_id, reason]` | `[BAN: user_id, reason, delete_days=0]` | "
            "`[UNBAN: user_id]` | `[TIMEOUT: user_id, minutes, reason]` | `[SET_NICKNAME: user_id, nickname]`\n"
            "Only use admin actions when explicitly requested. Always confirm destructive actions first."
        )

    # ─────────────────────────────────────────────
    # REFLECTION (query phase)
    # ─────────────────────────────────────────────

    async def execute_reflection(self, response: str, message) -> Optional[str]:
        if not message:
            return None
        guild = message.guild
        if not guild:
            return None

        parts = []

        if re.search(r'\[LIST_ROLES\]', response, re.IGNORECASE):
            roles_info = []
            for r in guild.roles:
                if r.name == "@everyone":
                    continue
                color = str(r.color) if r.color.value else "none"
                roles_info.append(f"- {r.name} (ID: {r.id}, color: {color}, hoist: {r.hoist}, mentionable: {r.mentionable})")
            parts.append("### SERVER ROLES:\n" + "\n".join(roles_info))

        if re.search(r'\[LIST_CHANNELS\]', response, re.IGNORECASE):
            channels_info = []
            for c in sorted(guild.channels, key=lambda x: (str(x.type), x.name)):
                cat = c.category.name if getattr(c, 'category', None) else "No category"
                channels_info.append(f"- #{c.name} (ID: {c.id}, type: {str(c.type).split('.')[-1]}, category: {cat})")
            parts.append("### SERVER CHANNELS:\n" + "\n".join(channels_info))

        if re.search(r'\[LIST_MEMBERS\]', response, re.IGNORECASE):
            members_info = [
                f"- {m.display_name} (ID: {m.id}, top_role: {m.top_role.name}, joined: {m.joined_at.strftime('%Y-%m-%d') if m.joined_at else 'unknown'})"
                for m in guild.members[:50]
            ]
            parts.append("### SERVER MEMBERS (first 50):\n" + "\n".join(members_info))

        if re.search(r'\[LIST_CATEGORIES\]', response, re.IGNORECASE):
            cats_info = []
            for cat in guild.categories:
                channels_under = [f"  - #{c.name} (ID: {c.id})" for c in cat.channels]
                cats_info.append(f"- {cat.name} (ID: {cat.id}):\n" + "\n".join(channels_under))
            parts.append("### SERVER CATEGORIES:\n" + "\n".join(cats_info))

        if re.search(r'\[LIST_BANS\]', response, re.IGNORECASE):
            try:
                bans = [entry async for entry in guild.bans()]
                bans_info = [f"- {b.user.display_name} (ID: {b.user.id}, reason: {b.reason or 'none'})" for b in bans]
                parts.append("### BANNED USERS:\n" + ("\n".join(bans_info) if bans_info else "No bans."))
            except Exception as e:
                parts.append(f"### BANNED USERS: Error fetching bans: {e}")

        for m_tag in re.finditer(r'\[GET_MEMBER:\s*(\d+)\]', response, re.IGNORECASE):
            member = guild.get_member(int(m_tag.group(1)))
            if member:
                roles = ", ".join(r.name for r in member.roles if r.name != "@everyone")
                joined = member.joined_at.strftime('%Y-%m-%d %H:%M') if member.joined_at else "unknown"
                info = (
                    f"### MEMBER INFO ({member.display_name}):\n"
                    f"- ID: {member.id}\n"
                    f"- Username: {member.name}\n"
                    f"- Nickname: {member.nick or 'none'}\n"
                    f"- Top Role: {member.top_role.name}\n"
                    f"- All Roles: {roles}\n"
                    f"- Joined: {joined}\n"
                    f"- Bot: {member.bot}"
                )
                parts.append(info)
            else:
                parts.append(f"### MEMBER INFO: Member {m_tag.group(1)} not found.")

        for r_tag in re.finditer(r'\[GET_ROLE:\s*(\d+)\]', response, re.IGNORECASE):
            role = guild.get_role(int(r_tag.group(1)))
            if role:
                key_perms = [p for p, v in iter(role.permissions) if v]
                members_with = [m.display_name for m in guild.members if role in m.roles][:20]
                info = (
                    f"### ROLE INFO ({role.name}):\n"
                    f"- ID: {role.id}\n"
                    f"- Color: {role.color}\n"
                    f"- Hoist: {role.hoist} | Mentionable: {role.mentionable}\n"
                    f"- Key Permissions: {', '.join(key_perms) or 'none'}\n"
                    f"- Members with this role ({len(members_with)}): {', '.join(members_with)}"
                )
                parts.append(info)
            else:
                parts.append(f"### ROLE INFO: Role {r_tag.group(1)} not found.")

        if not parts:
            return None

        injection = "\n\n".join(parts)
        injection += (
            "\n\n### MANDATORY INSTRUCTIONS:\n"
            "1. Use the data above to complete the user's request.\n"
            "2. Do NOT repeat query tags — the data is already FETCHED."
        )
        return injection

    # ─────────────────────────────────────────────
    # ACTION (execution phase)
    # ─────────────────────────────────────────────

    async def execute_action(self, response: str, message: Any) -> Tuple[str, Dict[str, Any]]:
        guild = getattr(message, 'guild', None) if message else None
        cleaned = response

        # Remove all query tags regardless of guild availability
        cleaned = re.sub(
            r'\[(?:LIST_ROLES|LIST_CHANNELS|LIST_MEMBERS|LIST_CATEGORIES|LIST_BANS|GET_MEMBER|GET_ROLE):?[^\]]*\]',
            '', cleaned, flags=re.IGNORECASE
        )

        if not guild:
            # Remove all action tags too
            cleaned = re.sub(
                r'\[(?:CREATE_ROLE|DELETE_ROLE|EDIT_ROLE|ASSIGN_ROLE|REMOVE_ROLE|'
                r'CREATE_CHANNEL|DELETE_CHANNEL|EDIT_CHANNEL|MOVE_CHANNEL|'
                r'CREATE_CATEGORY|DELETE_CATEGORY|SET_PERM|'
                r'KICK|BAN|UNBAN|TIMEOUT|SET_NICKNAME):?[^\]]*\]',
                '', cleaned, flags=re.IGNORECASE
            )
            return cleaned.strip(), {}

        # ── ROLES ──────────────────────────────

        for m in re.finditer(r'\[CREATE_ROLE:\s*(.*?)\]', cleaned, re.IGNORECASE):
            try:
                await guild.create_role(name=m.group(1).strip())
                print(f"[AdminSkill] Created role: {m.group(1).strip()}")
            except Exception as e:
                print(f"[AdminSkill] CREATE_ROLE failed: {e}")
        cleaned = re.sub(r'\[CREATE_ROLE:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[DELETE_ROLE:\s*(\d+)\]', cleaned, re.IGNORECASE):
            role = guild.get_role(int(m.group(1)))
            if role:
                try:
                    await role.delete()
                    print(f"[AdminSkill] Deleted role: {role.name}")
                except Exception as e:
                    print(f"[AdminSkill] DELETE_ROLE failed: {e}")
        cleaned = re.sub(r'\[DELETE_ROLE:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[EDIT_ROLE:\s*(\d+),\s*(.*?)\]', cleaned, re.IGNORECASE):
            role = guild.get_role(int(m.group(1)))
            if role:
                args = _parse_named_args(m.group(2))
                kwargs = {}
                if 'name' in args:
                    kwargs['name'] = args['name']
                if 'color' in args:
                    try:
                        kwargs['color'] = discord.Color(int(args['color'].lstrip('#'), 16))
                    except ValueError:
                        pass
                if 'hoist' in args:
                    kwargs['hoist'] = args['hoist'].lower() == 'true'
                if 'mentionable' in args:
                    kwargs['mentionable'] = args['mentionable'].lower() == 'true'
                try:
                    await role.edit(**kwargs)
                    print(f"[AdminSkill] Edited role: {role.name} → {kwargs}")
                except Exception as e:
                    print(f"[AdminSkill] EDIT_ROLE failed: {e}")
        cleaned = re.sub(r'\[EDIT_ROLE:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[ASSIGN_ROLE:\s*(\d+),\s*(\d+)\]', cleaned, re.IGNORECASE):
            member = guild.get_member(int(m.group(1)))
            role = guild.get_role(int(m.group(2)))
            if member and role:
                try:
                    await member.add_roles(role)
                    print(f"[AdminSkill] Assigned role {role.name} to {member.display_name}")
                except Exception as e:
                    print(f"[AdminSkill] ASSIGN_ROLE failed: {e}")
        cleaned = re.sub(r'\[ASSIGN_ROLE:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[REMOVE_ROLE:\s*(\d+),\s*(\d+)\]', cleaned, re.IGNORECASE):
            member = guild.get_member(int(m.group(1)))
            role = guild.get_role(int(m.group(2)))
            if member and role:
                try:
                    await member.remove_roles(role)
                    print(f"[AdminSkill] Removed role {role.name} from {member.display_name}")
                except Exception as e:
                    print(f"[AdminSkill] REMOVE_ROLE failed: {e}")
        cleaned = re.sub(r'\[REMOVE_ROLE:.*?\]', '', cleaned, flags=re.IGNORECASE)

        # ── CHANNELS ───────────────────────────

        for m in re.finditer(r'\[CREATE_CHANNEL:\s*(.*?),\s*(text|voice|forum|stage)(?:,\s*category_id=(\d+))?\]', cleaned, re.IGNORECASE):
            name, ch_type = m.group(1).strip(), m.group(2).strip().lower()
            cat_id = m.group(3)
            category = guild.get_channel(int(cat_id)) if cat_id else None
            try:
                if ch_type == "voice":
                    await guild.create_voice_channel(name=name, category=category)
                elif ch_type == "forum":
                    await guild.create_forum(name=name, category=category)
                elif ch_type == "stage":
                    await guild.create_stage_channel(name=name, category=category)
                else:
                    await guild.create_text_channel(name=name, category=category)
                print(f"[AdminSkill] Created {ch_type} channel: {name}")
            except Exception as e:
                print(f"[AdminSkill] CREATE_CHANNEL failed: {e}")
        cleaned = re.sub(r'\[CREATE_CHANNEL:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[DELETE_CHANNEL:\s*(\d+)\]', cleaned, re.IGNORECASE):
            channel = guild.get_channel(int(m.group(1)))
            if channel:
                try:
                    await channel.delete()
                    print(f"[AdminSkill] Deleted channel: {channel.name}")
                except Exception as e:
                    print(f"[AdminSkill] DELETE_CHANNEL failed: {e}")
        cleaned = re.sub(r'\[DELETE_CHANNEL:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[EDIT_CHANNEL:\s*(\d+),\s*(.*?)\]', cleaned, re.IGNORECASE):
            channel = guild.get_channel(int(m.group(1)))
            if channel:
                args = _parse_named_args(m.group(2))
                kwargs = {}
                if 'name' in args:
                    kwargs['name'] = args['name']
                if 'topic' in args and hasattr(channel, 'topic'):
                    kwargs['topic'] = args['topic']
                if 'slowmode' in args:
                    try:
                        kwargs['slowmode_delay'] = int(args['slowmode'])
                    except ValueError:
                        pass
                if 'nsfw' in args:
                    kwargs['nsfw'] = args['nsfw'].lower() == 'true'
                try:
                    await channel.edit(**kwargs)
                    print(f"[AdminSkill] Edited channel: {channel.name} → {kwargs}")
                except Exception as e:
                    print(f"[AdminSkill] EDIT_CHANNEL failed: {e}")
        cleaned = re.sub(r'\[EDIT_CHANNEL:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[MOVE_CHANNEL:\s*(\d+),\s*(\d+)\]', cleaned, re.IGNORECASE):
            channel = guild.get_channel(int(m.group(1)))
            category = guild.get_channel(int(m.group(2)))
            if channel and isinstance(category, discord.CategoryChannel):
                try:
                    await channel.edit(category=category)
                    print(f"[AdminSkill] Moved #{channel.name} to {category.name}")
                except Exception as e:
                    print(f"[AdminSkill] MOVE_CHANNEL failed: {e}")
        cleaned = re.sub(r'\[MOVE_CHANNEL:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[CREATE_CATEGORY:\s*(.*?)\]', cleaned, re.IGNORECASE):
            try:
                await guild.create_category(name=m.group(1).strip())
                print(f"[AdminSkill] Created category: {m.group(1).strip()}")
            except Exception as e:
                print(f"[AdminSkill] CREATE_CATEGORY failed: {e}")
        cleaned = re.sub(r'\[CREATE_CATEGORY:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[DELETE_CATEGORY:\s*(\d+)\]', cleaned, re.IGNORECASE):
            channel = guild.get_channel(int(m.group(1)))
            if channel:
                try:
                    await channel.delete()
                    print(f"[AdminSkill] Deleted category: {channel.name}")
                except Exception as e:
                    print(f"[AdminSkill] DELETE_CATEGORY failed: {e}")
        cleaned = re.sub(r'\[DELETE_CATEGORY:.*?\]', '', cleaned, flags=re.IGNORECASE)

        # ── PERMISSIONS ────────────────────────

        for m in re.finditer(
            r'\[SET_PERM:\s*(\d+),\s*(\d+),\s*type=(role|member)(?:,\s*allow=([^,\]]+))?(?:,\s*deny=([^\]]+))?\]',
            cleaned, re.IGNORECASE
        ):
            channel = guild.get_channel(int(m.group(1)))
            target_id = int(m.group(2))
            target_type = m.group(3).lower()
            allow_str = m.group(4) or ""
            deny_str = m.group(5) or ""

            target = guild.get_role(target_id) if target_type == "role" else guild.get_member(target_id)
            if channel and target:
                allow_perms = _parse_perms(allow_str) if allow_str else discord.Permissions()
                deny_perms = _parse_perms(deny_str) if deny_str else discord.Permissions()
                try:
                    overwrite = discord.PermissionOverwrite.from_pair(allow_perms, deny_perms)
                    await channel.set_permissions(target, overwrite=overwrite)
                    print(f"[AdminSkill] Set permissions on #{channel.name} for {target}")
                except Exception as e:
                    print(f"[AdminSkill] SET_PERM failed: {e}")
        cleaned = re.sub(r'\[SET_PERM:.*?\]', '', cleaned, flags=re.IGNORECASE)

        # ── MEMBERS ────────────────────────────

        for m in re.finditer(r'\[KICK:\s*(\d+),\s*(.*?)\]', cleaned, re.IGNORECASE):
            member = guild.get_member(int(m.group(1)))
            if member:
                try:
                    await member.kick(reason=m.group(2).strip())
                    print(f"[AdminSkill] Kicked {member.display_name}")
                except Exception as e:
                    print(f"[AdminSkill] KICK failed: {e}")
        cleaned = re.sub(r'\[KICK:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[BAN:\s*(\d+),\s*(.*?)(?:,\s*delete_days=(\d+))?\]', cleaned, re.IGNORECASE):
            member = guild.get_member(int(m.group(1)))
            if member:
                delete_days = int(m.group(3)) if m.group(3) else 0
                try:
                    await member.ban(reason=m.group(2).strip(), delete_message_days=delete_days)
                    print(f"[AdminSkill] Banned {member.display_name}")
                except Exception as e:
                    print(f"[AdminSkill] BAN failed: {e}")
        cleaned = re.sub(r'\[BAN:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[UNBAN:\s*(\d+)\]', cleaned, re.IGNORECASE):
            try:
                user = await guild.fetch_member(int(m.group(1)))
                await guild.unban(user)
                print(f"[AdminSkill] Unbanned user {m.group(1)}")
            except discord.NotFound:
                # Try fetching as user object
                try:
                    user = await guild._state._get_or_fetch_user(int(m.group(1)))
                    if user:
                        await guild.unban(user)
                        print(f"[AdminSkill] Unbanned user {m.group(1)}")
                except Exception as e:
                    print(f"[AdminSkill] UNBAN failed: {e}")
            except Exception as e:
                print(f"[AdminSkill] UNBAN failed: {e}")
        cleaned = re.sub(r'\[UNBAN:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[TIMEOUT:\s*(\d+),\s*(\d+),\s*(.*?)\]', cleaned, re.IGNORECASE):
            member = guild.get_member(int(m.group(1)))
            if member:
                try:
                    duration = datetime.timedelta(minutes=int(m.group(2)))
                    await member.timeout(duration, reason=m.group(3).strip())
                    print(f"[AdminSkill] Timed out {member.display_name} for {m.group(2)} min")
                except Exception as e:
                    print(f"[AdminSkill] TIMEOUT failed: {e}")
        cleaned = re.sub(r'\[TIMEOUT:.*?\]', '', cleaned, flags=re.IGNORECASE)

        for m in re.finditer(r'\[SET_NICKNAME:\s*(\d+),\s*(.*?)\]', cleaned, re.IGNORECASE):
            member = guild.get_member(int(m.group(1)))
            if member:
                nickname = m.group(2).strip()
                try:
                    await member.edit(nick=nickname if nickname.lower() != 'none' else None)
                    print(f"[AdminSkill] Set nickname of {member.display_name} to '{nickname}'")
                except Exception as e:
                    print(f"[AdminSkill] SET_NICKNAME failed: {e}")
        cleaned = re.sub(r'\[SET_NICKNAME:.*?\]', '', cleaned, flags=re.IGNORECASE)

        return cleaned.strip(), {}

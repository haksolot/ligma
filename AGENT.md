# L.I.G.M.A. Agent Guide

**L.I.G.M.A.** (Local Inference Gateway for Multi-model Assistants) is a modular architecture for deploying local AI agents on communication platforms (Discord, etc.) using **Ollama**.

## Project Mission
Decouple AI logic (**Core**) from communication interfaces (**Platforms**). A single "brain" maintains consistent identity, memory, and skills across multiple entry points, with full privacy via local inference.

---

## Directory Structure

### `core/` — The Brain
Platform-agnostic. Must never import from `platforms/` or `discord`.

| File | Class | Role |
|------|-------|------|
| `engine.py` | `AIEngine` | Main orchestrator: Ollama calls, system prompt assembly, logging |
| `memory.py` | `MemoryManager` | Per-channel conversation history + auto-summarization |
| `personality.py` | `PersonalityManager` | Personality text files with in-memory cache |
| `instructions.py` | `InstructionManager` | Toggleable global instruction overlays |
| `skills/base.py` | `BaseSkill` | Abstract base for all skills |
| `skills/manager.py` | `SkillManager` | Skill registry, reflection loop, action loop |
| `skills/search.py` | `SearchSkill` | Web search via DuckDuckGo (`[SEARCH: query]`) |
| `skills/browser.py` | `BrowserSkill` | Web page reader (`[READ: url]`) |
| `skills/gifs.py` | `GifSkill` | Giphy GIF injection (`[GIF: keywords]`) |

### `platforms/discord/` — The Discord Interface

| File | Role |
|------|------|
| `bot.py` | Bot init, skill registration, background tasks |
| `context.py` | `DiscordContextFetcher`: channel members, recent history, user info |
| `cogs/chat.py` | Message handling, slash commands `/think` `/hidden`, `on_typing` |
| `cogs/ai.py` | Slash commands `/panel` `/block` `/stop` + all management UI views |
| `skills/history.py` | `HistorySkill`: fetch channel history (`[HISTORY: N]`) |
| `skills/reactions.py` | `ReactionSkill`: add emoji reactions (`[REACT: emoji, msg_id]`) |
| `skills/replies.py` | `ReplySkill`: reply to specific messages (`[REPLY: msg_id]`) |
| `skills/search_history.py` | `SearchHistorySkill`: search channel history (`[DISCORD_SEARCH: query]`) |
| `skills/admin.py` | `AdminSkill`: full server admin toolbox (see below) |

---

## Skill System

Every skill extends `BaseSkill` and operates in two phases:

### Phase 1 — `execute_reflection(response, message)`
Called **after each LLM call**, before the response is sent. If the AI emitted a skill tag:
1. The skill detects it, performs the action (web search, DB lookup, etc.)
2. Returns a context string injected back into the conversation
3. The LLM is re-queried with this new context

### Phase 2 — `execute_action(response, message)`
Called **on the final response**. Cleans skill tags from the text and executes side effects (send GIF, add reaction, kick member, etc.).

**Critical:** `message` can be `None` when a skill is invoked from a slash command context (`/think`, `/hidden`). Always guard:
```python
async def execute_reflection(self, response: str, message) -> Optional[str]:
    if not message:
        return None
```

### Reflection loop (in `chat.py`)
```
LLM call → run_reflections() → if triggered: inject context + re-call LLM (max 2 steps)
         → run_actions() → clean tags, execute side effects → send response
```

---

## All Skill Tags

### Core Skills

| Skill | Tag | Phase |
|-------|-----|-------|
| SearchSkill | `[SEARCH: query]` | Reflection |
| BrowserSkill | `[READ: url]` | Reflection |
| GifSkill | `[GIF: keywords]` | Action |

### Discord Skills

| Skill | Tag | Phase | Description |
|-------|-----|-------|-------------|
| HistorySkill | `[HISTORY: N]` | Reflection | Fetch last N messages (max 25) with IDs |
| ReactionSkill | `[REACT: emoji, target_id]` | Action | Add reaction to a message |
| ReplySkill | `[REPLY: target_id]` | Action | Reply to a specific message by ID |
| SearchHistorySkill | `[DISCORD_SEARCH: query]` | Reflection | Full-text search in channel history (100 messages, 15 results) |
| AdminSkill | See table below | Both | Full server admin |

### AdminSkill Tags

**Query tags (reflection phase — fetch data, inject into context):**

| Tag | Returns |
|-----|---------|
| `[LIST_ROLES]` | All roles with ID, color, hoist, mentionable |
| `[LIST_CHANNELS]` | All channels with ID, type, category |
| `[LIST_MEMBERS]` | First 50 members with ID, top role, join date |
| `[LIST_CATEGORIES]` | All categories and their child channels |
| `[LIST_BANS]` | Banned users with reason |
| `[GET_MEMBER: user_id]` | Full member info (roles, joined, nickname, bot status) |
| `[GET_ROLE: role_id]` | Role details + list of members with this role |

**Action tags (execution phase — mutate server state):**

Roles:
- `[CREATE_ROLE: name]`
- `[DELETE_ROLE: role_id]`
- `[EDIT_ROLE: role_id, name=..., color=hex, hoist=true|false, mentionable=true|false]`
- `[ASSIGN_ROLE: user_id, role_id]`
- `[REMOVE_ROLE: user_id, role_id]`

Channels:
- `[CREATE_CHANNEL: name, text|voice|forum|stage, category_id=optional]`
- `[DELETE_CHANNEL: channel_id]`
- `[EDIT_CHANNEL: channel_id, name=..., topic=..., slowmode=N, nsfw=true|false]`
- `[MOVE_CHANNEL: channel_id, category_id]`
- `[CREATE_CATEGORY: name]`
- `[DELETE_CATEGORY: category_id]`

Permissions:
- `[SET_PERM: channel_id, target_id, type=role|member, allow=perm1+perm2, deny=perm3]`
  - Available permission names: `send_messages`, `read_messages`, `manage_messages`, `manage_channels`, `manage_roles`, `kick_members`, `ban_members`, `attach_files`, `embed_links`, `mention_everyone`, `add_reactions`, `connect`, `speak`, `mute_members`, `deafen_members`, `move_members`, `view_channel`, `administrator`

Members:
- `[KICK: user_id, reason]`
- `[BAN: user_id, reason, delete_days=0]`
- `[UNBAN: user_id]`
- `[TIMEOUT: user_id, minutes, reason]`
- `[SET_NICKNAME: user_id, nickname]`

---

## Slash Commands (Discord)

5 commands total. All management is accessible through `/panel`.

| Command | Visibility | Description |
|---------|------------|-------------|
| `/panel` | Creator only | Unified interactive control panel (model, memory, personality, instructions, skills, stats) |
| `/block` | Creator only | Toggle message handling on/off (all non-creator interactions blocked) |
| `/stop` | Creator only | Cancel the active AI generation in the current channel |
| `/think [prompt]` | Public | Ask the AI to reason step-by-step; reasoning shown as a Discord spoiler `\|\|...\|\|` |
| `/hidden [prompt] [private]` | Public | Prompt without showing the message in channel history |

### Message Triggering Logic (non-slash)
The bot responds to a message if any of these conditions are true:
1. Bot is explicitly mentioned (`@BotName`)
2. Bot's name or display name appears in the message
3. Message is a reply to one of the bot's messages
4. Same user sent a message within 45 seconds of the last interaction (followup)
5. User starts typing after the bot responded (resets the 45-second window via `on_typing`)

---

## Key Flows

### Standard message flow
```
on_message → detect trigger conditions → asyncio.Task(_do_response)
  → get_ai_response(channel, author, content, trigger_message)
    → memory.add_message(user)
    → AIEngine.chat() [1st call]
    → skills.run_reflections() [up to 2 loops]
    → skills.run_actions()
    → send response, update last_interactions, memory.add_message(assistant)
```

### `/stop` cancellation
`on_message` wraps `_do_response` in an `asyncio.Task` stored in `ChatCog.active_tasks[channel_id]`. `/stop` calls `task.cancel()`, which raises `CancelledError` at the next `await` inside the task.

### Block gate
`ChatCog.on_message`, `on_reaction_add`, `hidden_chat`, and `think` all check `bot.is_blocked` at the start. If `True`, any user other than `CREATOR_ID` is silently ignored.

---

## Configuration (`config.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | — | Bot token from Discord Developer Portal |
| `CREATOR_ID` | `0` | Discord user ID with full admin access to bot commands |
| `DEFAULT_MODEL` | `llama3.2:3b` | Default Ollama model |
| `MEMORY_LIMIT` | `10` | Messages before automatic context compression |
| `GIPHY_API_KEY` | `""` | Optional — required for GIF skill |

---

## How to Extend

### Add a skill
See `CONTRIBUTING.md → Adding a Skill`.

### Add a platform
See `CONTRIBUTING.md → Adding a Platform`.

### Modify memory behavior
Edit `core/memory.py`. The `compress()` method controls what gets summarized and what is kept. The summary prompt is inside `compress()` and can be tuned for your use case.

---

*This document is the primary reference for contributors and AI coding agents working on L.I.G.M.A.*

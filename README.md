# L.I.G.M.A.
### Local Inference Gateway for Multi-model Assistants

A modular framework for deploying local AI agents on communication platforms. L.I.G.M.A. decouples AI logic from platform interfaces, letting a single locally-hosted brain maintain consistent identity, memory, and capabilities across multiple endpoints — with zero data leaving your machine.

---

## How It Works

```
Discord / Telegram / any platform
          ↓
    Platform Layer  (platforms/)
          ↓
       AI Engine     (core/engine.py)
          ↓
  Ollama OR OpenRouter  (local/cloud inference)
```

The **Core** handles LLM orchestration, memory management, and skills. The **Platform layer** handles protocol-specific I/O. Neither knows about the other's internals.

---

## Features

- **Local OR Cloud inference** — use [Ollama](https://ollama.com) for 100% local inference, or [OpenRouter](https://openrouter.ai) for cloud models — switch at runtime
- **Persistent memory** with automatic context compression per conversation channel
- **Skill system** — extensible capabilities the AI can invoke autonomously using tag syntax
- **Hot-swappable models** — switch models at runtime without restarting (works for both Ollama and OpenRouter)
- **Hot-swappable providers** — switch between Ollama and OpenRouter on the fly
- **Dynamic personalities and instructions** — per-deployment behavioral profiles
- **Full Discord admin capabilities** — the AI can manage roles, channels, permissions, and members

---

## Skill System

Skills are modular capabilities the AI invokes autonomously by emitting special tags in its responses. Each skill has a two-phase lifecycle: a **reflection phase** (fetch data, re-query the model) and an **action phase** (clean tags, execute side effects).

| Skill | Tag | What it does |
|-------|-----|--------------|
| Web Search | `[SEARCH: query]` | DuckDuckGo real-time search |
| Browser | `[READ: url]` | Fetch and read a web page |
| GIF | `[GIF: keywords]` | Attach a Giphy GIF to the response |
| Discord History | `[HISTORY: N]` | Fetch the last N messages with IDs |
| Discord Search | `[DISCORD_SEARCH: query]` | Full-text search in channel history |
| Reactions | `[REACT: emoji, msg_id]` | Add an emoji reaction to a message |
| Replies | `[REPLY: msg_id]` | Reply to a specific past message |
| Admin | `[LIST_ROLES]`, `[KICK: ...]`, ... | Full Discord server administration |

---

## Discord Commands

Six slash commands. All management goes through `/panel`.

| Command | Access | Description |
|---------|--------|-------------|
| `/panel` | Creator | Interactive control panel — model, memory, personality, instructions, skills, stats |
| `/block` | Creator | Toggle on/off (non-creator messages ignored while blocked) |
| `/stop` | Creator | Cancel the active generation in the current channel |
| `/provider` | Creator | View current provider/model or switch between `ollama` and `openrouter` |
| `/think [prompt]` | Everyone | AI reasons step-by-step; reasoning hidden in a spoiler |
| `/hidden [prompt]` | Everyone | Send a prompt without it appearing in the channel history |

### Natural Conversation Triggers
Outside of slash commands, the bot responds when:
- It is mentioned by `@name`
- Its name appears in the message
- The message is a reply to one of its messages
- The same user sends a follow-up within 45 seconds
- The user starts typing after the bot responded (auto-extends the follow-up window)

---

## Discord Admin Capabilities

When granted the appropriate server permissions, the AI can autonomously perform server administration. A few examples:

- **Roles**: create, delete, edit (name, color, permissions, hoist), assign/remove from members
- **Channels**: create (text, voice, forum, stage), delete, edit (topic, slowmode, NSFW), move to category
- **Permissions**: set channel permission overrides per role or member
- **Members**: kick, ban, unban, timeout, change nickname

The bot will ask for confirmation before destructive actions.

---

## Installation

See **[INSTALL.md](INSTALL.md)** for the full step-by-step guide.

**Quick start:**
```bash
git clone https://github.com/haksolot/ligma.git
cd ligma
uv sync
cp .env.example .env   # fill in your tokens
uv run run.py
```

**`.env` reference:**
```env
DISCORD_TOKEN=your_discord_bot_token
CREATOR_ID=your_discord_user_id

# LLM Provider: "ollama" (local) or "openrouter" (cloud)
LLM_PROVIDER=ollama
DEFAULT_MODEL=llama3.2:3b

# OpenRouter settings (only needed if LLM_PROVIDER=openrouter)
OPENROUTER_API_KEY=sk-or-v1-...
# Optional: custom base URL for OpenRouter-compatible APIs
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

MEMORY_LIMIT=10
GIPHY_API_KEY=           # optional
```

### Using OpenRouter

To use cloud models via OpenRouter instead of local Ollama:

1. Get an API key from [openrouter.ai/keys](https://openrouter.ai/keys)
2. Set in your `.env`:
   ```
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=sk-or-v1-...
   DEFAULT_MODEL=openai/gpt-4o
   ```
3. Run the bot — it will automatically use OpenRouter

**Available OpenRouter models** include:
- `openai/gpt-4o` — OpenAI GPT-4 Omni
- `anthropic/claude-3.5-sonnet` — Anthropic Claude
- `google/gemini-2.0-flash` — Google Gemini
- `meta-llama/llama-3.1-70b-instruct` — Meta Llama
- And many more via [openrouter.ai/models](https://openrouter.ai/models)

**Switching providers at runtime** (creator only):
- `/provider status` — see current provider and model
- `/provider ollama` — switch to local Ollama
- `/provider openrouter` — switch to OpenRouter

---

## Project Structure

```
ligma/
├── core/                   # Platform-agnostic AI logic
│   ├── engine.py           # LLM orchestration (multi-provider)
│   ├── providers/          # LLM provider implementations
│   │   ├── base.py         # Provider abstraction
│   │   ├── ollama_provider.py
│   │   └── openrouter_provider.py
│   ├── memory.py           # Per-channel history + compression
│   ├── personality.py      # Personality management
│   ├── instructions.py     # Toggleable instruction overlays
│   └── skills/            # Base skill system + core skills
├── platforms/
│   └── discord/           # Discord implementation
│       ├── bot.py         # Bot init + skill registration
│       ├── context.py     # Channel context utilities
│       ├── cogs/          # Slash commands and event handlers
│       └── skills/        # Discord-specific skills
├── personalities/          # Personality text files
├── instructions/           # Instruction text files
├── config.py               # Environment variable loader
└── run.py                  # Entry point
```
ligma/
├── core/                   # Platform-agnostic AI logic
│   ├── engine.py           # LLM orchestration (Ollama)
│   ├── memory.py           # Per-channel history + compression
│   ├── personality.py      # Personality management
│   ├── instructions.py     # Toggleable instruction overlays
│   └── skills/             # Base skill system + core skills
├── platforms/
│   └── discord/            # Discord implementation
│       ├── bot.py          # Bot init + skill registration
│       ├── context.py      # Channel context utilities
│       ├── cogs/           # Slash commands and event handlers
│       └── skills/         # Discord-specific skills
├── personalities/          # Personality text files
├── instructions/           # Instruction text files
├── config.py               # Environment variable loader
└── run.py                  # Entry point
```

---

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for branch naming, commit conventions, skill development guide, and AI agent guidelines.

---

*Built by [Haksolot](https://github.com/haksolot).*

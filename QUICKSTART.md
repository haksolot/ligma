# Quickstart Guide

This guide walks you through setting up L.I.G.M.A. with a Discord bot from scratch.

---

## Prerequisites

Make sure the following are installed before continuing.

### uv
A fast Python package and project manager. Install it from **https://docs.astral.sh/uv/getting-started/installation/**

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Ollama
The local model runner. Download it from **https://ollama.com/download**

Once installed, pull the recommended model. It is small enough to run on most personal hardware:

```bash
ollama pull gemma4:e2b
```

> You can use any other Ollama model. Larger models will give better results but require more RAM/VRAM.

### Clone the repository

```bash
git clone https://github.com/haksolot/ligma.git
cd ligma
```

Install dependencies:

```bash
uv sync
```

---

## Step 1 — Create a Discord Application

Go to the **Discord Developer Portal**: **https://discord.com/developers/applications**

1. Click **New Application**
2. Give your bot a **name**, a **description**, and optionally an **avatar**
3. Click **Create**

---

## Step 2 — Configure Bot Intents

In the left sidebar, go to **Bot**.

Scroll down to **Privileged Gateway Intents** and enable all three:

- **Presence Intent**
- **Server Members Intent**
- **Message Content Intent**

Click **Save Changes**.

---

## Step 3 — Get Your Bot Token

Still in the **Bot** section, click **Reset Token** and copy the token that appears.

> Keep this token secret. Anyone with it can control your bot.

---

## Step 4 — Invite the Bot to Your Server

In the left sidebar, go to **OAuth2 → URL Generator**.

Under **Scopes**, check:
- `bot`
- `applications.commands`

Under **Bot Permissions**, check:
- `Administrator`

Copy the generated URL at the bottom of the page, open it in your browser, and invite the bot to your server.

---

## Step 5 — Configure the Project

Copy the example env file:

```bash
cp .env.example .env
```

Open `.env` and fill in the values:

```env
# Required
DISCORD_TOKEN=your_bot_token_here
CREATOR_ID=your_discord_user_id

# Model (must match an installed Ollama model)
DEFAULT_MODEL=gemma4:e2b

# Optional
MEMORY_LIMIT=10
GIPHY_API_KEY=
```

**How to find your Discord user ID:**
In Discord, go to Settings → Advanced → enable **Developer Mode**. Then right-click your username anywhere and select **Copy User ID**.

---

## Step 6 — Run the Bot

```bash
uv run run.py
```

If everything is configured correctly, you will see:

```
Logged in as YourBotName#0000!
Ollama models loaded: gemma4:e2b
Active model: gemma4:e2b
L.I.G.M.A. is ready!
```

The bot is now online. Mention it in any channel to start a conversation.

---

## What's Next

| Action | How |
|--------|-----|
| Open the control panel | `/panel` (creator only) |
| Change the active model | `/panel` → 🤖 Model |
| Create a personality | `/panel` → 🎭 Personality → Create/Update |
| Toggle a skill | `/panel` → 🔧 Skills |
| Ask the bot to reason | `/think your question here` |
| Send a hidden prompt | `/hidden your prompt` |
| Block non-creator messages | `/block` |

For a full list of skills, commands, and architecture details, see [AGENT.md](AGENT.md).

# Contributing to L.I.G.M.A.

This document defines the standards for contributing to the project — whether you are a human developer or an AI coding agent. All contributors are expected to follow these guidelines to maintain a clean, consistent, and readable history.

---

## Table of Contents

1. [Branch Naming](#branch-naming)
2. [Commit Messages](#commit-messages)
3. [Pull Request Guidelines](#pull-request-guidelines)
4. [Code Standards](#code-standards)
5. [Adding a Skill](#adding-a-skill)
6. [Adding a Platform](#adding-a-platform)
7. [For AI Agents](#for-ai-agents)

---

## Branch Naming

Branches must follow the pattern: `<type>/<short-description>`

| Type | When to use |
|------|-------------|
| `feat` | Adding a new feature or capability |
| `fix` | Fixing a bug |
| `refactor` | Restructuring code without changing behavior |
| `docs` | Documentation only |
| `chore` | Maintenance, deps updates, config changes |

**Rules:**
- Use lowercase kebab-case (no underscores, no spaces)
- Be specific but concise (max ~40 chars)
- Never work directly on `main`

**Examples:**
```
feat/admin-skill
fix/null-message-reflection
refactor/panel-views
docs/contributing-guide
chore/update-dependencies
```

---

## Commit Messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

### Types

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructure, no behavior change |
| `docs` | Documentation |
| `chore` | Build, deps, config |
| `perf` | Performance improvement |
| `test` | Tests only |

### Scope (optional but recommended)

Use the module or area affected:

`core`, `discord`, `skill`, `memory`, `engine`, `panel`, `admin`, `chat`, `config`

### Rules

- **Subject line:** max 72 characters, imperative mood, no trailing period
- **Body:** explain *why*, not *what* — the diff shows what
- **Breaking changes:** add `BREAKING CHANGE:` in the footer

**Good examples:**
```
feat(discord): add /panel unified control dashboard

Replaces 7 individual slash commands with a single interactive
panel using Discord native components (embeds + buttons).
```

```
fix(admin): guard against null message in execute_reflection

Slash commands (e.g. /think) pass None as trigger_message to
skills. AdminSkill and SearchHistorySkill now return early when
message is None to prevent AttributeError.
```

```
feat(skill): add full Discord admin toolbox to AdminSkill

Adds SET_PERM, EDIT_ROLE, EDIT_CHANNEL, MOVE_CHANNEL, BAN,
UNBAN, TIMEOUT, SET_NICKNAME and 4 new query tags.
```

**Bad examples (avoid):**
```
update stuff          ← too vague
fixed the bug         ← past tense, no scope
WIP                   ← never commit WIP to shared branches
feat: add everything  ← not specific
```

---

## Pull Request Guidelines

### Title
Follow the same format as commit messages: `feat(scope): description`

### Description template

```markdown
## What
Short summary of what this PR does.

## Why
Motivation — what problem does it solve or what need does it address?

## Changes
- List of notable changes (files, behaviors, APIs)

## Testing
How to verify this works.
```

### Checklist before opening a PR
- [ ] Code follows the project's async/typing standards
- [ ] No platform-specific imports in `core/`
- [ ] New skills are registered in `bot.py`
- [ ] No sensitive data (tokens, keys) committed
- [ ] `AGENT.md` updated if architecture changed

---

## Code Standards

### Async everywhere
All I/O and API calls must be `async`. Use `asyncio.to_thread()` to wrap synchronous blocking calls (e.g. HTTP, disk I/O in skills).

```python
# Correct
result = await asyncio.to_thread(some_blocking_function, arg)

# Wrong
result = some_blocking_function(arg)  # blocks the event loop
```

### Type hints
Use Python type hints on all function signatures.

```python
async def execute_reflection(self, response: str, message: Any) -> Optional[str]:
```

### Error handling
- Catch specific exceptions, not bare `except:`
- Skills should log errors with `print(f"[SkillName] Action failed: {e}")` and continue — never raise from a skill's action phase
- Platform code can propagate errors up to the cog handler

### Core purity
`core/` must never import from `platforms/` or `discord`. It is platform-agnostic.

```python
# Wrong (in core/)
import discord

# Correct: pass the message object as Any and use duck typing
```

### No magic numbers
Use constants or config values. Don't hardcode limits inline.

---

## Adding a Skill

1. Create a new file:
   - Generic skill → `core/skills/<name>.py`
   - Discord-specific skill → `platforms/discord/skills/<name>.py`

2. Inherit from `BaseSkill` (`core/skills/base.py`):

```python
from core.skills.base import BaseSkill
from typing import Optional, Tuple, Dict, Any

class MySkill(BaseSkill):
    name = "MySkill"
    description = "One-line description shown in /panel."
    is_active = True

    def get_prompt_injection(self) -> str:
        # Return instruction text that tells the LLM how to use this skill.
        return "**MY_SKILL**: Use `[MY_TAG: param]` to ..."

    async def execute_reflection(self, response: str, message: Any) -> Optional[str]:
        # Called after each LLM call. Return context string if skill triggered, else None.
        if not message:  # Always guard against None (slash command context)
            return None
        ...

    async def execute_action(self, response: str, message: Any) -> Tuple[str, Dict[str, Any]]:
        # Clean tags from response and execute side effects.
        # Returns (cleaned_response, context_dict)
        cleaned = re.sub(r'\[MY_TAG:.*?\]', '', response, flags=re.IGNORECASE)
        return cleaned.strip(), {}
```

3. Register in `platforms/discord/bot.py`:

```python
from platforms.discord.skills.my_skill import MySkill
discord_skills = [..., MySkill()]
```

4. Update `AGENT.md` with the new skill's tag syntax.

---

## Adding a Platform

1. Create `platforms/<platform_name>/` with at minimum:
   - `bot.py` or equivalent entry point
   - Skills directory if platform-specific skills are needed

2. Use `AIEngine` from `core/engine.py` as the sole interface to the AI layer:

```python
from core.engine import AIEngine

engine = AIEngine(skills=my_skills)
response = await engine.chat(channel_id, user_message, extra_context=..., bot_identity=...)
```

3. Manage conversation memory via `engine.memory`:

```python
await engine.memory.add_message(channel_id, "user", content, author_name=username)
await engine.memory.add_message(channel_id, "assistant", response)
```

4. Never duplicate memory, personality, or instruction logic — always delegate to `core/`.

---

## For AI Agents

If you are an AI coding agent working on this project, follow these additional guidelines:

### Before making any changes
1. **Read `AGENT.md` first** — it describes the full architecture, the skill lifecycle, and key conventions.
2. **Read the files you are about to modify** — never edit based on assumptions.
3. **Check for existing utilities** before writing new code. Skills, context fetchers, and managers often already have what you need.

### What to avoid
- Do not add platform-specific code (discord.py imports) to `core/`
- Do not add docstrings, comments, or type annotations to code you didn't change
- Do not add fallback/compatibility shims — make the change directly
- Do not commit work-in-progress — commits should represent complete, working states
- Do not over-engineer: one responsibility per skill, one concern per file

### Skill null-safety rule
Any skill's `execute_reflection` **must** begin with:
```python
if not message:
    return None
```
Slash commands (e.g. `/think`, `/hidden`) pass `None` as `trigger_message` to the skill pipeline.

### Commit as you go
Each logical change (bug fix, new feature, refactor) should be a separate commit with a proper Conventional Commit message. Do not batch unrelated changes.

### Update documentation
If you add a skill, slash command, or change the architecture, update `AGENT.md` accordingly. Keep it as the single source of truth for contributors and future agents.

# L.I.G.M.A.
### Local Inference Gateway for Multi-model Assistants

**L.I.G.M.A.** is a modular, high-performance architecture designed for deploying local AI agents across diverse communication platforms. It provides a standardized gateway to interface with Large Language Models (LLMs) via Ollama, ensuring data privacy and architectural flexibility.

---

## Overview

L.I.G.M.A. operates as an agnostic middleware that decouples **AI Logic (Core)** from **Communication Interfaces (Platforms)**. This separation of concerns allows a single, locally-hosted "brain" to maintain consistent state, memory, and personality across multiple endpoints (Discord, Telegram, Web, etc.).

By leveraging local inference, L.I.G.M.A. guarantees that all data processing remains within the user's infrastructure, eliminating third-party API dependencies and associated privacy risks.

---

## Technical Architecture

The system is engineered for extensibility and strictly adheres to a modular design pattern:

### Core Module (`core/`)
The foundational logic of the ecosystem:
- **`engine.py`**: Fully asynchronous orchestration of LLM interactions via the Ollama API.
- **`memory.py`**: Context management system featuring short-term history and automated summarization.
- **`skills/`**: Extensible skill system including:
    - **`search.py`**: Real-time web search capability (powered by `ddgs`).
    - **`gifs.py`**: Giphy integration for visual responses.
- **`personality.py` / `instructions.py`**: Dynamic management of system prompts and behavioral profiles.

### Platform Layer (`platforms/`)
Concrete implementations for specific interfaces:
- **`discord/`**: A robust integration using `discord.py`, featuring Slash Command support, asynchronous event handling, and real-time autocompletion.

---

## Deployment Guide

### Prerequisites
- **Ollama**: Must be installed and running locally.
- **Python 3.13+**
- **uv**: Recommended for dependency management.

### 1. Repository Initialization
```bash
git clone https://github.com/haksolot/ligma.git
cd ligma
```

### 2. Dependency Management
```bash
uv sync
```

### 3. System Configuration
Create a `.env` file in the root directory and populate it with your credentials:
```env
DISCORD_TOKEN=your_token_here
CREATOR_ID=your_discord_id
DEFAULT_MODEL=llama3.2:3b
MEMORY_LIMIT=10
GIPHY_API_KEY=your_giphy_key_here
```

### 4. Execution
```bash
uv run run.py
```

---

## System Capabilities (Discord implementation)

| Command Group | Functionality |
| --- | --- |
| `/model` | Dynamic hot-swapping of the active Ollama model with autocompletion. |
| `/reset` | Volatile memory purge and context summary reset for the current channel. |
| `/personality` | Real-time management of the agent's behavioral profile. |
| `/instructions` | Global management of persistent system instructions. |
| **Search Skill** | Automatic web search via `[SEARCH: query]` syntax (powered by `ddgs`). |
| **GIF Support** | Automatic GIF injection via `[GIF: query]` syntax (Giphy API). |

---

## Privacy & Compliance

L.I.G.M.A. is built on the principle of **Zero-Data Leakage**. All inference is performed 100% locally. Users retain absolute control over model selection, memory persistence policies, and the underlying hardware utilization.

---
*Architected by Haksolot.*

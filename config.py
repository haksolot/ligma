import os
from dotenv import load_dotenv

load_dotenv()

# L.I.G.M.A. Configuration

# --- DISCORD ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CREATOR_ID = int(os.getenv("CREATOR_ID", 0))

# --- LLM PROVIDER ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2:3b")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# --- CORE LOGIC ---
MEMORY_LIMIT = int(os.getenv("MEMORY_LIMIT", 10))
PERSONALITY_FILE = "personality.txt"

# --- GIFS ---
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY", "")

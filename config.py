import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# L.I.G.M.A. Configuration

# --- DISCORD ---
# Retrieved from .env, no default provided for safety
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# The creator's Discord User ID (to restrict administrative commands)
# Converted to int, defaults to 0 if not set
CREATOR_ID = int(os.getenv('CREATOR_ID', 0))

# --- OLLAMA ---
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'llama3.2:3b')

# --- CORE LOGIC ---
MEMORY_LIMIT = int(os.getenv('MEMORY_LIMIT', 6))
PERSONALITY_FILE = "personality.txt"

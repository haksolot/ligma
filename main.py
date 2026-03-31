import sys
from platforms.discord.bot import run_bot

def main():
    """Main entry point for L.I.G.M.A."""
    print("Starting L.I.G.M.A. (Local Inference Gateway for Multi-model Assistants)")
    
    # Currently, only the Discord platform is implemented
    run_bot()

if __name__ == "__main__":
    main()

import aiohttp
import random
from config import GIPHY_API_KEY

class GiphyFetcher:
    """Utility to fetch GIFs from Giphy API."""
    
    @staticmethod
    async def get_gif_url(query: str):
        if not GIPHY_API_KEY:
            print("[Giphy] Missing GIPHY_API_KEY in .env")
            return None
            
        url = "https://api.giphy.com/v1/gifs/search"
        params = {
            "api_key": GIPHY_API_KEY,
            "q": query,
            "limit": 10,
            "rating": "g" # Safe for general audiences
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("data", [])
                        if results:
                            # Pick a random one from top 10 for variety
                            return random.choice(results)["url"]
                    else:
                        print(f"[Giphy] Error: {resp.status}")
                        return None
        except Exception as e:
            print(f"[Giphy] Request failed: {e}")
            return None
        
        return None

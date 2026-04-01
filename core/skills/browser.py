import re
import asyncio
import requests
from bs4 import BeautifulSoup
from typing import Optional, Tuple, Dict, Any
from .base import BaseSkill

class BrowserSkill(BaseSkill):
    name = "Browser"
    description = "Allows the AI to read the full content of a specific web URL."
    is_active = True

    def get_prompt_injection(self) -> str:
        return "**BROWSER**: If you have a URL and need to read its full content to answer, you MUST include `[READ: https://url.com]` in your interim response. You will receive a summary of the text content."

    async def execute_reflection(self, response: str, message: Any) -> Optional[str]:
        read_match = re.search(r'\[READ:?\s*(https?://[^\s\]]+)\]', response, re.IGNORECASE)
        if read_match:
            url = read_match.group(1).strip()
            print(f"[BrowserSkill] EXECUTION: Fetching content from '{url}'...")
            
            try:
                def fetch_content():
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    resp = requests.get(url, headers=headers, timeout=10)
                    resp.raise_for_status()
                    
                    soup = BeautifulSoup(resp.text, 'lxml')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()

                    # Get text and clean it
                    text = soup.get_text(separator=' ')
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    # Limit to ~8000 characters to stay within context (around 2000 tokens)
                    return text[:8000]

                content = await asyncio.to_thread(fetch_content)
                
                if not content:
                    return f"### BROWSER ERROR for '{url}':\nThe page seems to be empty or blocked."

                injection = f"\n\n### WEB CONTENT FROM '{url}':\n{content}\n"
                injection += "\n### MANDATORY INSTRUCTIONS:\n1. Use the content above to answer.\n2. DO NOT include another [READ: ...] tag for this URL. The reading is COMPLETE."
                print(f"[BrowserSkill] Success: Fetched {len(content)} characters.")
                return injection

            except Exception as e:
                print(f"[BrowserSkill] Error during fetch: {e}")
                return f"### SYSTEM: Browser failed to fetch the URL: {e}"
        
        return None

    async def execute_action(self, response: str, message: Any) -> Tuple[str, Dict[str, Any]]:
        was_read = bool(re.search(r'\[READ:?.*?\]', response, re.IGNORECASE))
        cleaned_response = re.sub(r'\[READ:?.*?\]', '', response, flags=re.IGNORECASE)
        return cleaned_response.strip(), {'read_performed': was_read}

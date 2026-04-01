import re
import asyncio
from typing import Optional, Tuple, Dict, Any
from .base import BaseSkill
from ddgs import DDGS

class SearchSkill(BaseSkill):
    name = "Search"
    description = "Allows the AI to search the web for real-time information."
    is_active = True

    def get_prompt_injection(self) -> str:
        import datetime
        today = datetime.date.today().strftime("%B %d, %Y")
        return f"**SEARCH**: Today is {today}. If you lack real-time info (news, current events, weather) or need to verify a fact, you MUST include `[SEARCH: your query]` in your interim response. You will then receive 5 top search results. USE THIS FOR ALL CURRENT EVENTS."

    async def execute_reflection(self, response: str, message: Any) -> Optional[str]:
        # Robust detection for typos like 'SEAARCH' and case-insensitivity
        search_match = re.search(r'\[SE+A+RCH:?\s*(.*?)\]', response, re.IGNORECASE)
        if search_match:
            query = search_match.group(1).strip()
            if not query:
                return "### SYSTEM: Search query was empty."

            print(f"[SearchSkill] EXECUTION: Searching web for '{query}'...")
            try:
                def do_search():
                    with DDGS() as ddgs:
                        # Use 'news' or standard text search for better accuracy
                        return list(ddgs.text(query, max_results=5))

                results = await asyncio.to_thread(do_search)
                
                if not results:
                    print(f"[SearchSkill] No results found for '{query}'")
                    return f"### SEARCH RESULTS for '{query}':\nNo results found on the web. Inform the user you couldn't find live data."

                formatted_results = []
                for i, r in enumerate(results, 1):
                    formatted_results.append(f"RESULT {i}:\n- Title: {r['title']}\n- Snippet: {r['body']}\n- URL: {r['href']}")
                
                injection = f"\n\n### LIVE WEB SEARCH DATA for '{query}':\n" + "\n".join(formatted_results)
                injection += "\n\n### MANDATORY INSTRUCTIONS:\n1. Use the LIVE DATA above to answer. If it contradicts your knowledge, LIVE DATA is correct.\n2. DO NOT include another [SEARCH: ...] tag for this query in your next response. The search is COMPLETE."
                print(f"[SearchSkill] Success: Injected {len(results)} results.")
                return injection

            except Exception as e:
                print(f"[SearchSkill] Error during search: {e}")
                return f"### SYSTEM: Web search failed due to an error: {e}"
        
        return None

    async def execute_action(self, response: str, message: Any) -> Tuple[str, Dict[str, Any]]:
        # Robustly remove the search tag from final output
        was_searched = bool(re.search(r'\[SE+A+RCH:?.*?\]', response, re.IGNORECASE))
        cleaned_response = re.sub(r'\[SE+A+RCH:?.*?\]', '', response, flags=re.IGNORECASE)
        return cleaned_response.strip(), {'search_performed': was_searched}

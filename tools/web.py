import urllib.parse
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from tools.base import BaseTool

# --- Web Search Tool ---
class WebSearchInput(BaseModel):
    query: str = Field(..., description="The query to search the web for.")
    max_results: int = Field(5, description="Maximum number of search results to return. Default is 5.")

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Searches the web for the given query and returns titles, links, and snippets."
    args_schema = WebSearchInput
    permission_level = "safe"

    async def execute(self, query: str, max_results: int = 5, **kwargs) -> List[Dict[str, str]]:
        # Using DuckDuckGo HTML search (no API key required, reliable scraping)
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        data = {"q": query}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, data=data, headers=headers)
                
            if response.status_code != 200:
                return [{"error": f"Search failed with HTTP status {response.status_code}"}]
                
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            
            # Find all search result nodes in DDG HTML structure
            for a_tag in soup.find_all("a", class_="result__snippet"):
                result_div = a_tag.find_parent("div", class_="result__body")
                if not result_div:
                    continue
                
                title_tag = result_div.find("a", class_="result__url")
                if not title_tag:
                    continue
                
                title = title_tag.get_text(strip=True)
                raw_href = title_tag.get("href", "")
                
                # Unquote/parse DDG link redirection if necessary
                link = raw_href
                if "uddg=" in raw_href:
                    parsed = urllib.parse.urlparse(raw_href)
                    qs = urllib.parse.parse_qs(parsed.query)
                    if "uddg" in qs:
                        link = qs["uddg"][0]
                
                snippet = a_tag.get_text(strip=True)
                
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet
                })
                
                if len(results) >= max_results:
                    break
            
            return results if results else [{"message": "No search results found."}]
            
        except Exception as e:
            return [{"error": f"Search execution failed: {str(e)}"}]

# --- Fetch Webpage Tool ---
class FetchWebpageInput(BaseModel):
    url: str = Field(..., description="The URL of the webpage to read.")
    max_length: int = Field(2000, description="Max characters to return. Default is 2000.")

class FetchWebpageTool(BaseTool):
    name = "fetch_webpage"
    description = "Downloads a webpage and extracts clean, readable text content."
    args_schema = FetchWebpageInput
    permission_level = "safe"

    async def execute(self, url: str, max_length: int = 2000, **kwargs) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                
            if response.status_code != 200:
                return f"Error: Failed to fetch webpage (HTTP Status {response.status_code})."
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove scripts, styles, nav elements, and header/footer clutter
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
                
            # Get text and clean up whitespace
            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned_text = "\n".join(lines)
            
            if len(cleaned_text) > max_length:
                return cleaned_text[:max_length] + "\n... [Content Truncated] ..."
            return cleaned_text
            
        except Exception as e:
            return f"Error fetching webpage: {str(e)}"

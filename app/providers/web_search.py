"""Web/news search provider. Stub: wire Serper or Tavily API key.

Query strategy when enabled:
  - `"<Tool>" case study site:*`
  - `"chose <Tool>" OR "deployed <Tool>" OR "using <Tool>"`
  - `"<Tool>" filetype:pdf`
Return the top N results as RawHits; the runner will fetch + verify.
"""
from ..config import SERPER_API_KEY, TAVILY_API_KEY
from .base import Provider, RawHit, SearchRequest


class WebSearchProvider:
    name = "web_search"
    source_type = "news"

    def is_configured(self) -> bool:
        return bool(SERPER_API_KEY or TAVILY_API_KEY)

    async def search(self, req: SearchRequest) -> list[RawHit]:
        # TODO: implement Serper (https://serper.dev) or Tavily call.
        return []

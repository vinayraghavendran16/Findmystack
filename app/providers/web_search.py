"""Web/news search provider backed by Serper (https://serper.dev).

Runs a small set of high-signal query templates and returns organic results
as RawHits. Candidate company extraction is left to the verifier — Serper
gives us title + snippet + link and the verifier fetches the page to decide.
"""
from __future__ import annotations

from urllib.parse import urlparse

from ..config import SERPER_API_KEY
from ._serper import serper_search
from .base import Provider, RawHit, SearchRequest


QUERY_TEMPLATES = [
    '"{tool}" case study',
    '"chose {tool}" OR "selected {tool}" OR "deployed {tool}"',
    '"powered by {tool}" OR "runs on {tool}" OR "using {tool}"',
    '"{tool}" customer story',
]

# Blocklist: the vendor's own domain and generic aggregators dominate results
# without adding third-party signal. The verifier still handles them if they
# do slip through via vendor_case_studies.
DOMAIN_BLOCKLIST = {
    "wikipedia.org", "youtube.com", "reddit.com", "quora.com",
    "amazon.com", "ebay.com", "pinterest.com",
}


def _blocked(url: str, vendor_url: str | None) -> bool:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return True
    if any(host.endswith(d) for d in DOMAIN_BLOCKLIST):
        return True
    if vendor_url:
        vhost = urlparse(vendor_url).netloc.lower().removeprefix("www.")
        if vhost and host.endswith(vhost):
            return True  # vendor's own site handled by vendor_case_studies
    return False


class WebSearchProvider:
    name = "web_search"
    source_type = "news"

    def is_configured(self) -> bool:
        return bool(SERPER_API_KEY)

    async def search(self, req: SearchRequest) -> list[RawHit]:
        seen: set[str] = set()
        hits: list[RawHit] = []
        per_query = max(5, req.max_hits_per_provider // len(QUERY_TEMPLATES))
        for template in QUERY_TEMPLATES:
            for r in await serper_search(template.format(tool=req.tool_name), num=per_query):
                link = r.get("link", "")
                if not link or link in seen or _blocked(link, req.vendor_url):
                    continue
                seen.add(link)
                snippet = r.get("snippet") or ""
                title = r.get("title") or None
                hits.append(RawHit(
                    provider=self.name,
                    source_url=link,
                    source_title=title,
                    candidate_company=None,  # verifier extracts from page text
                    raw_snippet=f"{title} — {snippet}" if title else snippet,
                ))
                if len(hits) >= req.max_hits_per_provider:
                    return hits
        return hits

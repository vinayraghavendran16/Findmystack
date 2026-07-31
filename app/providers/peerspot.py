"""PeerSpot (formerly IT Central Station) provider.

Community review site with per-product review pages that name the reviewer's
company. URL patterns vary:
  /products/<slug>-reviews
  /products/<slug>
  /categories/<cat>/reviews  (harder to target)

Less aggressive bot-blocking than G2. If it 403s we surface a diagnostic
hit so debug view explains why we returned zero.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import quote

from selectolax.parser import HTMLParser

from ..http import client
from .base import Provider, RawHit, SearchRequest

log = logging.getLogger("findmystack.peerspot")


BASE = "https://www.peerspot.com"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")


IGNORE = {
    "", "peerspot", "peerspot logo", "logo", "read review", "read more",
    "verified user", "user", "administrator", "reviewer",
    "leader", "vice president", "director", "manager", "engineer",
}

NAME_RE = re.compile(r"^[A-Z0-9][\w&.\-' ]{1,60}$")


def _clean(s: str) -> str:
    return " ".join((s or "").split()).strip()


def _looks_like_company(s: str, tool_name: str) -> bool:
    s = _clean(s)
    if not s or len(s) > 80 or len(s) < 2:
        return False
    low = s.lower()
    if low in IGNORE:
        return False
    if tool_name and low == tool_name.lower():
        return False
    return bool(NAME_RE.match(s))


def _extract(html: str, tool_name: str) -> list[str]:
    tree = HTMLParser(html)
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        s = _clean(s)
        if not _looks_like_company(s, tool_name):
            return
        if s.lower() in seen:
            return
        seen.add(s.lower())
        out.append(s)

    for sel in (
        "[itemprop='name']",
        "[class*='company']",
        "[class*='employer']",
        "[data-qa*='company']",
        ".reviewer-info__company",
    ):
        for node in tree.css(sel):
            add(node.text())

    for img in tree.css("img"):
        alt = img.attributes.get("alt") or ""
        if "logo" in alt.lower():
            alt = re.sub(r"\s+logo\s*$", "", alt, flags=re.IGNORECASE).strip()
        add(alt)

    return out


class PeerSpotProvider:
    name = "peerspot"
    source_type = "review_site"

    def is_configured(self) -> bool:
        return True

    async def search(self, req: SearchRequest) -> list[RawHit]:
        slug = _slugify(req.tool_name)
        if not slug:
            return []

        candidates = [
            f"{BASE}/products/{quote(slug)}-reviews",
            f"{BASE}/products/{quote(slug)}",
        ]

        hits: list[RawHit] = []
        blocked: list[str] = []

        async with client() as http:
            for url in candidates:
                try:
                    resp = await http.get(url)
                except Exception as e:
                    log.warning("PeerSpot fetch failed %s: %s", url, e)
                    continue
                if resp.status_code in (403, 429):
                    blocked.append(url)
                    continue
                if resp.status_code != 200:
                    continue
                if "text/html" not in resp.headers.get("content-type", ""):
                    continue

                for company in _extract(resp.text, req.tool_name):
                    hits.append(RawHit(
                        provider=self.name,
                        source_url=url,
                        source_title=f"{req.tool_name} on PeerSpot",
                        candidate_company=company,
                        raw_snippet=f"Named on {url}",
                    ))
                    if len(hits) >= req.max_hits_per_provider:
                        return hits

        if not hits and blocked:
            hits.append(RawHit(
                provider=self.name,
                source_url=blocked[0],
                source_title="PeerSpot blocked our fetch",
                candidate_company=None,
                raw_snippet="PeerSpot returned 403/429; consider a scraping vendor.",
            ))
        return hits

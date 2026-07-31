"""TrustRadius provider.

Per-product page at /products/<slug>/reviews lists the reviewer's company.
Less-aggressive blocking than G2; frequently accessible with a browser UA.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import quote

from selectolax.parser import HTMLParser

from ..http import client
from .base import Provider, RawHit, SearchRequest

log = logging.getLogger("findmystack.trustradius")


BASE = "https://www.trustradius.com"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")


IGNORE = {
    "", "trustradius", "logo", "read review",
    "verified user", "anonymous", "user",
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
        "[data-testid*='company']",
        ".reviewer__company",
    ):
        for node in tree.css(sel):
            add(node.text())

    for img in tree.css("img"):
        alt = img.attributes.get("alt") or ""
        if "logo" in alt.lower():
            alt = re.sub(r"\s+logo\s*$", "", alt, flags=re.IGNORECASE).strip()
        add(alt)

    return out


class TrustRadiusProvider:
    name = "trustradius"
    source_type = "review_site"

    def is_configured(self) -> bool:
        return True

    async def search(self, req: SearchRequest) -> list[RawHit]:
        slug = _slugify(req.tool_name)
        if not slug:
            return []

        url = f"{BASE}/products/{quote(slug)}/reviews"
        async with client() as http:
            try:
                resp = await http.get(url)
            except Exception as e:
                log.warning("TrustRadius fetch failed %s: %s", url, e)
                return []
        if resp.status_code in (403, 429):
            return [RawHit(
                provider=self.name,
                source_url=url,
                source_title="TrustRadius blocked our fetch",
                candidate_company=None,
                raw_snippet="TrustRadius returned 403/429; consider a scraping vendor.",
            )]
        if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type", ""):
            return []

        hits: list[RawHit] = []
        for company in _extract(resp.text, req.tool_name):
            hits.append(RawHit(
                provider=self.name,
                source_url=url,
                source_title=f"{req.tool_name} on TrustRadius",
                candidate_company=company,
                raw_snippet=f"Named on {url}",
            ))
            if len(hits) >= req.max_hits_per_provider:
                break
        return hits

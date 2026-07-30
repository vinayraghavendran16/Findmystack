"""G2.com provider.

Tries the product-reviews page (/products/<slug>/reviews) and the seller
profile (/sellers/<slug>). Extracts reviewer companies from the review
cards' company-name fields plus any prominent named-company mentions.

Known limitation: G2 sits behind Cloudflare and aggressively blocks
non-browser fetches. Even with a Chrome UA the first request often
returns 403 or a challenge page. If that happens, we log it so the debug
view surfaces the block instead of silently returning zero. A scraping
vendor (ScrapingBee, ZenRows, Bright Data) is the reliable fix and can be
wired here later.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import quote

from selectolax.parser import HTMLParser

from ..http import client
from .base import Provider, RawHit, SearchRequest

log = logging.getLogger("findmystack.g2")


BASE = "https://www.g2.com"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")


IGNORE = {
    "", "g2", "g2 crowd", "logo", "read review", "read reviews",
    "company logo", "profile picture", "verified user", "verified reviewer",
    "small business", "mid-market", "enterprise", "small-business",
    "administrator", "user",
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


def _extract_companies(html: str, tool_name: str) -> list[str]:
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

    # G2 review cards commonly attach a company via data attributes or
    # dedicated CSS classes; try several patterns since G2 rewrites markup.
    for sel in (
        "[data-testid*='company']",
        "[class*='reviewer-company']",
        "[class*='company-name']",
        "[itemprop='name']",
        ".company",
        ".ratings__company",
    ):
        for node in tree.css(sel):
            add(node.text())

    # Also grab image alt text from customer logos on seller pages.
    for img in tree.css("img"):
        alt = img.attributes.get("alt") or ""
        if "logo" in alt.lower() or "customer" in alt.lower():
            # Extract just the company part, e.g. "Acme Corp logo" -> "Acme Corp"
            alt = re.sub(r"\s+(logo|customer)\s*$", "", alt, flags=re.IGNORECASE).strip()
        add(alt)

    return out


class G2Provider:
    name = "g2"
    source_type = "review_site"

    def is_configured(self) -> bool:
        return True  # no API key required, though it may 403

    async def search(self, req: SearchRequest) -> list[RawHit]:
        slug = _slugify(req.tool_name)
        if not slug:
            return []

        candidates = [
            f"{BASE}/products/{quote(slug)}/reviews",
            f"{BASE}/sellers/{quote(slug)}",
        ]

        hits: list[RawHit] = []
        blocked_urls: list[str] = []

        async with client() as http:
            for url in candidates:
                try:
                    resp = await http.get(url)
                except Exception as e:
                    log.warning("G2 fetch failed %s: %s", url, e)
                    continue

                if resp.status_code in (403, 429) or "cf-chl" in resp.text[:2000]:
                    log.warning("G2 blocked %s (status=%d)", url, resp.status_code)
                    blocked_urls.append(url)
                    continue
                if resp.status_code != 200:
                    continue
                if "text/html" not in resp.headers.get("content-type", ""):
                    continue

                for company in _extract_companies(resp.text, req.tool_name):
                    hits.append(RawHit(
                        provider=self.name,
                        source_url=url,
                        source_title=f"{req.tool_name} on G2",
                        candidate_company=company,
                        raw_snippet=f"Named on {url}",
                    ))
                    if len(hits) >= req.max_hits_per_provider:
                        return hits

        # If both URLs blocked and no hits, surface a diagnostic RawHit so the
        # debug view tells you why G2 returned nothing.
        if not hits and blocked_urls:
            hits.append(RawHit(
                provider=self.name,
                source_url=blocked_urls[0],
                source_title="G2 blocked our fetch",
                candidate_company=None,
                raw_snippet=(
                    "G2 returned 403/challenge. Wire a scraping vendor "
                    "(ScrapingBee, ZenRows, Bright Data) to bypass Cloudflare."
                ),
            ))
        return hits

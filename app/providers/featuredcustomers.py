"""FeaturedCustomers.com provider.

Third-party aggregator with structured testimonials for many B2B vendors.
Each vendor lives at `/vendor/<slug>` (e.g. /vendor/algosec).

Strategy: rather than guess CSS selectors that keep drifting, we extract
EVERY candidate company name from the initial HTML — image alt text and
prominent headings — and let the verifier arbitrate. The verifier fetches
the same page and confirms each candidate against the quote text.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from selectolax.parser import HTMLParser

from ..http import client
from .base import Provider, RawHit, SearchRequest


BASE = "https://www.featuredcustomers.com"


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


IGNORE = {
    "", "logo", "logos", "company logo", "customer logo", "profile picture",
    "featuredcustomers", "featured customers", "featured customers logo",
    "read more", "case study", "case studies", "testimonial", "testimonials",
    "featured testimonials", "featured case studies", "featured customer videos",
    "review", "reviews", "video", "videos", "customer story", "success story",
    "close", "menu", "search", "next", "previous", "load more",
    "share", "facebook", "linkedin", "twitter", "youtube",
    "banner", "cover", "hero", "screenshot",
}

# Reject obvious anonymised placeholders like "Leading Energy Company",
# "Large Financial Institution", "Global Insurance Provider" — the FC page
# uses these when a customer prefers not to be named.
GENERIC_PLACEHOLDER_RE = re.compile(
    r"^(leading|large|top|major|global|premier|prominent|well[- ]known|fortune \d+)"
    r"\s+(\w+\s+){0,3}(company|provider|institution|firm|organization|corporation|bank|insurer)$",
    re.IGNORECASE,
)

NAME_RE = re.compile(r"^[A-Z0-9][\w&.\-' ]{1,60}$")


def _clean(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _strip_logo_suffix(s: str) -> str:
    return re.sub(r"\s+(logo|logos|banner|cover|screenshot)\s*$", "", s, flags=re.IGNORECASE).strip()


def _looks_like_company(s: str, tool_name: str) -> bool:
    s = _strip_logo_suffix(_clean(s))
    if not s or len(s) > 80 or len(s) < 2:
        return False
    low = s.lower()
    if low in IGNORE:
        return False
    if tool_name and low == tool_name.lower():
        return False  # the vendor itself
    if GENERIC_PLACEHOLDER_RE.match(s):
        return False
    if low.startswith("featured "):
        return False
    return bool(NAME_RE.match(s))


def _extract_companies(html: str, tool_name: str) -> list[str]:
    tree = HTMLParser(html)
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        s = _strip_logo_suffix(_clean(s))
        if not _looks_like_company(s, tool_name):
            return
        key = s.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(s)

    # Image alt attributes are the strongest signal on FeaturedCustomers —
    # each testimonial card has a customer logo whose alt is the company name.
    for img in tree.css("img"):
        add(img.attributes.get("alt") or "")

    # Also look at prominent card headings and bold company labels.
    for sel in ("h3", "h4", "h5", ".company", ".company-name", "strong"):
        for node in tree.css(sel):
            add(node.text() or "")

    return out


class FeaturedCustomersProvider:
    name = "featuredcustomers"
    source_type = "aggregator"

    def is_configured(self) -> bool:
        return True

    async def search(self, req: SearchRequest) -> list[RawHit]:
        slug = _slugify(req.tool_name)
        if not slug:
            return []
        url = f"{BASE}/vendor/{quote(slug)}"

        async with client() as http:
            try:
                resp = await http.get(url)
            except Exception:
                return []
        if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type", ""):
            return []

        hits: list[RawHit] = []
        for company in _extract_companies(resp.text, req.tool_name):
            hits.append(RawHit(
                provider=self.name,
                source_url=url,
                source_title=f"{req.tool_name} on FeaturedCustomers.com",
                candidate_company=company,
                raw_snippet=f"Named in the FeaturedCustomers listing for {req.tool_name}.",
                extra={"vendor_slug": slug},
            ))
            if len(hits) >= req.max_hits_per_provider:
                break
        return hits

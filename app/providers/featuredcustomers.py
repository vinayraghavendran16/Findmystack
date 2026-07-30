"""FeaturedCustomers.com provider.

Third-party aggregator with structured testimonials for many B2B vendors.
Each vendor lives at `/vendor/<slug>` (e.g. /vendor/algosec) and lists
30+ named customers with logos, quotes, and reviewer attributions.

Strategy:
- Slugify the tool name and fetch /vendor/<slug>.
- Parse testimonial cards; the company name lives in the logo <img alt=...>
  or in prominent card headings. Fall back to nearby text if needed.
- Return each as a RawHit with candidate_company populated so the verifier
  can confirm from the surrounding quote text.

Note: some pages paginate testimonials behind a "Load additional Testimonials"
button (AJAX). We only see what's in the initial HTML; a follow-up can add
pagination.
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
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


IGNORE_ALT = {
    "", "logo", "company logo", "customer logo",
    "featuredcustomers", "featured customers",
    "read more", "case study", "testimonial",
}


def _clean(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _looks_like_company(s: str) -> bool:
    s = _clean(s)
    if not s or len(s) > 80 or len(s) < 2:
        return False
    if s.lower() in IGNORE_ALT:
        return False
    return True


def _extract_testimonials(html: str) -> list[tuple[str, str]]:
    """Return list of (company_name, quote_snippet)."""
    tree = HTMLParser(html)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    # Common containers used by FeaturedCustomers testimonial cards. Try a
    # few selectors — the site's markup has shifted over time.
    selectors = [
        ".testimonial", "[class*='testimonial']",
        ".customer-quote", "[class*='customer-quote']",
        ".card-testimonial", "[class*='card']",
    ]

    cards = []
    for sel in selectors:
        cards = tree.css(sel)
        if cards:
            break

    for card in cards:
        # Company name: prefer the logo's alt text.
        company = ""
        img = card.css_first("img")
        if img is not None:
            company = (img.attributes.get("alt") or "").strip()
        if not _looks_like_company(company):
            # Fallback: bold or heading text inside the card.
            for tag in ("strong", "h3", "h4", "h5", ".company", ".company-name"):
                node = card.css_first(tag)
                if node is not None:
                    candidate = _clean(node.text())
                    if _looks_like_company(candidate):
                        company = candidate
                        break
        if not _looks_like_company(company):
            continue

        quote_node = (
            card.css_first("blockquote")
            or card.css_first(".quote")
            or card.css_first("p")
        )
        quote = _clean(quote_node.text()) if quote_node is not None else _clean(card.text())
        quote = quote[:400]

        key = company.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append((company, quote))

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
        for company, quote in _extract_testimonials(resp.text):
            hits.append(RawHit(
                provider=self.name,
                source_url=url,
                source_title=f"{req.tool_name} on FeaturedCustomers.com",
                candidate_company=company,
                raw_snippet=quote,
                extra={"vendor_slug": slug},
            ))
            if len(hits) >= req.max_hits_per_provider:
                break
        return hits

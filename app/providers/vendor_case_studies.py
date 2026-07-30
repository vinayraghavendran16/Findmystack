"""Generic vendor case-study crawler.

Given a vendor URL (or bare domain), try common customer/case-study paths,
fetch each, extract candidate company names, and return them as RawHits.
No API keys required — uses plain HTTP + HTML parsing.

Signal quality here is highest: the vendor is directly asserting the customer.
The verifier still confirms the exact tool/company pairing from page text.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from ..http import client
from .base import Provider, RawHit, SearchRequest


CANDIDATE_PATHS = [
    "/customers",
    "/customers/",
    "/case-studies",
    "/case-studies/",
    "/case-study",
    "/resources/case-studies",
    "/company/customers",
    "/customer-stories",
    "/success-stories",
    "/our-customers",
    "/who-uses-us",
]

STOPWORDS = {
    "case study", "case studies", "customer story", "customer stories",
    "read more", "learn more", "download", "watch now", "see how",
    "success story", "success stories", "testimonial", "testimonials",
    "resources", "customers", "our customers", "trusted by",
}


def _norm_url(vendor_url: str) -> str:
    if not vendor_url.startswith(("http://", "https://")):
        vendor_url = "https://" + vendor_url
    parsed = urlparse(vendor_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _extract_candidates(html: str, base_url: str) -> list[tuple[str, str, str | None]]:
    """Return (company_guess, source_url, snippet) tuples from a customers-index page."""
    tree = HTMLParser(html)
    out: list[tuple[str, str, str | None]] = []
    seen: set[str] = set()

    # Case-study cards commonly live in <a> tags whose text is the customer name
    # or whose alt text on the inner <img> is the customer name.
    for a in tree.css("a"):
        href = a.attributes.get("href")
        if not href:
            continue
        text = (a.text() or "").strip()
        img = a.css_first("img")
        alt = (img.attributes.get("alt", "") if img is not None else "") or ""
        alt = alt.strip()

        candidate = text if _looks_like_company(text) else (alt if _looks_like_company(alt) else "")
        if not candidate:
            continue

        abs_url = urljoin(base_url + "/", href)
        key = (candidate.lower(), abs_url)
        if key in seen:
            continue
        seen.add(key)

        # Grab a bit of surrounding context as evidence snippet.
        parent = a.parent
        snippet = None
        if parent is not None:
            ptext = " ".join((parent.text() or "").split())
            if ptext:
                snippet = ptext[:400]
        out.append((candidate, abs_url, snippet))

    return out


NAME_RE = re.compile(r"^[A-Z0-9][\w&.\- ]{1,60}$")


def _looks_like_company(s: str) -> bool:
    s = s.strip()
    if not s or len(s) > 80:
        return False
    if s.lower() in STOPWORDS:
        return False
    if any(sw in s.lower() for sw in ("read the", "watch the", "download the")):
        return False
    return bool(NAME_RE.match(s))


class VendorCaseStudyProvider:
    name = "vendor_case_studies"
    source_type = "vendor_case_study"

    def is_configured(self) -> bool:
        # Only usable when the caller supplied a vendor URL.
        return True

    async def search(self, req: SearchRequest) -> list[RawHit]:
        if not req.vendor_url:
            return []
        base = _norm_url(req.vendor_url)
        hits: list[RawHit] = []

        async with client() as http:
            for path in CANDIDATE_PATHS:
                url = base + path
                try:
                    resp = await http.get(url)
                except httpx_error():
                    continue
                if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type", ""):
                    continue
                for company, source_url, snippet in _extract_candidates(resp.text, base):
                    hits.append(RawHit(
                        provider=self.name,
                        source_url=source_url,
                        source_title=f"{req.tool_name} case study: {company}",
                        candidate_company=company,
                        raw_snippet=snippet,
                        extra={"index_page": url},
                    ))
                    if len(hits) >= req.max_hits_per_provider:
                        return hits
        return hits


def httpx_error():
    import httpx
    return (httpx.HTTPError, httpx.TimeoutException)

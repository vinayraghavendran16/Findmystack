"""Generic vendor case-study crawler.

Given a vendor URL (or bare domain), try common customer/case-study index
paths, and extract candidate company names ONLY from links whose href looks
like a specific customer page. Otherwise we drown in top-nav garbage
(products/solutions/etc.) that appears on every page.

No API keys required — plain HTTP + HTML parsing. Signal is highest here
(vendor asserts customer directly); the verifier still confirms the exact
tool/company pairing from the linked page's text.
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
    "/customer-story",
    "/success-stories",
    "/our-customers",
    "/who-uses-us",
]

# Only accept a candidate link if its href path segment matches one of
# these patterns. This is the whole point of the fix: reject product/
# solution/nav links that just happen to sit on the customers page.
CUSTOMER_HREF_RE = re.compile(
    r"/(customer[-_ ]?stor(?:y|ies)|case[-_ ]?stud(?:y|ies)|customer[s]?/[^/]+|success[-_ ]?stor(?:y|ies))/",
    re.IGNORECASE,
)

STOPWORDS = {
    "case study", "case studies", "customer story", "customer stories",
    "read more", "learn more", "download", "watch now", "see how",
    "success story", "success stories", "testimonial", "testimonials",
    "resources", "customers", "our customers", "trusted by",
    "products", "solutions", "platform", "overview", "pricing",
    "contact", "support", "documentation", "docs", "blog",
    "about", "about us", "company", "careers", "partners",
}

BAD_NAME_TOKENS = {
    "solution", "solutions", "product", "products", "platform",
    "management", "security", "software", "cloud", "network",
    "compliance", "auditing", "monitoring", "analytics",
    "policy", "policies", "operations", "response",
    "segmentation", "migration", "orchestration", "automation",
    "overview", "getting started", "how to",
}

NAME_RE = re.compile(r"^[A-Z0-9][\w&.\-' ]{1,60}$")


def _norm_url(vendor_url: str) -> str:
    if not vendor_url.startswith(("http://", "https://")):
        vendor_url = "https://" + vendor_url
    parsed = urlparse(vendor_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _looks_like_company(s: str) -> bool:
    s = (s or "").strip()
    if not s or len(s) > 80 or len(s) < 2:
        return False
    lower = s.lower()
    if lower in STOPWORDS:
        return False
    if any(bad in lower.split() for bad in BAD_NAME_TOKENS):
        return False
    if any(sw in lower for sw in ("read the", "watch the", "download the", "click here")):
        return False
    return bool(NAME_RE.match(s))


def _extract_candidates(html: str, base_url: str) -> list[tuple[str, str, str | None]]:
    """Return (company, absolute_source_url, snippet) tuples from a customers-index page.

    Only follows links whose href matches a customer/case-study URL pattern.
    """
    tree = HTMLParser(html)
    out: list[tuple[str, str, str | None]] = []
    seen: set[tuple[str, str]] = set()

    for a in tree.css("a"):
        href = a.attributes.get("href")
        if not href:
            continue
        if not CUSTOMER_HREF_RE.search(href):
            continue

        text = (a.text() or "").strip()
        img = a.css_first("img")
        alt = ((img.attributes.get("alt") if img is not None else "") or "").strip()

        # Prefer the image alt (usually the actual company name); fall back to link text.
        company = alt if _looks_like_company(alt) else (text if _looks_like_company(text) else "")
        if not company:
            continue

        abs_url = urljoin(base_url + "/", href)
        key = (company.lower(), abs_url)
        if key in seen:
            continue
        seen.add(key)

        parent = a.parent
        snippet = None
        if parent is not None:
            ptext = " ".join((parent.text() or "").split())
            if ptext:
                snippet = ptext[:400]
        out.append((company, abs_url, snippet))

    return out


class VendorCaseStudyProvider:
    name = "vendor_case_studies"
    source_type = "vendor_case_study"

    def is_configured(self) -> bool:
        return True

    async def search(self, req: SearchRequest) -> list[RawHit]:
        if not req.vendor_url:
            return []
        base = _norm_url(req.vendor_url)
        hits: list[RawHit] = []
        seen_urls: set[str] = set()

        async with client() as http:
            for path in CANDIDATE_PATHS:
                url = base + path
                try:
                    resp = await http.get(url)
                except Exception:
                    continue
                if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type", ""):
                    continue
                for company, source_url, snippet in _extract_candidates(resp.text, base):
                    if source_url in seen_urls:
                        continue
                    seen_urls.add(source_url)
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

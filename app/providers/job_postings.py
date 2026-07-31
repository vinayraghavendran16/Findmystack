"""Job-postings provider backed by Serper.

Queries the major ATS/board hosts for postings that name the tool as a
requirement, then extracts the hiring company from the URL where possible.
The verifier still confirms the (company, tool) pairing from the JD text.
"""
from __future__ import annotations

from urllib.parse import urlparse

from ..config import SERPER_API_KEY
from ._serper import serper_search
from .base import Provider, RawHit, SearchRequest


ATS_HOSTS = [
    "boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.ashbyhq.com",
    "apply.workable.com",
    "careers.smartrecruiters.com",
    "linkedin.com/jobs",
    "indeed.com",
]

QUERY_TEMPLATES = [
    '"{tool}" ({sites})',
    '"experience with {tool}" ({sites})',
]


def _sites_clause() -> str:
    return " OR ".join(f"site:{h}" for h in ATS_HOSTS)


def _company_from_url(url: str) -> str | None:
    """Extract hiring company slug from common ATS URL patterns."""
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    if host == "boards.greenhouse.io" and parts:
        return _prettify(parts[0])
    if host == "jobs.lever.co" and parts:
        return _prettify(parts[0])
    if host == "jobs.ashbyhq.com" and parts:
        return _prettify(parts[0])
    if host == "apply.workable.com" and parts:
        return _prettify(parts[0])
    if host.endswith("smartrecruiters.com") and parts:
        return _prettify(parts[0])
    return None


def _prettify(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").strip().title()


class JobPostingsProvider:
    name = "job_postings"
    source_type = "job_posting"

    def is_configured(self) -> bool:
        return bool(SERPER_API_KEY)

    async def search(self, req: SearchRequest) -> list[RawHit]:
        seen: set[str] = set()
        hits: list[RawHit] = []
        sites = _sites_clause()
        per_query = max(5, req.max_hits_per_provider // len(QUERY_TEMPLATES))
        for template in QUERY_TEMPLATES:
            q = template.format(tool=req.tool_name, sites=sites)
            for r in await serper_search(q, num=per_query):
                link = r.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                snippet = r.get("snippet") or ""
                title = r.get("title") or None
                company = _company_from_url(link)
                hits.append(RawHit(
                    provider=self.name,
                    source_url=link,
                    source_title=title,
                    candidate_company=company,
                    raw_snippet=f"{title} — {snippet}" if title else snippet,
                ))
                if len(hits) >= req.max_hits_per_provider:
                    return hits
        return hits

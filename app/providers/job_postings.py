"""Job-postings provider. Stub.

Approach when enabled: run a web-search query like
  `"<Tool>" (site:boards.greenhouse.io OR site:jobs.lever.co OR site:linkedin.com/jobs)`
then extract the hiring company from the URL/page. Reuses the web-search key.
"""
from ..config import SERPER_API_KEY, TAVILY_API_KEY
from .base import Provider, RawHit, SearchRequest


class JobPostingsProvider:
    name = "job_postings"
    source_type = "job_posting"

    def is_configured(self) -> bool:
        return bool(SERPER_API_KEY or TAVILY_API_KEY)

    async def search(self, req: SearchRequest) -> list[RawHit]:
        # TODO: search + parse hiring company from ATS URL.
        return []

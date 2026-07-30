"""LinkedIn provider. Stub.

LinkedIn blocks direct scraping. Enable via:
  - Proxycurl (https://nubela.co/proxycurl) for profile/company enrichment
  - PhantomBuster for post/skill scraping
  - Apollo.io (already integrated at the org level) for people/company data
"""
from ..config import PROXYCURL_API_KEY
from .base import Provider, RawHit, SearchRequest


class LinkedInProvider:
    name = "linkedin"
    source_type = "linkedin"

    def is_configured(self) -> bool:
        return bool(PROXYCURL_API_KEY)

    async def search(self, req: SearchRequest) -> list[RawHit]:
        # TODO: Proxycurl "search people/companies with skill/keyword" endpoint.
        return []

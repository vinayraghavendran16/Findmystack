"""Review-site provider. Stub.

G2, Gartner Peer Insights, and TrustRadius block direct scraping. Options:
  - G2 partner API (paid)
  - A scraping vendor (ScrapingBee, ZenRows, Bright Data) targeting review pages
  - Manual export CSV drop-in
The reviewer's company name is usually listed near the review body.
"""
from .base import Provider, RawHit, SearchRequest


class ReviewSitesProvider:
    name = "review_sites"
    source_type = "review_site"

    def is_configured(self) -> bool:
        return False

    async def search(self, req: SearchRequest) -> list[RawHit]:
        # TODO: wire scraping vendor or partner API.
        return []

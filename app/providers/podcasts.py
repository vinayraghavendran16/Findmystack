"""Podcast / webinar transcript provider. Stub.

Approach: search Listen Notes (podcasts) or the vendor's own webinar page for
episodes mentioning the tool; pull transcripts (Listen Notes returns them for
some feeds); LLM-extract company mentions.
"""
from .base import Provider, RawHit, SearchRequest


class PodcastsProvider:
    name = "podcasts"
    source_type = "podcast"

    def is_configured(self) -> bool:
        return False

    async def search(self, req: SearchRequest) -> list[RawHit]:
        # TODO: wire Listen Notes API or a vendor webinar crawl.
        return []

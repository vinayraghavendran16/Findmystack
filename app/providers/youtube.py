"""YouTube / conference talks provider. Stub.

Approach: YouTube Data API v3 search for `"<Tool>"`, then youtube-transcript-api
for captions, then LLM extraction of "Company X uses Tool Y" mentions.
"""
from ..config import YOUTUBE_API_KEY
from .base import Provider, RawHit, SearchRequest


class YouTubeProvider:
    name = "youtube"
    source_type = "conference_talk"

    def is_configured(self) -> bool:
        return bool(YOUTUBE_API_KEY)

    async def search(self, req: SearchRequest) -> list[RawHit]:
        # TODO: search videos + pull transcripts + entity extract.
        return []

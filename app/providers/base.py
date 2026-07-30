from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class SearchRequest:
    tool_name: str
    vendor_url: str | None = None
    max_hits_per_provider: int = 25


@dataclass
class RawHit:
    provider: str
    source_url: str
    source_title: str | None = None
    candidate_company: str | None = None
    raw_snippet: str | None = None
    extra: dict = field(default_factory=dict)


@runtime_checkable
class Provider(Protocol):
    name: str
    source_type: str  # e.g. "vendor_case_study", "news", "review_site"

    def is_configured(self) -> bool: ...

    async def search(self, req: SearchRequest) -> list[RawHit]: ...

"""Orchestrates: run all configured providers -> persist hits -> verify -> persist confirmations."""
from __future__ import annotations

import asyncio
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models
from .providers import all_providers
from .providers.base import RawHit, SearchRequest
from .verifier import verify


async def _run_provider(provider, req: SearchRequest) -> tuple[str, list[RawHit]]:
    try:
        hits = await provider.search(req)
    except Exception as e:
        return provider.name, [RawHit(
            provider=provider.name,
            source_url="",
            source_title=None,
            candidate_company=None,
            raw_snippet=f"provider error: {e}",
        )]
    return provider.name, hits


async def run_search(db: Session, tool_name: str, vendor_url: str | None) -> models.Search:
    search = models.Search(tool_name=tool_name, vendor_url=vendor_url, status="running")
    db.add(search)
    db.commit()
    db.refresh(search)

    req = SearchRequest(tool_name=tool_name, vendor_url=vendor_url)
    providers = [p for p in all_providers() if p.is_configured()]

    results = await asyncio.gather(*[_run_provider(p, req) for p in providers])

    provider_source_types = {p.name: p.source_type for p in providers}
    all_hits: list[tuple[str, RawHit]] = []
    for name, hits in results:
        for h in hits:
            if not h.source_url:
                continue
            all_hits.append((name, h))

    # Persist hits
    hit_rows: list[models.Hit] = []
    for name, h in all_hits:
        row = models.Hit(
            search_id=search.id,
            provider=name,
            source_url=h.source_url,
            source_title=h.source_title,
            candidate_company=h.candidate_company,
            raw_snippet=h.raw_snippet,
        )
        db.add(row)
        hit_rows.append(row)
    db.commit()

    # Verify in parallel, but cap concurrency to stay polite.
    sem = asyncio.Semaphore(4)

    async def _verify_one(row: models.Hit, raw: RawHit):
        async with sem:
            return row, await verify(raw, tool_name)

    verdicts = await asyncio.gather(*[
        _verify_one(row, raw) for row, (_, raw) in zip(hit_rows, all_hits)
    ])

    for row, verdict in verdicts:
        if not verdict.confirmed or verdict.confidence < 0.4:
            continue
        conf = models.Confirmation(
            hit_id=row.id,
            tool_name=tool_name,
            tool_name_norm=models.normalize(tool_name),
            company=verdict.company,
            company_norm=models.normalize(verdict.company),
            source_url=row.source_url,
            source_type=provider_source_types.get(row.provider, row.provider),
            evidence_snippet=verdict.evidence_snippet,
            confidence=verdict.confidence,
            verified=True,
            verifier_note=verdict.note,
        )
        db.add(conf)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # duplicate (tool, company, url) — fine

    search.status = "complete"
    search.notes = f"{len(hit_rows)} hits, {sum(1 for _, v in verdicts if v.confirmed)} confirmed"
    db.commit()
    db.refresh(search)
    return search

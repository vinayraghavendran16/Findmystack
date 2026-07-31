"""One-shot diagnostic. Run: python scripts/check.py

Verifies each piece of the pipeline in order so a failure tells you exactly
where things break.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import ANTHROPIC_API_KEY, SERPER_API_KEY, VERIFIER_MODEL  # noqa: E402


def status(label: str, ok: bool, detail: str = "") -> None:
    tag = "OK  " if ok else "FAIL"
    print(f"[{tag}] {label}" + (f"  ({detail})" if detail else ""))


async def check_anthropic() -> None:
    if not ANTHROPIC_API_KEY:
        status("Anthropic key present in .env", False)
        return
    status("Anthropic key present in .env", True, f"len={len(ANTHROPIC_API_KEY)}")
    try:
        from anthropic import AsyncAnthropic
        c = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        r = await c.messages.create(
            model=VERIFIER_MODEL,
            max_tokens=20,
            messages=[{"role": "user", "content": "reply with the single word: pong"}],
        )
        text = "".join(b.text for b in r.content if getattr(b, "type", None) == "text").strip()
        status(f"Anthropic API call ({VERIFIER_MODEL})", True, f"reply: {text[:40]}")
    except Exception as e:
        status(f"Anthropic API call ({VERIFIER_MODEL})", False, f"{type(e).__name__}: {e}")


async def check_serper() -> None:
    if not SERPER_API_KEY:
        status("Serper key present in .env", False)
        return
    status("Serper key present in .env", True, f"len={len(SERPER_API_KEY)}")
    from app.providers._serper import serper_search
    try:
        results = await serper_search("Snowflake case study", num=3)
        status("Serper API call", True, f"{len(results)} results")
    except Exception as e:
        status("Serper API call", False, f"{type(e).__name__}: {e}")


async def check_verifier_end_to_end() -> None:
    if not ANTHROPIC_API_KEY:
        return
    from app.providers.base import RawHit
    from app.verifier import verify
    hit = RawHit(
        provider="test",
        source_url="https://www.snowflake.com/en/customers/all-customers/",
        source_title="Snowflake customers",
        candidate_company=None,
        raw_snippet="",
    )
    v = await verify(hit, "Snowflake")
    status("Verifier end-to-end", v.confidence >= 0.0,
           f"confirmed={v.confirmed} conf={v.confidence:.2f} company={v.company!r} note={v.note!r}")


async def main() -> None:
    print(f"--- Findmystack diagnostic ---")
    print(f"VERIFIER_MODEL: {VERIFIER_MODEL}")
    print()
    await check_anthropic()
    await check_serper()
    await check_verifier_end_to_end()


if __name__ == "__main__":
    asyncio.run(main())

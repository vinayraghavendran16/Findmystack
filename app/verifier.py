"""LLM cross-check for hits.

Given a RawHit, fetch the source URL's visible text (best-effort) and ask
Claude to answer strictly whether the page actually says the named company
uses the named tool. Returns a structured verdict.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from selectolax.parser import HTMLParser

from .config import ANTHROPIC_API_KEY, VERIFIER_MODEL
from .http import client
from .providers.base import RawHit


MAX_TEXT_CHARS = 15000


@dataclass
class Verdict:
    confirmed: bool
    company: str
    evidence_snippet: str
    confidence: float
    note: str


async def fetch_visible_text(url: str) -> str:
    async with client() as http:
        try:
            resp = await http.get(url)
        except Exception:
            return ""
    if resp.status_code != 200:
        return ""
    ctype = resp.headers.get("content-type", "")
    if "text/html" not in ctype:
        return resp.text[:MAX_TEXT_CHARS]
    tree = HTMLParser(resp.text)
    for sel in ("script", "style", "noscript", "nav", "footer", "header"):
        for n in tree.css(sel):
            n.decompose()
    root = tree.body or tree.root
    text = " ".join((root.text() if root else "").split())
    return text[:MAX_TEXT_CHARS]


def _fallback_verdict(hit: RawHit, reason: str) -> Verdict:
    return Verdict(
        confirmed=False,
        company=hit.candidate_company or "",
        evidence_snippet=(hit.raw_snippet or "")[:400],
        confidence=0.0,
        note=reason,
    )


PROMPT = """You verify claims about which companies use which software tools.

TOOL: {tool}
CANDIDATE COMPANY: {company}
SOURCE URL: {url}

Below is the visible text of the source page. Decide:
1. Does this page actually state (or clearly imply through a first-party
   assertion like a case study, testimonial, press release, or job posting)
   that the CANDIDATE COMPANY uses the TOOL?
2. If yes, quote the single most direct sentence as evidence.
3. Score your confidence 0.0-1.0.

Respond with ONLY a JSON object on one line, no prose, no code fences:
{{"confirmed": true|false, "company": "...", "evidence": "...", "confidence": 0.0-1.0, "note": "short reason"}}

If the candidate company is wrong but a different company is clearly named,
set confirmed=false and put the correct company name in "note".

--- PAGE TEXT ---
{text}
--- END PAGE TEXT ---
"""


async def verify(hit: RawHit, tool_name: str) -> Verdict:
    if not ANTHROPIC_API_KEY:
        return _fallback_verdict(hit, "no ANTHROPIC_API_KEY configured; unverified")
    if not hit.candidate_company:
        return _fallback_verdict(hit, "no candidate company on hit")

    text = await fetch_visible_text(hit.source_url)
    if not text:
        return _fallback_verdict(hit, "could not fetch source text")

    from anthropic import AsyncAnthropic
    client_ = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    prompt = PROMPT.format(
        tool=tool_name,
        company=hit.candidate_company,
        url=hit.source_url,
        text=text,
    )
    try:
        msg = await client_.messages.create(
            model=VERIFIER_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        return _fallback_verdict(hit, f"verifier error: {e}")

    raw = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_verdict(hit, f"non-JSON verdict: {raw[:120]}")

    return Verdict(
        confirmed=bool(data.get("confirmed", False)),
        company=str(data.get("company") or hit.candidate_company),
        evidence_snippet=str(data.get("evidence") or "")[:800],
        confidence=float(data.get("confidence") or 0.0),
        note=str(data.get("note") or ""),
    )

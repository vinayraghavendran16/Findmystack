"""LLM cross-check for hits.

Given a RawHit, fetch the source URL's visible text (best-effort) and ask
Claude to answer strictly whether the page actually says a real company
uses the named tool. Two modes:

- Hit already has a candidate company (vendor case study, ATS URL slug):
  ask Claude to CONFIRM that specific pairing.
- Hit has no candidate (web search hit): ask Claude to EXTRACT the company
  name from the page while confirming the tool is used.
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


PROMPT_CONFIRM = """You verify claims about which companies use which software tools.

TOOL: {tool}
CANDIDATE COMPANY: {company}
SOURCE URL: {url}

Below is the visible text of the source page. Decide:
1. Does this page state (or clearly imply through a first-party assertion
   like a case study, testimonial, press release, or job posting) that the
   CANDIDATE COMPANY uses the TOOL?
2. If yes, quote the single most direct sentence as evidence.
3. Score your confidence 0.0-1.0.

Respond with ONLY a JSON object on one line, no prose, no code fences:
{{"confirmed": true|false, "company": "...", "evidence": "...", "confidence": 0.0-1.0, "note": "short reason"}}

If the candidate company is wrong but a different company is clearly named
as a user of the TOOL, set confirmed=true and put that correct company in "company".

--- PAGE TEXT ---
{text}
--- END PAGE TEXT ---
"""


PROMPT_EXTRACT = """You extract and verify claims about which companies use which software tools.

TOOL: {tool}
SOURCE URL: {url}

Below is the visible text of the source page. Decide:
1. Does this page name a specific company (not the tool vendor itself, and
   not a generic list like "Fortune 500") as a user of the TOOL?
   Accept: named customer in a case study, quoted employee, press release,
   or a job posting requiring hands-on experience with the tool (the hiring
   company is the user).
2. If yes, return the single most direct sentence as evidence and the
   company name.
3. Score your confidence 0.0-1.0.

Respond with ONLY a JSON object on one line, no prose, no code fences:
{{"confirmed": true|false, "company": "...", "evidence": "...", "confidence": 0.0-1.0, "note": "short reason"}}

If no specific customer company is named, set confirmed=false.

--- PAGE TEXT ---
{text}
--- END PAGE TEXT ---
"""


async def verify(hit: RawHit, tool_name: str) -> Verdict:
    if not ANTHROPIC_API_KEY:
        return _fallback_verdict(hit, "no ANTHROPIC_API_KEY configured; unverified")

    text = await fetch_visible_text(hit.source_url)
    if not text:
        return _fallback_verdict(hit, "could not fetch source text")

    if hit.candidate_company:
        prompt = PROMPT_CONFIRM.format(
            tool=tool_name, company=hit.candidate_company, url=hit.source_url, text=text,
        )
    else:
        prompt = PROMPT_EXTRACT.format(tool=tool_name, url=hit.source_url, text=text)

    from anthropic import AsyncAnthropic
    client_ = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
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

    company = str(data.get("company") or hit.candidate_company or "").strip()
    confirmed = bool(data.get("confirmed", False)) and bool(company)
    return Verdict(
        confirmed=confirmed,
        company=company,
        evidence_snippet=str(data.get("evidence") or "")[:800],
        confidence=float(data.get("confidence") or 0.0),
        note=str(data.get("note") or ""),
    )

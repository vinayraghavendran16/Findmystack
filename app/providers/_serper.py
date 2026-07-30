"""Shared Serper client (https://serper.dev).

One helper is enough for both the web_search and job_postings providers
since they only differ by query template.
"""
from __future__ import annotations

import httpx

from ..config import SERPER_API_KEY, HTTP_TIMEOUT, HTTP_USER_AGENT


SERPER_ENDPOINT = "https://google.serper.dev/search"


async def serper_search(query: str, num: int = 20) -> list[dict]:
    if not SERPER_API_KEY:
        return []
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": HTTP_USER_AGENT},
    ) as http:
        try:
            resp = await http.post(
                SERPER_ENDPOINT,
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": num},
            )
        except httpx.HTTPError:
            return []
    if resp.status_code != 200:
        return []
    return resp.json().get("organic", []) or []

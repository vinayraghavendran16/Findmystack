import httpx

from .config import HTTP_TIMEOUT, HTTP_USER_AGENT


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": HTTP_USER_AGENT},
    )

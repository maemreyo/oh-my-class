from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(("https", parsed.netloc.lower(), path, "", ""))


def domain_for(url: str) -> str:
    return urlsplit(url).netloc

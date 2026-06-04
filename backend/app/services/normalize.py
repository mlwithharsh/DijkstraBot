from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_username(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lstrip("@")
    if "/" in cleaned:
        cleaned = cleaned.rstrip("/").split("/")[-1]
    return cleaned.lower() or None


def normalize_profile_url(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if value.startswith("instagram.com/") or value.startswith("www.instagram.com/"):
        value = f"https://{value}"
    elif not value.startswith("http"):
        value = f"https://www.instagram.com/{value.lstrip('@').strip('/')}/"
    parsed = urlparse(value)
    path = parsed.path.split("?")[0].split("#")[0].strip("/")
    if not path:
        return None
    username = path.split("/")[0].lstrip("@").lower()
    return urlunparse(("https", "www.instagram.com", f"/{username}/", "", "", ""))


def extract_username_from_url(value: str | None) -> str | None:
    normalized = normalize_profile_url(value)
    if not normalized:
        return None
    parsed = urlparse(normalized)
    path = parsed.path.strip("/")
    return normalize_username(path.split("/")[0]) if path else None

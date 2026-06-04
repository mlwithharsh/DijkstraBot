from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.app.core.config import get_settings
from backend.app.services.apify import ApifyService
from backend.app.services.normalize import extract_username_from_url, normalize_profile_url, normalize_username


settings = get_settings()
INSTAGRAM_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?", re.IGNORECASE)


@dataclass(slots=True)
class DiscoveryHit:
    profile_url: str
    username: str
    source: str
    query: str | None = None


def extract_instagram_urls(text: str | None) -> list[str]:
    if not text:
        return []
    urls = []
    for match in INSTAGRAM_URL_RE.findall(text):
        normalized = normalize_profile_url(f"https://www.instagram.com/{match}/")
        if normalized:
            urls.append(normalized)
    return list(dict.fromkeys(urls))


class GoogleDiscoverySource:
    def __init__(self, apify: ApifyService) -> None:
        self.apify = apify

    def _build_queries(self, source: str, query: str | None = None) -> list[str]:
        if query:
            return [query]

        base = [
            'site:instagram.com inurl:"instagram.com/" India creator',
            'site:instagram.com "India" "Instagram" "followers"',
            'site:youtube.com instagram.com India creator',
        ]
        directory_queries = [
            'site:favikon.com India Instagram creator',
            'site:heepsy.com India Instagram influencer',
            'site:starngage.com India Instagram creator',
            'site:hypeauditor.com India Instagram influencer',
        ]

        if source == "google":
            return base
        if source == "directories":
            return directory_queries
        if source == "youtube":
            return [
                'site:youtube.com/channel instagram.com India creator',
                'site:youtube.com/@ instagram.com India',
                'site:youtube.com "instagram.com/" India',
            ]
        return base

    async def discover(self, source: str, query: str | None = None, max_results: int = 25) -> list[DiscoveryHit]:
        if not self.apify.is_configured():
            raise RuntimeError("APIFY_TOKEN is required for discovery")

        max_results = min(max_results, settings.apify_max_profiles_per_day)
        hits: list[DiscoveryHit] = []
        queries = self._build_queries(source, query)
        per_query_limit = max(1, min(settings.apify_google_pages_per_query, 10))

        for q in queries:
            run_input = {
                "queries": q,
                "maxPagesPerQuery": per_query_limit,
                "languageCode": "en",
                "searchLanguage": "en",
            }
            result = await self.apify.call_actor(settings.apify_google_actor, run_input, max_items=max_results * 10)
            for item in result.items:
                urls = self._extract_urls_from_search_result(item)
                for url in urls:
                    username = extract_username_from_url(url)
                    if username:
                        hits.append(DiscoveryHit(profile_url=url, username=username, source=source, query=q))
                if len(hits) >= max_results:
                    return self._dedupe(hits)[:max_results]
        return self._dedupe(hits)[:max_results]

    def _extract_urls_from_search_result(self, item: dict) -> list[str]:
        candidates = []
        for key in ("url", "link", "displayUrl", "title", "snippet", "description", "text"):
            value = item.get(key)
            if isinstance(value, str):
                candidates.extend(extract_instagram_urls(value))
        if "organicResults" in item and isinstance(item["organicResults"], list):
            for nested in item["organicResults"]:
                candidates.extend(self._extract_urls_from_search_result(nested))
        return list(dict.fromkeys(candidates))

    def _dedupe(self, hits: list[DiscoveryHit]) -> list[DiscoveryHit]:
        seen = set()
        unique: list[DiscoveryHit] = []
        for hit in hits:
            key = (hit.username, hit.profile_url)
            if key in seen:
                continue
            seen.add(key)
            unique.append(hit)
        return unique


class ManualDiscoverySource:
    def parse_urls(self, urls: list[str], source: str = "manual") -> list[DiscoveryHit]:
        hits: list[DiscoveryHit] = []
        for raw in urls:
            normalized = normalize_profile_url(str(raw))
            if not normalized:
                continue
            username = extract_username_from_url(normalized)
            if not username:
                continue
            hits.append(DiscoveryHit(profile_url=normalized, username=username, source=source))
        return self._dedupe(hits)

    def _dedupe(self, hits: list[DiscoveryHit]) -> list[DiscoveryHit]:
        seen = set()
        output = []
        for hit in hits:
            key = (normalize_username(hit.username), hit.profile_url)
            if key in seen:
                continue
            seen.add(key)
            output.append(hit)
        return output

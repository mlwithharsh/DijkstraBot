from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.config import get_settings
from backend.app.services.apify import ApifyService
from backend.app.services.classification import CategoryClassifier
from backend.app.services.country import detect_country
from backend.app.services.normalize import normalize_profile_url, normalize_username


settings = get_settings()


@dataclass(slots=True)
class EnrichedProfile:
    username: str
    profile_url: str
    full_name: str | None
    bio: str | None
    followers: int | None
    following: int | None
    posts: int | None
    displayed_category: str | None
    derived_category: str | None
    country: str | None
    email: str | None
    external_url: str | None
    verified: bool
    source: str
    confidence_score: float | None
    country_confidence: float | None


class InstagramEnrichmentService:
    def __init__(self, apify: ApifyService | None = None) -> None:
        self.apify = apify or ApifyService()
        self.classifier = CategoryClassifier()

    async def enrich_usernames(self, usernames: list[str], source: str = "manual") -> list[EnrichedProfile]:
        if not usernames:
            return []
        if not self.apify.is_configured():
            raise RuntimeError("APIFY_TOKEN is required for enrichment")

        run_input = {
            "usernames": usernames,
            "includeAboutSection": True,
        }
        result = await self.apify.call_actor(settings.apify_instagram_actor, run_input, max_items=settings.apify_instagram_profile_limit)
        output: list[EnrichedProfile] = []
        for item in result.items:
            mapped = self._map_item(item, source=source)
            if mapped:
                output.append(mapped)
        return output

    def _map_item(self, item: dict, source: str) -> EnrichedProfile | None:
        username = normalize_username(
            item.get("username")
            or item.get("handle")
            or item.get("user_name")
            or item.get("ownerUsername")
            or item.get("name")
        )
        profile_url = normalize_profile_url(
            item.get("url")
            or item.get("profile_url")
            or item.get("profileUrl")
            or (f"https://www.instagram.com/{username}/" if username else None)
        )
        if not username or not profile_url:
            return None

        bio = item.get("biography") or item.get("bio") or item.get("description")
        full_name = item.get("fullName") or item.get("full_name") or item.get("name")
        followers = self._as_int(item, ["followersCount", "followers", "follower_count"])
        following = self._as_int(item, ["followsCount", "following", "following_count"])
        posts = self._as_int(item, ["mediaCount", "postsCount", "posts", "post_count"])
        displayed_category = item.get("category") or item.get("businessCategory") or item.get("displayedCategory")
        external_url = item.get("website") or item.get("externalUrl") or item.get("external_url")
        verified = bool(item.get("isVerified") or item.get("verified") or item.get("is_verified"))
        email = item.get("email") or item.get("contactEmail")

        category_result = self.classifier.classify(f"{full_name or ''}\n{bio or ''}", displayed_category=displayed_category)
        country_result = detect_country(f"{full_name or ''}\n{bio or ''}\n{external_url or ''}")

        return EnrichedProfile(
            username=username,
            profile_url=profile_url,
            full_name=full_name,
            bio=bio,
            followers=followers,
            following=following,
            posts=posts,
            displayed_category=displayed_category,
            derived_category=category_result.category,
            country=country_result.country,
            email=email,
            external_url=external_url,
            verified=verified,
            source=source,
            confidence_score=category_result.confidence,
            country_confidence=country_result.confidence,
        )

    def _as_int(self, item: dict, keys: list[str]) -> int | None:
        for key in keys:
            value = item.get(key)
            if isinstance(value, bool) or value is None:
                continue
            try:
                return int(str(value).replace(",", "").strip())
            except ValueError:
                continue
        return None

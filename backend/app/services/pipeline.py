from __future__ import annotations

from datetime import datetime, timezone

from backend.app.repositories.influencers import InfluencerRepository
from backend.app.repositories.refresh_jobs import RefreshJobRepository
from backend.app.services.enrichment import InstagramEnrichmentService
from backend.app.services.normalize import extract_username_from_url, normalize_profile_url, normalize_username
from backend.app.services.refresh_policy import next_refresh_for_followers
from backend.app.services.discovery import DiscoveryHit


class PipelineService:
    def __init__(self, influencer_repo: InfluencerRepository, job_repo: RefreshJobRepository, enrichment: InstagramEnrichmentService) -> None:
        self.influencer_repo = influencer_repo
        self.job_repo = job_repo
        self.enrichment = enrichment

    async def store_discovery_hits(self, hits: list[DiscoveryHit], source: str) -> int:
        rows = []
        for hit in hits:
            rows.append(
                {
                    "username": normalize_username(hit.username),
                    "profile_url": normalize_profile_url(hit.profile_url),
                    "source": source,
                    "last_updated": datetime.now(timezone.utc),
                }
            )
        rows = [row for row in rows if row["username"] and row["profile_url"]]
        if not rows:
            return 0
        return await self.influencer_repo.bulk_upsert(rows)

    async def enrich_and_store_usernames(self, usernames: list[str], source: str) -> int:
        enriched = await self.enrichment.enrich_usernames(usernames, source=source)
        count = 0
        for item in enriched:
            next_refresh = next_refresh_for_followers(item.followers)
            await self.influencer_repo.upsert(
                {
                    "username": item.username,
                    "profile_url": item.profile_url,
                    "full_name": item.full_name,
                    "bio": item.bio,
                    "followers": item.followers,
                    "following": item.following,
                    "posts": item.posts,
                    "displayed_category": item.displayed_category,
                    "derived_category": item.derived_category,
                    "country": item.country,
                    "email": item.email,
                    "external_url": item.external_url,
                    "verified": item.verified,
                    "source": item.source,
                    "confidence_score": item.confidence_score,
                    "country_confidence": item.country_confidence,
                    "last_updated": datetime.now(timezone.utc),
                    "next_refresh_at": next_refresh,
                }
            )
            count += 1
        return count

    async def refresh_profile(self, profile_url: str, source: str = "manual") -> int:
        username = extract_username_from_url(profile_url)
        usernames = [username] if username else []
        return await self.enrich_and_store_usernames(usernames, source=source)

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.app.core.database import AsyncSessionLocal, engine, wait_for_database
from backend.app.models import Base
from backend.app.repositories.influencers import InfluencerRepository
from backend.app.repositories.refresh_jobs import RefreshJobRepository
from backend.app.services.apify import ApifyService
from backend.app.services.discovery import GoogleDiscoverySource, ManualDiscoverySource
from backend.app.services.enrichment import InstagramEnrichmentService
from backend.app.services.pipeline import PipelineService
from backend.app.services.normalize import extract_username_from_url
from backend.app.services.queue import RedisQueue


class Worker:
    def __init__(self) -> None:
        self.queue = RedisQueue()
        self.apify = ApifyService()

    async def ensure_schema(self) -> None:
        await wait_for_database()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def run_once(self) -> bool:
        message = await self.queue.pop(timeout=1)
        if not message:
            return False

        async with AsyncSessionLocal() as session:
            influencer_repo = InfluencerRepository(session)
            job_repo = RefreshJobRepository(session)
            pipeline = PipelineService(influencer_repo, job_repo, InstagramEnrichmentService(self.apify))

            if message.job_type == "discover_google":
                source = GoogleDiscoverySource(self.apify)
                hits = await source.discover("google", query=message.payload.get("query"), max_results=message.payload.get("max_results", 25))
                await pipeline.store_discovery_hits(hits, source="google")
                for hit in hits:
                    await self.queue.enqueue("refresh_profile", {"profile_url": hit.profile_url, "source": "google"}, priority="low")
                return True

            if message.job_type == "discover_directories":
                source = GoogleDiscoverySource(self.apify)
                hits = await source.discover("directories", query=message.payload.get("query"), max_results=message.payload.get("max_results", 25))
                await pipeline.store_discovery_hits(hits, source="directories")
                for hit in hits:
                    await self.queue.enqueue("refresh_profile", {"profile_url": hit.profile_url, "source": "directories"}, priority="low")
                return True

            if message.job_type == "discover_youtube":
                source = GoogleDiscoverySource(self.apify)
                hits = await source.discover("youtube", query=message.payload.get("query"), max_results=message.payload.get("max_results", 25))
                await pipeline.store_discovery_hits(hits, source="youtube")
                for hit in hits:
                    await self.queue.enqueue("refresh_profile", {"profile_url": hit.profile_url, "source": "youtube"}, priority="low")
                return True

            if message.job_type == "import_urls":
                urls = message.payload.get("urls", [])
                hits = ManualDiscoverySource().parse_urls(urls, source=message.payload.get("source", "manual"))
                await pipeline.store_discovery_hits(hits, source=message.payload.get("source", "manual"))
                for hit in hits:
                    await self.queue.enqueue("refresh_profile", {"profile_url": hit.profile_url, "source": message.payload.get("source", "manual")}, priority="high")
                return True

            if message.job_type == "refresh_profile":
                profile_url = message.payload["profile_url"]
                existing_job = await job_repo.latest_for_profile(profile_url)
                if existing_job:
                    job = existing_job
                    await job_repo.update_status(str(job.id), "running")
                else:
                    job = await job_repo.create(profile_url=profile_url, status="running", source=message.payload.get("source"))
                username = extract_username_from_url(profile_url)
                enriched = await pipeline.enrich_and_store_usernames([username] if username else [], source=message.payload.get("source", "refresh"))
                await job_repo.update_status(str(job.id), "completed" if enriched else "failed")
                return bool(enriched)

        return False

    async def run_forever(self) -> None:
        await self.ensure_schema()
        while True:
            processed = await self.run_once()
            if not processed:
                await asyncio.sleep(2)


async def main() -> None:
    worker = Worker()
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(main())

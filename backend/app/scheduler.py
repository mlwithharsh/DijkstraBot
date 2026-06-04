from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal, engine, wait_for_database
from backend.app.models import Base, Influencer
from backend.app.repositories.refresh_jobs import RefreshJobRepository
from backend.app.services.queue import RedisQueue


class RefreshScheduler:
    def __init__(self) -> None:
        self.queue = RedisQueue()

    async def ensure_schema(self) -> None:
        await wait_for_database()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def enqueue_due_refreshes(self) -> int:
        async with AsyncSessionLocal() as session:
            job_repo = RefreshJobRepository(session)
            rows = (
                await session.execute(
                    select(Influencer.profile_url, Influencer.followers).where(
                        (Influencer.next_refresh_at.is_(None)) | (Influencer.next_refresh_at <= datetime.now(timezone.utc))
                    )
                )
            ).all()
            for profile_url, followers in rows:
                await job_repo.create_pending(profile_url, source="scheduled")
                await self.queue.enqueue("refresh_profile", {"profile_url": profile_url, "source": "scheduled"}, priority="low")
                next_refresh = self._compute_next_refresh(followers)
                await session.execute(Influencer.__table__.update().where(Influencer.profile_url == profile_url).values(next_refresh_at=next_refresh))
            await session.commit()
            return len(rows)

    def _compute_next_refresh(self, followers: int | None) -> datetime:
        now = datetime.now(timezone.utc)
        count = followers or 0
        if count > 100000:
            return now + timedelta(days=3)
        if count >= 10000:
            return now + timedelta(days=7)
        return now + timedelta(days=30)


async def main() -> None:
    scheduler = RefreshScheduler()
    await scheduler.ensure_schema()
    while True:
        await scheduler.enqueue_due_refreshes()
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())

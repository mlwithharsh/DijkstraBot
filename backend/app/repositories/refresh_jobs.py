from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import RefreshJob


class RefreshJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, profile_url: str, status: str = "pending", source: str | None = None) -> RefreshJob:
        job = RefreshJob(profile_url=profile_url, status=status, source=source)
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def create_pending(self, profile_url: str, source: str | None = None) -> RefreshJob:
        return await self.create(profile_url=profile_url, status="pending", source=source)

    async def list_recent(self, limit: int = 50) -> list[RefreshJob]:
        result = await self.session.execute(select(RefreshJob).order_by(RefreshJob.created_at.desc()).limit(limit))
        return result.scalars().all()

    async def pending_count(self) -> int:
        return int((await self.session.execute(select(func.count()).select_from(RefreshJob).where(RefreshJob.status == "pending"))).scalar_one())

    async def update_status(self, job_id: str, status: str) -> None:
        await self.session.execute(RefreshJob.__table__.update().where(RefreshJob.id == job_id).values(status=status))
        await self.session.commit()

    async def latest_for_profile(self, profile_url: str) -> RefreshJob | None:
        result = await self.session.execute(
            select(RefreshJob).where(RefreshJob.profile_url == profile_url).order_by(RefreshJob.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

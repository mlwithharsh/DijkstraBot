from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Influencer


class InfluencerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, data: dict[str, Any]) -> Influencer:
        stmt = insert(Influencer).values(**data)
        update_cols = {
            key: stmt.excluded[key]
            for key in data.keys()
            if key not in {"id", "created_at"}
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=[Influencer.username],
            set_=update_cols,
        ).returning(Influencer)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    async def bulk_upsert(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        stmt = insert(Influencer).values(rows)
        update_cols = {
            key: stmt.excluded[key]
            for key in rows[0].keys()
            if key not in {"id", "created_at"}
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=[Influencer.username],
            set_=update_cols,
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount or 0

    async def get_by_username(self, username: str) -> Influencer | None:
        result = await self.session.execute(select(Influencer).where(Influencer.username == username))
        return result.scalar_one_or_none()

    async def get_by_profile_url(self, profile_url: str) -> Influencer | None:
        result = await self.session.execute(select(Influencer).where(Influencer.profile_url == profile_url))
        return result.scalar_one_or_none()

    async def list(self, *, country: str | None = None, category: str | None = None, min_followers: int | None = None, max_followers: int | None = None, verified: bool | None = None, limit: int = 50, offset: int = 0) -> tuple[list[Influencer], int]:
        query = select(Influencer)
        count_query = select(func.count()).select_from(Influencer)
        filters = []

        if country:
            filters.append(func.lower(Influencer.country) == country.lower())
        if category:
            filters.append(func.lower(func.coalesce(Influencer.derived_category, Influencer.displayed_category)) == category.lower())
        if min_followers is not None:
            filters.append(func.coalesce(Influencer.followers, 0) >= min_followers)
        if max_followers is not None:
            filters.append(func.coalesce(Influencer.followers, 0) <= max_followers)
        if verified is not None:
            filters.append(Influencer.verified.is_(verified))

        for condition in filters:
            query = query.where(condition)
            count_query = count_query.where(condition)

        query = query.order_by(func.coalesce(Influencer.followers, 0).desc(), Influencer.last_updated.desc().nullslast()).limit(limit).offset(offset)
        items = (await self.session.execute(query)).scalars().all()
        total = int((await self.session.execute(count_query)).scalar_one())
        return items, total

    async def stats(self) -> dict[str, Any]:
        total = int((await self.session.execute(select(func.count()).select_from(Influencer))).scalar_one())
        by_country = await self.session.execute(select(Influencer.country, func.count()).group_by(Influencer.country))
        by_category = await self.session.execute(
            select(func.coalesce(Influencer.derived_category, Influencer.displayed_category), func.count()).group_by(
                func.coalesce(Influencer.derived_category, Influencer.displayed_category)
            )
        )
        follower_buckets = await self.session.execute(
            select(
                func.sum(case((Influencer.followers > 100000, 1), else_=0)).label("high"),
                func.sum(case(((Influencer.followers >= 10000) & (Influencer.followers <= 100000), 1), else_=0)).label("mid"),
                func.sum(case((Influencer.followers < 10000, 1), else_=0)).label("low"),
            )
        )
        bucket_row = follower_buckets.first()

        return {
            "total_influencers": total,
            "by_country": {row[0] or "Unknown": int(row[1]) for row in by_country.all()},
            "by_category": {row[0] or "Other": int(row[1]) for row in by_category.all()},
            "follower_buckets": {
                ">100k": int(bucket_row[0] or 0) if bucket_row else 0,
                "10k-100k": int(bucket_row[1] or 0) if bucket_row else 0,
                "<10k": int(bucket_row[2] or 0) if bucket_row else 0,
            },
        }

    async def mark_next_refresh(self, profile_url: str, next_refresh_at: datetime) -> None:
        await self.session.execute(
            Influencer.__table__.update().where(Influencer.profile_url == profile_url).values(next_refresh_at=next_refresh_at, last_updated=datetime.now(timezone.utc))
        )
        await self.session.commit()

    async def delete_all(self) -> None:
        await self.session.execute(delete(Influencer))
        await self.session.commit()

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def next_refresh_for_followers(followers: int | None, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    count = followers or 0
    if count > 100000:
        return now + timedelta(days=3)
    if count >= 10000:
        return now + timedelta(days=7)
    return now + timedelta(days=30)

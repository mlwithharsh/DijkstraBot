from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.repositories.influencers import InfluencerRepository
from backend.app.repositories.refresh_jobs import RefreshJobRepository
from backend.app.schemas import ImportUrlsRequest, JobResponse, ManualRefreshRequest, SearchResponse, SearchResponseItem, StatsResponse
from backend.app.services.normalize import normalize_profile_url
from backend.app.services.queue import RedisQueue


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/search", response_model=SearchResponse)
async def search(
    country: str | None = None,
    category: str | None = None,
    min_followers: int | None = Query(default=None, ge=0),
    max_followers: int | None = Query(default=None, ge=0),
    verified: bool | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    repo = InfluencerRepository(db)
    items, total = await repo.list(
        country=country,
        category=category,
        min_followers=min_followers,
        max_followers=max_followers,
        verified=verified,
        limit=limit,
        offset=offset,
    )
    return SearchResponse(
        total=total,
        items=[
            SearchResponseItem(
                username=item.username,
                profile_url=item.profile_url,
                full_name=item.full_name,
                followers=item.followers,
                displayed_category=item.displayed_category,
                derived_category=item.derived_category,
                country=item.country,
                verified=item.verified,
                last_updated=item.last_updated,
            )
            for item in items
        ],
    )


@router.get("/stats", response_model=StatsResponse)
async def stats(db: AsyncSession = Depends(get_db)) -> StatsResponse:
    repo = InfluencerRepository(db)
    data = await repo.stats()
    return StatsResponse(**data)


@router.get("/jobs", response_model=list[JobResponse])
async def jobs(db: AsyncSession = Depends(get_db)) -> list[JobResponse]:
    repo = RefreshJobRepository(db)
    rows = await repo.list_recent(limit=100)
    return [JobResponse(id=str(row.id), profile_url=row.profile_url, status=row.status, created_at=row.created_at) for row in rows]


@router.post("/discover")
async def discover(
    source: str = Form(...),
    query: str | None = Form(default=None),
    max_results: int = Form(default=25),
) -> dict[str, str | int]:
    queue = RedisQueue()
    await queue.enqueue(
        f"discover_{source}",
        {"query": query, "max_results": max_results},
        priority="normal",
    )
    return {"status": "queued", "source": source, "max_results": max_results}


@router.post("/import")
async def import_urls(payload: ImportUrlsRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str | int]:
    queue = RedisQueue()
    job_repo = RefreshJobRepository(db)
    urls = [normalize_profile_url(str(url)) for url in payload.urls]
    urls = [url for url in urls if url]
    if not urls:
        raise HTTPException(status_code=400, detail="No valid Instagram profile URLs provided")
    for url in urls:
        await job_repo.create_pending(url, source=payload.source)
    await queue.enqueue("import_urls", {"urls": urls, "source": payload.source}, priority="high")
    return {"status": "queued", "count": len(urls)}


@router.post("/refresh")
async def refresh(payload: ManualRefreshRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str | int]:
    queue = RedisQueue()
    job_repo = RefreshJobRepository(db)
    urls = [normalize_profile_url(str(url)) for url in payload.profile_urls]
    urls = [url for url in urls if url]
    if not urls:
        raise HTTPException(status_code=400, detail="No valid Instagram profile URLs provided")
    for url in urls:
        await job_repo.create_pending(url, source="manual")
        await queue.enqueue("refresh_profile", {"profile_url": url, "source": "manual"}, priority="high")
    return {"status": "queued", "count": len(urls)}

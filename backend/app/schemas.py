from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class DiscoveryRequest(BaseModel):
    source: str = Field(default="google", description="google | directories | youtube | import")
    query: str | None = None
    max_results: int = 25


class ImportUrlsRequest(BaseModel):
    urls: list[HttpUrl]
    source: str = "manual"


class ManualRefreshRequest(BaseModel):
    profile_urls: list[HttpUrl]


class SearchResponseItem(BaseModel):
    username: str
    profile_url: str
    full_name: str | None
    followers: int | None
    displayed_category: str | None
    derived_category: str | None
    country: str | None
    verified: bool
    last_updated: datetime | None


class SearchResponse(BaseModel):
    total: int
    items: list[SearchResponseItem]


class StatsResponse(BaseModel):
    total_influencers: int
    by_country: dict[str, int]
    by_category: dict[str, int]
    follower_buckets: dict[str, int]


class JobResponse(BaseModel):
    id: str
    profile_url: str
    status: str
    created_at: datetime

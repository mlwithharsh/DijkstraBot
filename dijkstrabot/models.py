from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class RawProfile(BaseModel):
    username: str
    full_name: Optional[str] = None
    biography: Optional[str] = None
    follower_count: int
    following_count: int
    media_count: int
    avg_likes: Optional[float] = None
    avg_comments: Optional[float] = None
    is_verified: bool
    profile_pic_url: Optional[str] = None
    external_url: Optional[str] = None
    gender: Optional[str] = None
    api_category: Optional[str] = None
    source_api: str
    fetched_at: datetime = Field(default_factory=datetime.now)

class EnrichedProfile(RawProfile):
    profile_url: str
    engagement_rate: float
    est_avg_reach: int
    location: Optional[str] = None
    category: str
    primary_hashtags: List[str]
    bio_keywords_matched: List[str]
    dijkstra_score: float
    last_scraped_at: datetime = Field(default_factory=datetime.now)

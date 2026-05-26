from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from dijkstrabot.models import EnrichedProfile
from dijkstrabot.utils.logger import logger

@dataclass
class AudienceConfig:
    follower_min: int = 1_000
    follower_max: int = 10_000_000
    location_country: Optional[str] = None
    location_city: Optional[str] = None

@dataclass
class CreatorConfig:
    gender: Optional[str] = None
    category: Optional[Union[str, List[str]]] = None
    bio_keywords: List[str] = field(default_factory=list)
    bio_hashtags: List[str] = field(default_factory=list)
    community_tags: List[str] = field(default_factory=list)

@dataclass
class PerformanceConfig:
    min_engagement_rate: float = 0.5
    min_dijkstra_score: float = 0.0
    verified_only: bool = False

@dataclass
class OutputConfig:
    max_results: int = 50_000
    sort_by: str = "dijkstra_score"
    google_drive_folder_id: Optional[str] = None

@dataclass
class FilterConfig:
    audience: AudienceConfig = field(default_factory=AudienceConfig)
    creator: CreatorConfig = field(default_factory=CreatorConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

def apply_filters(profiles: List[EnrichedProfile], config: FilterConfig) -> List[EnrichedProfile]:
    initial_count = len(profiles)
    profiles = [p for p in profiles if config.audience.follower_min <= p.follower_count <= config.audience.follower_max]
    after_audience = len(profiles)
    logger.info("filter_step", step="audience", eliminated=initial_count - after_audience)
    profiles = [p for p in profiles if p.engagement_rate >= config.performance.min_engagement_rate]
    profiles = [p for p in profiles if p.dijkstra_score >= config.performance.min_dijkstra_score]
    if config.performance.verified_only:
        profiles = [p for p in profiles if p.is_verified]
    after_perf = len(profiles)
    logger.info("filter_step", step="performance", eliminated=after_audience - after_perf)
    if config.creator.category:
        categories = config.creator.category
        if isinstance(categories, str): categories = [categories]
        profiles = [p for p in profiles if p.category in categories]
    if config.creator.gender and config.creator.gender != "any":
        profiles = [p for p in profiles if p.gender == config.creator.gender]
    after_creator = len(profiles)
    logger.info("filter_step", step="creator", eliminated=after_perf - after_creator)
    profiles.sort(key=lambda x: getattr(x, config.output.sort_by, 0), reverse=True)
    profiles = profiles[:config.output.max_results]
    logger.info("filtering_complete", initial=initial_count, final=len(profiles))
    return profiles

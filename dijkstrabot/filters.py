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
    niches: List[str] = field(default_factory=list)
    bio_keywords: List[str] = field(default_factory=list)
    bio_hashtags: List[str] = field(default_factory=list)
    community_tags: List[str] = field(default_factory=list)
    seed_usernames: List[str] = field(default_factory=list)

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
    output_dir: str = "./output"
    export_format: str = "csv"
    use_mock_data: bool = False
    allow_empty_export: bool = False
    profile_fetch_limit: int = 10

@dataclass
class FilterConfig:
    audience: AudienceConfig = field(default_factory=AudienceConfig)
    creator: CreatorConfig = field(default_factory=CreatorConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

def filter_profiles_with_report(profiles: List[EnrichedProfile], config: FilterConfig) -> tuple[List[EnrichedProfile], dict]:
    initial_count = len(profiles)
    report = {"initial": initial_count, "steps": []}

    profiles = [p for p in profiles if config.audience.follower_min <= p.follower_count <= config.audience.follower_max]
    after_audience = len(profiles)
    report["steps"].append({"step": "audience", "before": initial_count, "after": after_audience, "eliminated": initial_count - after_audience})
    logger.info("filter_step", step="audience", eliminated=initial_count - after_audience)

    if config.audience.location_city:
        city = config.audience.location_city.lower()
        profiles = [p for p in profiles if p.location and city in p.location.lower()]
    if config.audience.location_country:
        country = config.audience.location_country.lower()
        profiles = [p for p in profiles if p.location and country in p.location.lower()]
    after_location = len(profiles)
    report["steps"].append({"step": "location", "before": after_audience, "after": after_location, "eliminated": after_audience - after_location})
    logger.info("filter_step", step="location", eliminated=after_audience - after_location)

    profiles = [p for p in profiles if p.engagement_rate >= config.performance.min_engagement_rate]
    profiles = [p for p in profiles if p.dijkstra_score >= config.performance.min_dijkstra_score]
    if config.performance.verified_only:
        profiles = [p for p in profiles if p.is_verified]
    after_perf = len(profiles)
    report["steps"].append({"step": "performance", "before": after_location, "after": after_perf, "eliminated": after_location - after_perf})
    logger.info("filter_step", step="performance", eliminated=after_location - after_perf)

    if config.creator.category:
        categories = config.creator.category
        if isinstance(categories, str): categories = [categories]
        category_set = {c.lower() for c in categories}
        profiles = [p for p in profiles if p.category.lower() in category_set]
    if config.creator.niches:
        niche_terms = [n.lower() for n in config.creator.niches]
        profiles = [
            p for p in profiles
            if any(term in (p.biography or "").lower() for term in niche_terms)
            or any(term in h.lower() for term in niche_terms for h in p.primary_hashtags)
        ]
    if config.creator.bio_keywords:
        profiles = [p for p in profiles if p.bio_keywords_matched]
    if config.creator.bio_hashtags:
        wanted_tags = {h.lower().lstrip("#") for h in config.creator.bio_hashtags}
        profiles = [
            p for p in profiles
            if wanted_tags.intersection({h.lower().lstrip("#") for h in p.primary_hashtags})
        ]
    if config.creator.gender and config.creator.gender != "any":
        profiles = [p for p in profiles if p.gender == config.creator.gender]
    after_creator = len(profiles)
    report["steps"].append({"step": "creator", "before": after_perf, "after": after_creator, "eliminated": after_perf - after_creator})
    logger.info("filter_step", step="creator", eliminated=after_perf - after_creator)

    sort_by = config.output.sort_by if hasattr(EnrichedProfile, config.output.sort_by) else config.output.sort_by
    profiles.sort(key=lambda x: getattr(x, sort_by, 0) or 0, reverse=True)
    profiles = profiles[:config.output.max_results]
    report["final"] = len(profiles)
    logger.info("filtering_complete", initial=initial_count, final=len(profiles))
    return profiles, report


def apply_filters(profiles: List[EnrichedProfile], config: FilterConfig) -> List[EnrichedProfile]:
    filtered, _ = filter_profiles_with_report(profiles, config)
    return filtered

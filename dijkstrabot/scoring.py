from typing import Any
from dijkstrabot.models import EnrichedProfile

WEIGHTS = {
    "engagement_rate": 0.40,
    "follower_authenticity": 0.20,
    "niche_relevance": 0.25,
    "location_match": 0.10,
    "posting_frequency": 0.05,
}

def compute_engagement_rate(likes: int, comments: int, followers: int) -> float:
    if followers == 0: return 0.0
    return round(((likes + comments) / followers) * 100, 2)

def compute_avg_reach(profile: EnrichedProfile) -> int:
    return int(round(profile.engagement_rate * profile.follower_count / 100, -2))

def compute_dijkstra_score(profile: EnrichedProfile, config: Any) -> float:
    er = profile.engagement_rate
    followers = profile.follower_count
    if followers < 10_000: er_score = min(100, (er / 5.0) * 100)
    elif followers < 100_000: er_score = min(100, (er / 3.0) * 100)
    elif followers < 1_000_000: er_score = min(100, (er / 1.5) * 100)
    else: er_score = min(100, (er / 0.5) * 100)
    ratio = profile.follower_count / (profile.following_count or 1)
    if ratio > 10: auth_score = 100
    elif ratio > 5: auth_score = 75
    elif ratio > 2: auth_score = 50
    else: auth_score = 25
    matched = len(profile.bio_keywords_matched)
    total = len(config.creator.bio_keywords) or 1
    relevance_score = min(100, (matched / total) * 100)
    target_categories = config.creator.category
    if isinstance(target_categories, str): target_categories = [target_categories]
    elif target_categories is None: target_categories = []
    if profile.category in target_categories: relevance_score = min(100, relevance_score + 20)
    loc_score = 0
    if config.audience.location_city and profile.location:
        if config.audience.location_city.lower() in profile.location.lower(): loc_score = 100
    elif config.audience.location_country and profile.location:
        if config.audience.location_country.lower() in profile.location.lower(): loc_score = 60
    freq_score = min(100, (profile.media_count / 100) * 100)
    final_score = (er_score * WEIGHTS["engagement_rate"] + auth_score * WEIGHTS["follower_authenticity"] + relevance_score * WEIGHTS["niche_relevance"] + loc_score * WEIGHTS["location_match"] + freq_score * WEIGHTS["posting_frequency"])
    return round(min(100.0, final_score), 2)

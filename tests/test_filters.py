from dijkstrabot.filters import FilterConfig, AudienceConfig, PerformanceConfig, apply_filters
from dijkstrabot.models import EnrichedProfile
from datetime import datetime

def test_follower_range_filter():
    config = FilterConfig(audience=AudienceConfig(follower_min=1000, follower_max=5000))
    profiles = [
        EnrichedProfile(
            username="p1", follower_count=500, following_count=10, media_count=10,
            is_verified=False, source_api="t", fetched_at=datetime.now(),
            profile_url="", engagement_rate=1.0, est_avg_reach=1, category="c",
            primary_hashtags=[], bio_keywords_matched=[], dijkstra_score=50.0
        ),
        EnrichedProfile(
            username="p2", follower_count=2000, following_count=10, media_count=10,
            is_verified=False, source_api="t", fetched_at=datetime.now(),
            profile_url="", engagement_rate=1.0, est_avg_reach=1, category="c",
            primary_hashtags=[], bio_keywords_matched=[], dijkstra_score=50.0
        )
    ]
    filtered = apply_filters(profiles, config)
    assert len(filtered) == 1
    assert filtered[0].username == "p2"

def test_min_score_filter():
    config = FilterConfig(performance=PerformanceConfig(min_dijkstra_score=70.0))
    profiles = [
        EnrichedProfile(
            username="p1", follower_count=2000, following_count=10, media_count=10,
            is_verified=False, source_api="t", fetched_at=datetime.now(),
            profile_url="", engagement_rate=1.0, est_avg_reach=1, category="c",
            primary_hashtags=[], bio_keywords_matched=[], dijkstra_score=50.0
        ),
        EnrichedProfile(
            username="p2", follower_count=2000, following_count=10, media_count=10,
            is_verified=False, source_api="t", fetched_at=datetime.now(),
            profile_url="", engagement_rate=1.0, est_avg_reach=1, category="c",
            primary_hashtags=[], bio_keywords_matched=[], dijkstra_score=80.0
        )
    ]
    filtered = apply_filters(profiles, config)
    assert len(filtered) == 1
    assert filtered[0].username == "p2"

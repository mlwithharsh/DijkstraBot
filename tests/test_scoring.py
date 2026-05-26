import pytest
from datetime import datetime
from dijkstrabot.models import EnrichedProfile
from dijkstrabot.scoring import compute_dijkstra_score, compute_engagement_rate
from dijkstrabot.filters import FilterConfig, CreatorConfig

@pytest.fixture
def mock_config():
    return FilterConfig(creator=CreatorConfig(bio_keywords=["fitness"]))

def test_engagement_rate_calc():
    assert compute_engagement_rate(100, 50, 1000) == 15.0

def test_nano_influencer_high_er_scores_100(mock_config):
    profile = EnrichedProfile(
        username="test", follower_count=5000, following_count=100,
        media_count=100, is_verified=False, source_api="test",
        fetched_at=datetime.now(), profile_url="", engagement_rate=10.0,
        est_avg_reach=500, category="fitness", primary_hashtags=[],
        bio_keywords_matched=["fitness"], dijkstra_score=0.0
    )
    score = compute_dijkstra_score(profile, mock_config)
    assert score >= 80

def test_dijkstra_score_bounded(mock_config):
    profile = EnrichedProfile(
        username="test", follower_count=10, following_count=10,
        media_count=0, is_verified=False, source_api="test",
        fetched_at=datetime.now(), profile_url="", engagement_rate=0.0,
        est_avg_reach=0, category="unknown", primary_hashtags=[],
        bio_keywords_matched=[], dijkstra_score=0.0
    )
    score = compute_dijkstra_score(profile, mock_config)
    assert 0 <= score <= 100

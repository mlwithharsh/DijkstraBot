from dijkstrabot.enrichment import extract_hashtags, detect_gender, score_category
from dijkstrabot.models import RawProfile
from datetime import datetime

def test_hashtag_extraction():
    bio = "#fitness #gym lover"
    assert extract_hashtags(bio) == ["#fitness", "#gym"]

def test_gender_pronoun_she():
    profile = RawProfile(
        username="test", follower_count=100, following_count=100,
        media_count=10, is_verified=False, source_api="test",
        biography="she/her | lifestyle", fetched_at=datetime.now()
    )
    assert detect_gender(profile) == "female"

def test_category_fitness():
    bio = "I love the gym and crossfit"
    assert score_category(bio, []) == "fitness"

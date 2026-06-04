import re
from typing import List, Any
from dijkstrabot.models import RawProfile, EnrichedProfile
from dijkstrabot.utils.geo import extract_location
from dijkstrabot.utils.logger import logger

NICHE_TAXONOMY = {
    "fitness": ["gym", "workout", "fitness", "crossfit", "yoga", "running", "athlete", "weightlifting"],
    "beauty": ["makeup", "skincare", "beauty", "cosmetics", "glam", "lipstick", "eyeshadow"],
    "food": ["foodie", "chef", "recipe", "cooking", "restaurant", "baking", "nutrition"],
    "travel": ["travel", "wanderlust", "explorer", "adventure", "backpacker", "nomad"],
    "tech": ["developer", "coding", "startup", "saas", "ai", "engineer", "tech"],
    "fashion": ["fashion", "style", "ootd", "streetwear", "designer", "model"],
    "parenting": ["mom", "dad", "parent", "baby", "toddler", "family", "motherhood"],
    "lifestyle": ["lifestyle", "wellness", "mindfulness", "selfcare", "motivation"],
    "business": ["entrepreneur", "ceo", "founder", "business", "marketing", "sales"],
    "gaming": ["gamer", "gaming", "streamer", "esports", "twitch", "playstation", "xbox"],
    "artist": ["artist", "painter", "sculptor", "illustrator", "creative", "art", "gallery", "sketch"],
    "dancer": ["dance", "dancer", "choreographer", "choreography", "hiphop", "ballet", "contemporary"],
    "music": ["musician", "singer", "rapper", "producer", "dj", "songwriter", "music"],
    "comedy": ["comedian", "comedy", "standup", "sketch comedy", "funny", "memes"],
}

def extract_hashtags(bio: str) -> List[str]:
    if not bio: return []
    return re.findall(r"#\w+", bio)

def match_keywords(bio: str, search_terms: List[str]) -> List[str]:
    if not bio or not search_terms: return []
    bio_lower = bio.lower()
    return [term for term in search_terms if term.lower() in bio_lower]

def detect_gender(profile: RawProfile) -> str:
    if profile.gender: return profile.gender
    bio = (profile.biography or "").lower()
    if re.search(r"\bshe/her\b", bio): return "female"
    if re.search(r"\bhe/him\b", bio): return "male"
    if re.search(r"\bthey/them\b", bio): return "non-binary"
    return "unknown"

def score_category(bio: str, hashtags: List[str]) -> str:
    bio_text = f"{bio} {' '.join(hashtags)}".lower()
    scores = {}
    for category, keywords in NICHE_TAXONOMY.items():
        score = sum(1 for kw in keywords if kw in bio_text)
        if score > 0: scores[category] = score
    if not scores: return "lifestyle"
    return max(scores, key=scores.get)

async def enrich_profile(profile: RawProfile, config: Any) -> EnrichedProfile:
    bio = profile.biography or ""
    hashtags = extract_hashtags(bio)
    likes = profile.avg_likes or 0
    comments = profile.avg_comments or 0
    followers = profile.follower_count or 1
    engagement_rate = ((likes + comments) / followers) * 100
    location = extract_location(bio)
    category = (profile.api_category or "").lower() or score_category(bio, hashtags)
    matched_kws = match_keywords(bio, config.creator.bio_keywords)
    gender = detect_gender(profile)
    data = profile.model_dump()
    data["gender"] = gender
    return EnrichedProfile(
        **data,
        profile_url=f"https://instagram.com/{profile.username}",
        engagement_rate=round(engagement_rate, 2),
        est_avg_reach=int(engagement_rate * followers / 100),
        location=location,
        category=category,
        primary_hashtags=hashtags[:5],
        bio_keywords_matched=matched_kws,
        dijkstra_score=0.0
    )

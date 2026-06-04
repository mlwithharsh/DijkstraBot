from __future__ import annotations

from dataclasses import dataclass


CATEGORY_KEYWORDS = {
    "Fitness": ["fitness", "gym", "workout", "coach", "trainer", "yoga", "run", "athlete", "crossfit"],
    "Fashion": ["fashion", "style", "ootd", "outfit", "designer", "model", "streetwear"],
    "Beauty": ["beauty", "makeup", "skincare", "cosmetics", "glam", "hair", "salon"],
    "Food": ["food", "recipe", "chef", "cooking", "cafe", "restaurant", "baking", "foodie"],
    "Travel": ["travel", "wanderlust", "trip", "explore", "adventure", "airport", "backpack"],
    "Gaming": ["gaming", "gamer", "streamer", "esports", "gameplay", "twitch", "pc gamer"],
    "Finance": ["finance", "stock", "invest", "investing", "trading", "wealth", "money", "personal finance"],
    "Technology": ["tech", "developer", "engineer", "ai", "startup", "software", "product", "programmer"],
    "Business": ["business", "founder", "co-founder", "entrepreneur", "marketing", "sales", "agency", "consulting"],
    "Education": ["education", "teacher", "mentor", "learning", "edtech", "course", "study"],
    "Lifestyle": ["lifestyle", "daily", "vlog", "wellness", "selfcare", "motivation", "routine"],
    "Parenting": ["parent", "mom", "dad", "motherhood", "fatherhood", "baby", "kids", "family"],
}


@dataclass(slots=True)
class ClassificationResult:
    category: str
    confidence: float
    matched_keywords: list[str]


class CategoryClassifier:
    def classify(self, text: str | None, displayed_category: str | None = None) -> ClassificationResult:
        candidates = [text or "", displayed_category or ""]
        haystack = " ".join(candidates).lower()
        best_category = "Other"
        best_hits: list[str] = []

        for category, keywords in CATEGORY_KEYWORDS.items():
            hits = [keyword for keyword in keywords if keyword in haystack]
            if len(hits) > len(best_hits):
                best_category = category
                best_hits = hits

        confidence = min(0.95, 0.2 + (len(best_hits) * 0.15))
        if best_category == "Other":
            confidence = 0.25 if haystack else 0.0
        return ClassificationResult(category=best_category, confidence=round(confidence, 2), matched_keywords=best_hits)

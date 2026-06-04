from __future__ import annotations

import re
from dataclasses import dataclass


INDIAN_CITIES = {
    "mumbai", "delhi", "new delhi", "bangalore", "bengaluru", "hyderabad", "chennai", "kolkata",
    "pune", "ahmedabad", "jaipur", "surat", "lucknow", "kochi", "goa", "indore", "nagpur",
    "gurgaon", "gurugram", "noida", "chandigarh", "coimbatore", "bhopal", "visakhapatnam",
}

INDIAN_DOMAINS = {".in", ".co.in", ".org.in", ".net.in", ".gov.in"}
PHONE_PATTERNS = [r"\+91\b", r"\b91[-\s]?\d{10}\b"]
HINDI_RE = re.compile(r"[\u0900-\u097F]")


@dataclass(slots=True)
class CountryDetection:
    country: str | None
    confidence: float
    signals: list[str]


def detect_country(text: str | None) -> CountryDetection:
    if not text:
        return CountryDetection(country=None, confidence=0.0, signals=[])

    lowered = text.lower()
    score = 0.0
    signals: list[str] = []

    if any(city in lowered for city in INDIAN_CITIES):
        score += 0.35
        signals.append("indian_city")
    if any(domain in lowered for domain in INDIAN_DOMAINS):
        score += 0.2
        signals.append("indian_domain")
    if any(re.search(pattern, lowered) for pattern in PHONE_PATTERNS):
        score += 0.2
        signals.append("indian_phone")
    if HINDI_RE.search(text):
        score += 0.2
        signals.append("hindi_script")
    if any(word in lowered for word in ["india", "indian", "bharat", "delhi", "mumbai"]):
        score += 0.15
        signals.append("india_reference")

    confidence = min(score, 0.99)
    if confidence >= 0.35:
        return CountryDetection(country="India", confidence=round(confidence, 2), signals=signals)
    return CountryDetection(country=None, confidence=round(confidence, 2), signals=signals)

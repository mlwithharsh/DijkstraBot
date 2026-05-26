import spacy
from typing import Optional

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            return None
    return _nlp

# Expanded dictionary for common locations
CITY_DICT = {
    "mumbai", "delhi", "bangalore", "hyderabad", "ahmedabad", "chennai", "kolkata", "surat", "pune", "jaipur",
    "london", "new york", "paris", "tokyo", "berlin", "dubai", "singapore", "sydney", "toronto", "los angeles",
    "chicago", "houston", "san francisco", "seattle", "austin", "miami", "atlanta", "denver", "boston",
    "madrid", "rome", "amsterdam", "vienna", "prague", "warsaw", "istanbul", "moscow", "seoul", "beijing",
    "bangkok", "jakarta", "manila", "mexico city", "sao paulo", "buenos aires", "lagos", "cairo", "nairobi"
}

COUNTRY_DICT = {
    "india", "united states", "united kingdom", "france", "germany", "japan", "united arab emirates", "australia", "canada", "brazil",
    "italy", "spain", "netherlands", "switzerland", "sweden", "norway", "denmark", "russia", "china", "south korea",
    "mexico", "argentina", "colombia", "nigeria", "egypt", "south africa", "turkey", "thailand", "vietnam", "indonesia"
}

def extract_location(bio: str) -> Optional[str]:
    if not bio: return None
    nlp = get_nlp()
    if nlp:
        doc = nlp(bio)
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"): return ent.text

    bio_lower = bio.lower()
    for city in CITY_DICT:
        if city in bio_lower: return city.title()
    for country in COUNTRY_DICT:
        if country in bio_lower: return country.title()
    return None

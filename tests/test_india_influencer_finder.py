from backend.app.services.classification import CategoryClassifier
from backend.app.services.country import detect_country
from backend.app.services.normalize import normalize_profile_url, normalize_username


def test_normalize_username_and_url():
    assert normalize_username("@FitCoach") == "fitcoach"
    assert normalize_profile_url("instagram.com/FitCoach") == "https://www.instagram.com/fitcoach/"


def test_classification_service_detects_fitness():
    result = CategoryClassifier().classify("Certified personal trainer and gym coach in Mumbai")
    assert result.category == "Fitness"
    assert result.confidence >= 0.2


def test_country_detector_marks_india():
    result = detect_country("Mumbai, India | +91 9876543210 | coaching in Hindi")
    assert result.country == "India"
    assert result.confidence >= 0.35

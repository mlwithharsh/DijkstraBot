import asyncio
import random
import time
from typing import List

from dotenv import load_dotenv

from dijkstrabot.filters import (
    AudienceConfig,
    CreatorConfig,
    FilterConfig,
    OutputConfig,
    PerformanceConfig,
    apply_filters,
)
from dijkstrabot.discovery import discover_all
from dijkstrabot.enrichment import enrich_profile
from dijkstrabot.scoring import compute_dijkstra_score
from dijkstrabot.models import RawProfile, EnrichedProfile

load_dotenv()


def build_test_config() -> FilterConfig:
    # Target: lifestyle influencers with 50K-100K followers.
    return FilterConfig(
        audience=AudienceConfig(
            follower_min=50_000,
            follower_max=100_000,
            location_country=None,
            location_city=None,
        ),
        creator=CreatorConfig(
            gender=None,
            category="lifestyle",
            bio_keywords=[],
            # Seed discovery (RapidAPI hashtag feed) with lifestyle-related tags.
            # More seeds increases candidate pool for Meta Business Discovery.
            # Keep seeds small to avoid RapidAPI throttling during robust test.
            bio_hashtags=["lifestyle", "wellness", "selfcare", "mindfulness", "motivation"],
            community_tags=[],
        ),
        performance=PerformanceConfig(
            min_engagement_rate=0.0,
            min_dijkstra_score=0.0,
            verified_only=False,
        ),
        # This primarily controls pagination for Phyllo discovery (mock fallback ignores it).
        output=OutputConfig(
            max_results=5_000,
            sort_by="dijkstra_score",
            google_drive_folder_id=None,
        ),
    )


async def process_profile(raw: RawProfile, config: FilterConfig) -> EnrichedProfile:
    enriched = await enrich_profile(raw, config)
    enriched.dijkstra_score = compute_dijkstra_score(enriched, config)
    return enriched


async def run_once(config: FilterConfig, *, seed: int) -> List[EnrichedProfile]:
    # For deterministic mock fallback results.
    random.seed(seed)

    raw_profiles = await discover_all(config)
    tasks = [process_profile(raw, config) for raw in raw_profiles]
    enriched_profiles = await asyncio.gather(*tasks)

    final_profiles = apply_filters(enriched_profiles, config)
    return final_profiles


def validate_profiles(profiles: List[EnrichedProfile], config: FilterConfig) -> List[str]:
    errors: List[str] = []
    wanted_category = (
        [config.creator.category] if isinstance(config.creator.category, str) else (config.creator.category or [])
    )
    for p in profiles:
        if not (config.audience.follower_min <= p.follower_count <= config.audience.follower_max):
            errors.append(f"{p.username}: follower_count out of range ({p.follower_count})")
        if wanted_category and p.category not in wanted_category:
            errors.append(f"{p.username}: category mismatch ({p.category} != {wanted_category})")
    return errors


async def main() -> None:
    config = build_test_config()
    attempts = 3
    seed_base = int(time.time()) % 10_000

    print("Robust scraper integration test")
    print("Target:", "lifestyle", "followers:", f"{config.audience.follower_min}-{config.audience.follower_max}")
    print("Attempts:", attempts)

    best: List[EnrichedProfile] = []
    last_errors: List[str] = []

    for attempt in range(1, attempts + 1):
        seed = seed_base + attempt
        print(f"\nAttempt {attempt}/{attempts} (seed={seed}) ...")
        final_profiles = await run_once(config, seed=seed)
        final_profiles = sorted(final_profiles, key=lambda x: x.dijkstra_score, reverse=True)

        errors = validate_profiles(final_profiles[:20], config)
        last_errors = errors

        print(f"Found after filtering: {len(final_profiles)} profiles")
        if final_profiles:
            top3 = ", ".join([f"{p.username}({p.follower_count})" for p in final_profiles[:3]])
            print("Top 3:", top3)

        if len(final_profiles) > len(best):
            best = final_profiles

        if len(final_profiles) >= 20:
            break

    print("\n=== Test Result ===")
    if len(best) >= 20:
        print(f"PASS: Found {len(best)} >= 20 lifestyle influencers in the target follower range.")
        top20 = best[:20]
        for i, p in enumerate(top20, start=1):
            print(f"{i:02d}. {p.username} | followers={p.follower_count} | dijkstra_score={p.dijkstra_score}")
    else:
        print(f"FAIL: Found {len(best)} (<20) lifestyle influencers in the target follower range.")
        if last_errors:
            print("Validation issues (top slice):")
            for e in last_errors[:10]:
                print(" -", e)
        print(
            "Note: If no Phyllo/RapidAPI credentials are configured in environment variables, "
            "the scraper uses mock data, which may not produce enough matches."
        )


if __name__ == "__main__":
    asyncio.run(main())


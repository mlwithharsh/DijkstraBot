from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from dijkstrabot.filters import (
    AudienceConfig,
    CreatorConfig,
    FilterConfig,
    OutputConfig,
    PerformanceConfig,
)


def _prompt_text(label: str, default: Optional[str] = None) -> Optional[str]:
    suffix = f" [{default}]" if default not in (None, "") else ""
    value = input(f"{label}{suffix}: ").strip()
    if value:
        return value
    return default


def _prompt_int(label: str, default: int) -> int:
    while True:
        value = _prompt_text(label, str(default))
        try:
            return int(str(value).replace(",", ""))
        except ValueError:
            print("Enter a whole number.")


def _prompt_float(label: str, default: float) -> float:
    while True:
        value = _prompt_text(label, str(default))
        try:
            return float(str(value))
        except ValueError:
            print("Enter a number.")


def _prompt_bool(label: str, default: bool = False) -> bool:
    default_text = "y" if default else "n"
    value = (_prompt_text(label, default_text) or default_text).lower()
    return value in {"y", "yes", "true", "1"}


def _csv_values(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _read_seed_file(path: Optional[str]) -> List[str]:
    if not path:
        return []
    seed_path = Path(path).expanduser()
    if not seed_path.exists():
        print(f"Seed file not found: {seed_path}")
        return []
    return [
        line.strip().lstrip("@")
        for line in seed_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def prompt_for_config(default: Optional[FilterConfig] = None) -> FilterConfig:
    default = default or FilterConfig()
    print("\nDijkstraBot campaign setup")
    print("Leave a value blank to use the default shown in brackets.\n")

    follower_min = _prompt_int("Minimum followers", default.audience.follower_min)
    follower_max = _prompt_int("Maximum followers", default.audience.follower_max)
    location_country = _prompt_text("Country filter, blank for any", default.audience.location_country)
    location_city = _prompt_text("City filter, blank for any", default.audience.location_city)

    category_value = _prompt_text(
        "Categories, comma-separated e.g. fitness,artist,dancer",
        ",".join(default.creator.category) if isinstance(default.creator.category, list) else default.creator.category,
    )
    categories = _csv_values(category_value)
    category = categories if len(categories) > 1 else (categories[0] if categories else None)

    niches = _csv_values(_prompt_text("Niche terms, comma-separated", ",".join(default.creator.niches)))
    bio_keywords = _csv_values(_prompt_text("Bio keywords, comma-separated", ",".join(default.creator.bio_keywords)))
    hashtags = _csv_values(_prompt_text("Hashtags, comma-separated", ",".join(default.creator.bio_hashtags)))
    gender = _prompt_text("Gender filter: any, male, female, non-binary", default.creator.gender or "any")
    if gender == "any":
        gender = None

    seed_usernames = _csv_values(_prompt_text("Seed usernames, comma-separated", ""))
    seed_file = _prompt_text("Seed username file path, blank for none", "")
    seed_usernames.extend(_read_seed_file(seed_file))

    min_engagement_rate = _prompt_float("Minimum engagement rate percent", default.performance.min_engagement_rate)
    min_dijkstra_score = _prompt_float("Minimum DijkstraScore", default.performance.min_dijkstra_score)
    verified_only = _prompt_bool("Verified accounts only? y/n", default.performance.verified_only)

    max_results = _prompt_int("Maximum output rows", default.output.max_results)
    profile_fetch_limit = _prompt_int("Credit-safe full profile fetch limit", default.output.profile_fetch_limit)
    sort_by = _prompt_text("Sort by: dijkstra_score, follower_count, engagement_rate", default.output.sort_by) or "dijkstra_score"
    output_dir = _prompt_text("Output directory", default.output.output_dir) or "./output"
    export_format = (_prompt_text("Export format: csv, xlsx, both", default.output.export_format) or "csv").lower()

    return FilterConfig(
        audience=AudienceConfig(
            follower_min=follower_min,
            follower_max=follower_max,
            location_country=location_country or None,
            location_city=location_city or None,
        ),
        creator=CreatorConfig(
            gender=gender,
            category=category,
            niches=niches,
            bio_keywords=bio_keywords,
            bio_hashtags=hashtags,
            seed_usernames=sorted(set(seed_usernames)),
        ),
        performance=PerformanceConfig(
            min_engagement_rate=min_engagement_rate,
            min_dijkstra_score=min_dijkstra_score,
            verified_only=verified_only,
        ),
        output=OutputConfig(
            max_results=max_results,
            profile_fetch_limit=profile_fetch_limit,
            sort_by=sort_by,
            output_dir=output_dir,
            export_format=export_format,
            google_drive_folder_id=default.output.google_drive_folder_id,
        ),
    )

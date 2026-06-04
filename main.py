import argparse
import asyncio
import os
import time
from datetime import datetime

import yaml
from dotenv import load_dotenv

from dijkstrabot.cli import prompt_for_config
from dijkstrabot.discovery import discover_all, get_last_discovery_diagnostics
from dijkstrabot.enrichment import enrich_profile
from dijkstrabot.exporter import CSVExporter, SheetsExporter, XLSXExporter
from dijkstrabot.filters import (
    AudienceConfig,
    CreatorConfig,
    FilterConfig,
    OutputConfig,
    PerformanceConfig,
    filter_profiles_with_report,
)
from dijkstrabot.scheduler import start_scheduler
from dijkstrabot.scoring import compute_dijkstra_score
from dijkstrabot.utils.logger import logger

load_dotenv()


async def process_profile(raw, config):
    enriched = await enrich_profile(raw, config)
    enriched.dijkstra_score = compute_dijkstra_score(enriched, config)
    return enriched


async def run_discovery(
    config: FilterConfig,
    dry_run: bool = False,
    no_sheets: bool = False,
    no_xlsx: bool = False,
    no_csv: bool = False,
):
    start_time = time.time()

    raw_profiles = await discover_all(config)
    if dry_run:
        raw_profiles = raw_profiles[:100]

    if not raw_profiles:
        diagnostics = get_last_discovery_diagnostics()
        print("\nNo profiles were discovered. CSV export was skipped.")
        if diagnostics:
            print("Discovery diagnostics:")
            for item in diagnostics:
                print(f"- {item}")
        raise RuntimeError("No profiles discovered from configured data sources.")

    logger.info("enrichment_started", count=len(raw_profiles))
    semaphore = asyncio.Semaphore(100)

    async def bounded_process(raw):
        async with semaphore:
            return await process_profile(raw, config)

    enriched_profiles = []
    for start in range(0, len(raw_profiles), 1000):
        batch = raw_profiles[start:start + 1000]
        enriched_profiles.extend(await asyncio.gather(*[bounded_process(raw) for raw in batch]))

    final_profiles, filter_report = filter_profiles_with_report(enriched_profiles, config)

    stats = {
        "profiles_fetched": len(raw_profiles),
        "profiles_enriched": len(enriched_profiles),
        "profiles_filtered": len(final_profiles),
        "run_duration_seconds": round(time.time() - start_time, 2),
        "timestamp": datetime.now().isoformat(),
    }

    if not final_profiles and not config.output.allow_empty_export:
        print("\nProfiles were discovered, but all were removed by filters. CSV export was skipped.")
        print("Filter diagnostics:")
        for step in filter_report["steps"]:
            print(f"- {step['step']}: {step['before']} -> {step['after']} ({step['eliminated']} removed)")
        print("Relax one or more filters, usually follower range, location, hashtags, bio keywords, or minimum score.")
        raise RuntimeError("All discovered profiles were removed by filters.")

    if not dry_run:
        export_format = (config.output.export_format or "csv").lower()
        if export_format in {"csv", "both"} and not no_csv:
            CSVExporter(config.output.output_dir).export(final_profiles)

        if export_format in {"xlsx", "both"} and not no_xlsx:
            XLSXExporter(config.output.output_dir).export(final_profiles)

        if not no_sheets:
            sheets_exporter = SheetsExporter(
                service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json"),
                folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID", ""),
            )
            await sheets_exporter.export(final_profiles, stats)

    logger.info("run_completed", **stats)


def load_config(path: str) -> FilterConfig:
    if not os.path.exists(path):
        return FilterConfig()
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return FilterConfig(
        audience=AudienceConfig(**data.get("audience", {})),
        creator=CreatorConfig(**data.get("creator", {})),
        performance=PerformanceConfig(**data.get("performance", {})),
        output=OutputConfig(**data.get("output", {})),
    )


def _csv_arg(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _read_seed_file(path: str | None) -> list[str]:
    if not path:
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return [
            line.strip().lstrip("@")
            for line in handle
            if line.strip() and not line.strip().startswith("#")
        ]


async def main():
    parser = argparse.ArgumentParser(description="DijkstraBot - Instagram Influencer Intelligence")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML filter config")
    parser.add_argument("--interactive", "--wizard", action="store_true", help="Prompt for campaign filters")
    parser.add_argument("--output-dir", default=None, help="Local output directory")
    parser.add_argument("--max-results", type=int, help="Cap total exported profiles")
    parser.add_argument("--follower-min", type=int, help="Minimum followers")
    parser.add_argument("--follower-max", type=int, help="Maximum followers")
    parser.add_argument("--category", help="Comma-separated categories, e.g. fitness,artist,dancer")
    parser.add_argument("--niche", help="Comma-separated niche terms")
    parser.add_argument("--location-country", help="Country filter")
    parser.add_argument("--location-city", help="City filter")
    parser.add_argument("--hashtags", help="Comma-separated hashtags")
    parser.add_argument("--bio-keywords", help="Comma-separated bio keywords")
    parser.add_argument("--seed-usernames", help="Comma-separated usernames for Meta Business Discovery")
    parser.add_argument("--seed-file", help="File with one Instagram username per line")
    parser.add_argument("--export-format", choices=["csv", "xlsx", "both"], default=None)
    parser.add_argument("--mock-data", action="store_true", help="Use generated mock profiles when APIs return no data")
    parser.add_argument("--allow-empty-export", action="store_true", help="Write CSV/XLSX even when filters return zero profiles")
    parser.add_argument("--profile-fetch-limit", type=int, help="Max full profiles to fetch from credit-based discovery APIs")
    parser.add_argument("--dry-run", action="store_true", help="Fetch first 100 profiles only, skip export")
    parser.add_argument("--schedule", help="Run on cron schedule, e.g. '0 6 * * *'")
    parser.add_argument("--log-level", default="INFO", help="debug | info | warning")
    parser.add_argument("--no-sheets", action="store_true", help="Skip Google Sheets export")
    parser.add_argument("--no-xlsx", action="store_true", help="Skip XLSX export")
    parser.add_argument("--no-csv", action="store_true", help="Skip CSV export")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.interactive:
        config = prompt_for_config(config)

    if args.follower_min is not None:
        config.audience.follower_min = args.follower_min
    if args.follower_max is not None:
        config.audience.follower_max = args.follower_max
    if args.location_country is not None:
        config.audience.location_country = args.location_country
    if args.location_city is not None:
        config.audience.location_city = args.location_city
    if args.category:
        categories = _csv_arg(args.category)
        config.creator.category = categories if len(categories) > 1 else categories[0]
    if args.niche:
        config.creator.niches = _csv_arg(args.niche)
    if args.hashtags:
        config.creator.bio_hashtags = _csv_arg(args.hashtags)
    if args.bio_keywords:
        config.creator.bio_keywords = _csv_arg(args.bio_keywords)
    if args.seed_usernames:
        config.creator.seed_usernames.extend([u.lstrip("@") for u in _csv_arg(args.seed_usernames)])
    if args.seed_file:
        config.creator.seed_usernames.extend(_read_seed_file(args.seed_file))
    config.creator.seed_usernames = sorted(set(config.creator.seed_usernames))
    if args.max_results:
        config.output.max_results = args.max_results
    if args.output_dir:
        config.output.output_dir = args.output_dir
    if args.export_format:
        config.output.export_format = args.export_format
    if args.profile_fetch_limit is not None:
        config.output.profile_fetch_limit = args.profile_fetch_limit
    if args.mock_data:
        config.output.use_mock_data = True
    if args.allow_empty_export:
        config.output.allow_empty_export = True

    if args.schedule:
        start_scheduler(
            run_discovery,
            args.schedule,
            config,
            args.dry_run,
            args.no_sheets,
            args.no_xlsx,
            args.no_csv,
        )
        while True:
            await asyncio.sleep(1)
    else:
        await run_discovery(config, args.dry_run, args.no_sheets, args.no_xlsx, args.no_csv)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        logger.error("run_failed", error=str(exc))
        raise SystemExit(1)

import asyncio
import argparse
import yaml
import os
import time
from datetime import datetime
from dotenv import load_dotenv

from dijkstrabot.filters import FilterConfig, AudienceConfig, CreatorConfig, PerformanceConfig, OutputConfig, apply_filters
from dijkstrabot.discovery import discover_all
from dijkstrabot.enrichment import enrich_profile
from dijkstrabot.scoring import compute_dijkstra_score
from dijkstrabot.exporter import SheetsExporter, XLSXExporter
from dijkstrabot.scheduler import start_scheduler
from dijkstrabot.utils.logger import logger

load_dotenv()

async def process_profile(raw, config):
    enriched = await enrich_profile(raw, config)
    enriched.dijkstra_score = compute_dijkstra_score(enriched, config)
    return enriched

async def run_discovery(config: FilterConfig, dry_run: bool = False, no_sheets: bool = False, no_xlsx: bool = False):
    start_time = time.time()

    # 1. Discover
    raw_profiles = await discover_all(config)
    if dry_run: raw_profiles = raw_profiles[:100]

    # 2. Enrich & Score (Concurrent)
    logger.info("enrichment_started", count=len(raw_profiles))
    tasks = [process_profile(raw, config) for raw in raw_profiles]
    enriched_profiles = await asyncio.gather(*tasks)

    # 3. Filter
    final_profiles = apply_filters(enriched_profiles, config)

    # 4. Export
    stats = {
        "profiles_fetched": len(raw_profiles),
        "profiles_enriched": len(enriched_profiles),
        "profiles_filtered": len(final_profiles),
        "run_duration_seconds": round(time.time() - start_time, 2),
        "timestamp": datetime.now().isoformat()
    }

    if not dry_run:
        if not no_xlsx:
            xlsx_exporter = XLSXExporter()
            xlsx_exporter.export(final_profiles)

        if not no_sheets:
            sheets_exporter = SheetsExporter(
                service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json"),
                folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
            )
            await sheets_exporter.export(final_profiles, stats)

    logger.info("run_completed", **stats)

def load_config(path: str) -> FilterConfig:
    if not os.path.exists(path): return FilterConfig()
    with open(path, "r") as f: data = yaml.safe_load(f)
    return FilterConfig(
        audience=AudienceConfig(**data.get("audience", {})),
        creator=CreatorConfig(**data.get("creator", {})),
        performance=PerformanceConfig(**data.get("performance", {})),
        output=OutputConfig(**data.get("output", {}))
    )

async def main():
    parser = argparse.ArgumentParser(description="DijkstraBot — Instagram Influencer Intelligence")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML filter config")
    parser.add_argument("--output-dir", default="./output", help="Local output directory")
    parser.add_argument("--max-results", type=int, help="Cap total exported profiles")
    parser.add_argument("--dry-run", action="store_true", help="Fetch first 100 profiles only, skip export")
    parser.add_argument("--schedule", help="Run on cron schedule (e.g. '0 6 * * *')")
    parser.add_argument("--log-level", default="INFO", help="debug | info | warning")
    parser.add_argument("--no-sheets", action="store_true", help="Skip Google Sheets export")
    parser.add_argument("--no-xlsx", action="store_true", help="Skip XLSX export")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.max_results: config.output.max_results = args.max_results
    if args.schedule:
        start_scheduler(run_discovery, args.schedule, config, args.dry_run, args.no_sheets, args.no_xlsx)
        while True: await asyncio.sleep(1)
    else:
        await run_discovery(config, args.dry_run, args.no_sheets, args.no_xlsx)

if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from apify_client import ApifyClient

from backend.app.core.config import get_settings


settings = get_settings()


@dataclass(slots=True)
class ApifyRunResult:
    run_id: str | None
    items: list[dict[str, Any]]


class ApifyService:
    def __init__(self) -> None:
        self.client = ApifyClient(settings.apify_token) if settings.apify_token else None

    def is_configured(self) -> bool:
        return self.client is not None

    async def call_actor(self, actor_id: str, run_input: dict[str, Any], max_items: int | None = None) -> ApifyRunResult:
        if not self.client:
            raise RuntimeError("APIFY_TOKEN is not configured")

        def _call() -> ApifyRunResult:
            run = self.client.actor(actor_id).call(run_input=run_input)
            if run is None:
                return ApifyRunResult(run_id=None, items=[])
            dataset = self.client.dataset(run.default_dataset_id)
            items = dataset.list_items(clean=True, limit=max_items or 1000).items
            return ApifyRunResult(run_id=run.id, items=list(items))

        return await asyncio.to_thread(_call)

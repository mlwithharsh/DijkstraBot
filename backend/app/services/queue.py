from __future__ import annotations

import json
from dataclasses import dataclass

import redis.asyncio as redis

from backend.app.core.config import get_settings


settings = get_settings()


@dataclass(slots=True)
class QueueMessage:
    job_type: str
    payload: dict


class RedisQueue:
    def __init__(self) -> None:
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        self.high_key = "influencer_jobs:high"
        self.normal_key = "influencer_jobs:normal"
        self.low_key = "influencer_jobs:low"

    async def enqueue(self, job_type: str, payload: dict, priority: str = "normal") -> None:
        message = json.dumps({"job_type": job_type, "payload": payload})
        key = self._key(priority)
        await self.redis.lpush(key, message)

    async def pop(self, timeout: int = 5) -> QueueMessage | None:
        result = await self.redis.brpop([self.high_key, self.normal_key, self.low_key], timeout=timeout)
        if not result:
            return None
        _, raw = result
        data = json.loads(raw)
        return QueueMessage(job_type=data["job_type"], payload=data["payload"])

    def _key(self, priority: str) -> str:
        return {"high": self.high_key, "normal": self.normal_key, "low": self.low_key}.get(priority, self.normal_key)

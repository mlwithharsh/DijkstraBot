import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
from dijkstrabot.models import RawProfile
from dijkstrabot.utils.rate_limiter import RateLimiter
from dijkstrabot.utils.logger import logger
import random

class PhylloDiscovery:
    BASE_URL = "https://api.getphyllo.com/v1"
    def __init__(self, client_id: str, client_secret: str):
        self.auth = aiohttp.BasicAuth(client_id, client_secret)
        self.rate_limiter = RateLimiter(300)

    async def search_creators(self, session: aiohttp.ClientSession, filters: Dict[str, Any], max_items: int = 5000) -> List[RawProfile]:
        all_profiles = []
        page = 1
        page_size = 500

        while len(all_profiles) < max_items:
            await self.rate_limiter.acquire()
            url = f"{self.BASE_URL}/creators/search"
            payload = {"platform": "instagram", "page": page, "page_size": page_size, **filters}

            try:
                async with session.post(url, json=payload, auth=self.auth) as response:
                    if response.status == 200:
                        data = await response.json()
                        raw_items = data.get("data", [])
                        if not raw_items: break
                        all_profiles.extend([self._map_profile(item) for item in raw_items])
                        page += 1
                        if len(raw_items) < page_size: break
                    elif response.status == 429:
                        await asyncio.sleep(5)
                        continue
                    else:
                        logger.error("phyllo_api_error", status=response.status)
                        break
            except Exception as e:
                logger.error("phyllo_request_exception", error=str(e))
                break
        return all_profiles

    def _map_profile(self, item: Dict[str, Any]) -> RawProfile:
        return RawProfile(
            username=item.get("handle") or item.get("username", "unknown"),
            full_name=item.get("full_name"),
            biography=item.get("biography"),
            follower_count=item.get("follower_count", 0),
            following_count=item.get("following_count", 0),
            media_count=item.get("media_count", 0),
            avg_likes=item.get("avg_likes"),
            avg_comments=item.get("avg_comments"),
            is_verified=item.get("is_verified", False),
            profile_pic_url=item.get("profile_pic_url"),
            external_url=item.get("external_url"),
            gender=item.get("gender"),
            api_category=item.get("category"),
            source_api="phyllo",
            fetched_at=datetime.now()
        )

class RapidAPIDiscovery:
    BASE_URL = "https://instagram-data1.p.rapidapi.com"
    def __init__(self, api_key: str):
        self.headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "instagram-data1.p.rapidapi.com"}
        self.rate_limiter = RateLimiter(100)

    async def search_by_hashtag(self, session: aiohttp.ClientSession, hashtag: str) -> List[RawProfile]:
        await self.rate_limiter.acquire()
        url = f"{self.BASE_URL}/hashtag/feed"
        params = {"hashtag": hashtag}
        try:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("items", [])
                    return [self._map_profile(item) for item in items]
                return []
        except Exception as e:
            logger.error("rapidapi_request_exception", error=str(e))
            return []

    def _map_profile(self, item: Dict[str, Any]) -> RawProfile:
        user = item.get("user", {})
        return RawProfile(
            username=user.get("username", "unknown"),
            full_name=user.get("full_name"),
            biography=user.get("biography"),
            follower_count=user.get("follower_count", 0),
            following_count=user.get("following_count", 0),
            media_count=user.get("media_count", 0),
            avg_likes=None,
            avg_comments=None,
            is_verified=user.get("is_verified", False),
            profile_pic_url=user.get("profile_pic_url"),
            external_url=user.get("external_url"),
            gender=None,
            api_category=None,
            source_api="rapidapi",
            fetched_at=datetime.now()
        )

async def discover_all(config: Any) -> List[RawProfile]:
    import os
    client_id = os.getenv("PHYLLO_CLIENT_ID")
    client_secret = os.getenv("PHYLLO_SECRET")
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    semaphore = asyncio.Semaphore(50)

    async def bounded_search(discovery_obj, session, filters):
        async with semaphore:
            if isinstance(discovery_obj, PhylloDiscovery):
                return await discovery_obj.search_creators(session, filters, max_items=config.output.max_results)
            elif isinstance(discovery_obj, RapidAPIDiscovery):
                return await discovery_obj.search_by_hashtag(session, filters.get("hashtag", ""))
            return []

    all_profiles = []
    if client_id and client_secret:
        phyllo = PhylloDiscovery(client_id, client_secret)
        async with aiohttp.ClientSession() as session:
            categories = config.creator.category
            if not categories: categories = [None]
            elif isinstance(categories, str): categories = [categories]

            # Map filters to API
            api_filters = {
                "follower_count_min": config.audience.follower_min,
                "follower_count_max": config.audience.follower_max,
            }
            if config.audience.location_country: api_filters["location"] = config.audience.location_country

            tasks = [bounded_search(phyllo, session, {**api_filters, "category": cat} if cat else api_filters) for cat in categories]
            results = await asyncio.gather(*tasks)
            for res in results: all_profiles.extend(res)

    if not all_profiles and rapidapi_key:
        logger.info("falling_back_to_rapidapi")
        rapidapi = RapidAPIDiscovery(rapidapi_key)
        async with aiohttp.ClientSession() as session:
            hashtags = config.creator.bio_hashtags or ["instagram"]
            tasks = [bounded_search(rapidapi, session, {"hashtag": h.strip("#")}) for h in hashtags]
            results = await asyncio.gather(*tasks)
            for res in results: all_profiles.extend(res)

    if not all_profiles:
        logger.info("using_mock_data_fallback")
        categories = ["lifestyle", "artist", "fitness", "tech", "beauty"]
        bios = {
            "lifestyle": "Living my best life. #lifestyle #wellness",
            "artist": "Creative soul, painter and illustrator. Visit my gallery.",
            "fitness": "Gym rat. Personal trainer. #fitnessmotivation",
            "tech": "Software engineer. AI enthusiast.",
            "beauty": "Makeup artist. Skincare lover."
        }
        for i in range(100):
            cat = random.choice(categories)
            followers = random.randint(10000, 2000000)
            all_profiles.append(RawProfile(
                username=f"user_{i}",
                full_name=f"Influencer {i}",
                biography=bios[cat] + " Based in Mumbai.",
                follower_count=followers,
                following_count=random.randint(100, 2000),
                media_count=random.randint(50, 1000),
                avg_likes=followers * 0.03,
                avg_comments=followers * 0.005,
                is_verified=followers > 500000,
                source_api="mock",
                fetched_at=datetime.now()
            ))

    unique_profiles = {p.username: p for p in all_profiles}
    logger.info("discovery_completed", count=len(unique_profiles))
    return list(unique_profiles.values())

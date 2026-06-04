import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
from dijkstrabot.models import RawProfile
from dijkstrabot.utils.rate_limiter import RateLimiter
from dijkstrabot.utils.logger import logger
import random
import re

LAST_DISCOVERY_DIAGNOSTICS: List[str] = []


def _diagnostic(message: str) -> None:
    LAST_DISCOVERY_DIAGNOSTICS.append(message)


def get_last_discovery_diagnostics() -> List[str]:
    return list(LAST_DISCOVERY_DIAGNOSTICS)


def _safe_body(text: str, limit: int = 200) -> str:
    redacted = re.sub(r"Authorization=[^\"'\s}]+", "Authorization=<redacted>", text)
    return redacted[:limit]


def _first_value(value: Any) -> Optional[str]:
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value else None


TOPYAPPERS_CATEGORY_MAP = {
    "artist": "Arts",
    "arts": "Arts",
    "beauty": "Beauty & Personal Care",
    "business": "Business",
    "dancer": "Entertainment",
    "dance": "Entertainment",
    "education": "Education",
    "fashion": "Fashion",
    "fitness": "Fitness",
    "food": "Food",
    "gaming": "Gaming",
    "lifestyle": "Lifestyle",
    "music": "Music",
    "photography": "Photography",
    "sports": "Sports",
    "tech": "Technology",
    "technology": "Technology",
    "travel": "Travel",
}


class TopYappersDiscovery:
    BASE_URL = "https://api.topyappers.com"

    def __init__(self, api_key: str, profile_fetch_limit: int = 10):
        self.headers = {"x-ty-api-key": api_key, "Content-Type": "application/json"}
        self.profile_fetch_limit = max(0, profile_fetch_limit)
        self.rate_limiter = RateLimiter(50)

    def build_params(self, config: Any, page: int, per_page: int) -> Dict[str, Any]:
        category = _first_value(config.creator.category)
        params: Dict[str, Any] = {
            "source": "instagram",
            "followersMin": config.audience.follower_min,
            "followersMax": config.audience.follower_max,
            "page": page,
            "perPage": per_page,
            "sortBy": "followers" if config.output.sort_by == "follower_count" else "engagement_rate",
            "sortOrder": "desc",
        }
        if config.audience.location_country:
            params["country"] = config.audience.location_country
        if category:
            params["mainCategory"] = TOPYAPPERS_CATEGORY_MAP.get(category.lower(), category.title())
        if config.creator.gender in {"male", "female"}:
            params["gender"] = config.creator.gender
        if config.creator.bio_keywords:
            params["bio"] = ",".join(config.creator.bio_keywords)
        if config.creator.bio_hashtags:
            params["hashtags"] = ",".join([tag.lstrip("#") for tag in config.creator.bio_hashtags])
        if getattr(config.creator, "niches", None):
            params["nichesToPromote"] = ",".join(config.creator.niches)
        if config.performance.min_engagement_rate:
            params["engagementRateMin"] = config.performance.min_engagement_rate
        return {k: v for k, v in params.items() if v not in (None, "", [])}

    async def search_creator_ids(self, session: aiohttp.ClientSession, config: Any, max_ids: int) -> List[str]:
        user_ids: List[str] = []
        per_page = min(100, max(1, max_ids))
        page = 1
        while len(user_ids) < max_ids:
            await self.rate_limiter.acquire()
            params = self.build_params(config, page, per_page)
            url = f"{self.BASE_URL}/api/v2/creators/search"
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 429:
                        data = await response.json(content_type=None)
                        retry_after = int(data.get("retryAfter") or response.headers.get("Retry-After") or 60)
                        logger.warning("topyappers_rate_limited", retry_after=retry_after)
                        await asyncio.sleep(retry_after)
                        continue
                    body = await response.text()
                    if response.status != 200:
                        _diagnostic(f"TopYappers search failed with HTTP {response.status}: {_safe_body(body)}")
                        logger.error("topyappers_search_error", status=response.status, body=_safe_body(body))
                        break
                    data = await response.json(content_type=None)
                    response_obj = data.get("response") or {}
                    batch = [str(item) for item in response_obj.get("data", []) if item]
                    user_ids.extend(batch)
                    next_page = response_obj.get("next_page")
                    if not batch or not next_page:
                        break
                    page = int(next_page)
            except Exception as e:
                _diagnostic(f"TopYappers search exception: {str(e)[:200]}")
                logger.error("topyappers_search_exception", error=str(e))
                break
        unique_ids = list(dict.fromkeys(user_ids))
        logger.info("topyappers_search_completed", ids=len(unique_ids))
        return unique_ids[:max_ids]

    async def get_profiles(self, session: aiohttp.ClientSession, user_ids: List[str]) -> List[RawProfile]:
        if not user_ids:
            return []
        if self.profile_fetch_limit <= 0:
            _diagnostic("TopYappers search returned matching IDs, but profile_fetch_limit is 0 so no paid/credit profile fetch was attempted.")
            return []

        selected_ids = user_ids[: self.profile_fetch_limit]
        all_profiles: List[RawProfile] = []
        for start in range(0, len(selected_ids), 100):
            batch = selected_ids[start:start + 100]
            await self.rate_limiter.acquire()
            url = f"{self.BASE_URL}/api/v2/creators/get"
            try:
                async with session.post(url, headers=self.headers, json={"userIds": batch}) as response:
                    body = await response.text()
                    credits = response.headers.get("x-ty-credits")
                    if response.status == 429:
                        data = await response.json(content_type=None)
                        retry_after = int(data.get("retryAfter") or response.headers.get("Retry-After") or 60)
                        logger.warning("topyappers_get_rate_limited", retry_after=retry_after)
                        await asyncio.sleep(retry_after)
                        continue
                    if response.status != 200:
                        _diagnostic(f"TopYappers profile fetch failed with HTTP {response.status}: {_safe_body(body)}")
                        logger.error("topyappers_get_error", status=response.status, body=_safe_body(body), credits=credits)
                        continue
                    data = await response.json(content_type=None)
                    items = (data.get("response") or {}).get("data", [])
                    all_profiles.extend([self._map_profile(item) for item in items])
                    logger.info("topyappers_get_completed", fetched=len(items), credits_remaining=credits)
            except Exception as e:
                _diagnostic(f"TopYappers profile fetch exception: {str(e)[:200]}")
                logger.error("topyappers_get_exception", error=str(e))
        return all_profiles

    async def discover(self, session: aiohttp.ClientSession, config: Any) -> List[RawProfile]:
        max_ids = min(max(config.output.max_results, self.profile_fetch_limit), 1000)
        user_ids = await self.search_creator_ids(session, config, max_ids=max_ids)
        if user_ids:
            _diagnostic(f"TopYappers free search found {len(user_ids)} matching creator IDs. Fetching full profiles is capped at {self.profile_fetch_limit} to protect credits/free tier.")
        return await self.get_profiles(session, user_ids)

    def _map_profile(self, item: Dict[str, Any]) -> RawProfile:
        handle = str(item.get("handle") or item.get("username") or "unknown").lstrip("@")
        websites = item.get("websites") or []
        categories = item.get("categories") or []
        hashtags = item.get("hashtags") or []
        country = item.get("country")
        bio_parts = [item.get("bio") or item.get("description") or ""]
        if hashtags:
            bio_parts.append(" ".join([f"#{str(tag).lstrip('#')}" for tag in hashtags]))
        if country:
            bio_parts.append(f"Based in {country}.")
        return RawProfile(
            username=handle,
            full_name=item.get("nickname") or item.get("full_name"),
            biography=" ".join([part for part in bio_parts if part]),
            follower_count=int(item.get("followers") or 0),
            following_count=int(item.get("following") or 0),
            media_count=int(item.get("total_videos") or 0),
            avg_likes=item.get("avg_likes"),
            avg_comments=item.get("avg_comments"),
            is_verified=bool(item.get("is_verified") or False),
            profile_pic_url=item.get("avatar_url"),
            external_url=item.get("main_website") or (websites[0] if websites else None),
            gender=item.get("gender"),
            api_category=(item.get("main_category") or (categories[0] if categories else None)),
            source_api="topyappers",
            fetched_at=datetime.now(),
        )

class MetaGraphDiscovery:
    """
    Uses Instagram Graph API (Facebook Login) Business Discovery to fetch public
    profile metadata (incl. followers_count) for *professional* accounts.
    Requires a token that has access to at least one connected IG professional user.
    """

    BASE_URL = "https://graph.facebook.com"

    def __init__(self, access_token: str, api_version: str = "v22.0"):
        self.access_token = access_token
        self.api_version = api_version
        self.rate_limiter = RateLimiter(200)  # keep conservative

    async def get_connected_ig_user_id(self, session: aiohttp.ClientSession) -> Optional[str]:
        """
        Attempts to discover an IG professional user id connected to this token.
        """
        await self.rate_limiter.acquire()
        url = f"{self.BASE_URL}/{self.api_version}/me/accounts"
        params = {
            "fields": "instagram_business_account",
            "access_token": self.access_token,
        }
        try:
            async with session.get(url, params=params) as resp:
                data = await resp.json(content_type=None)
                if resp.status != 200:
                    logger.error("meta_accounts_error", status=resp.status, body=str(data)[:500])
                    return None
                for page in data.get("data", []) or []:
                    iba = page.get("instagram_business_account")
                    if iba and iba.get("id"):
                        return str(iba["id"])
                logger.error("meta_no_instagram_business_account", body=str(data)[:500])
                return None
        except Exception as e:
            logger.error("meta_accounts_exception", error=str(e))
            return None

    async def business_discovery(self, session: aiohttp.ClientSession, ig_user_id: str, username: str) -> Optional[RawProfile]:
        await self.rate_limiter.acquire()
        url = f"{self.BASE_URL}/{self.api_version}/{ig_user_id}"
        fields = (
            f"business_discovery.username({username})"
            "{username,name,biography,followers_count,follows_count,media_count,profile_picture_url,website}"
        )
        params = {"fields": fields, "access_token": self.access_token}
        try:
            async with session.get(url, params=params) as resp:
                data = await resp.json(content_type=None)
                if resp.status != 200:
                    logger.error("meta_business_discovery_error", status=resp.status, username=username, body=str(data)[:500])
                    return None
                bd = data.get("business_discovery") or {}
                if not bd or not bd.get("username"):
                    return None
                return RawProfile(
                    username=bd.get("username", "unknown"),
                    full_name=bd.get("name"),
                    biography=bd.get("biography"),
                    follower_count=int(bd.get("followers_count") or 0),
                    following_count=int(bd.get("follows_count") or 0),
                    media_count=int(bd.get("media_count") or 0),
                    avg_likes=None,
                    avg_comments=None,
                    is_verified=False,  # not available via business discovery fields list in our query
                    profile_pic_url=bd.get("profile_picture_url"),
                    external_url=bd.get("website"),
                    gender=None,
                    api_category=None,
                    source_api="meta_graph",
                    fetched_at=datetime.now(),
                )
        except Exception as e:
            logger.error("meta_business_discovery_exception", username=username, error=str(e))
            return None

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
                        body = await response.text()
                        safe_body = _safe_body(body)
                        _diagnostic(f"Phyllo discovery failed with HTTP {response.status}: {safe_body}")
                        logger.error("phyllo_api_error", status=response.status, body=safe_body)
                        break
            except Exception as e:
                _diagnostic(f"Phyllo discovery exception: {str(e)[:200]}")
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
        url = f"{self.BASE_URL}/hashtag/feed"
        params = {"hashtag": hashtag}

        # Retry on throttling; RapidAPI often returns 429 bursts.
        max_retries = 5
        attempt = 0
        while True:
            attempt += 1
            await self.rate_limiter.acquire()
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("items", [])
                        return [self._map_profile(item) for item in items]

                    body = await response.text()
                    short_body = str(body)[:500]

                    if response.status == 429 and attempt <= max_retries:
                        # Exponential backoff with jitter.
                        backoff_s = min(60, (2 ** (attempt - 1))) + random.random()
                        logger.warning(
                            "rapidapi_rate_limited_retry",
                            status=response.status,
                            hashtag=hashtag,
                            attempt=attempt,
                            backoff_seconds=round(backoff_s, 2),
                        )
                        await asyncio.sleep(backoff_s)
                        continue

                    if response.status == 403:
                        # Subscription/entitlement issue: don't keep retrying.
                        _diagnostic(f"RapidAPI hashtag '{hashtag}' failed with HTTP 403. The key is not subscribed/entitled to this Instagram API.")
                        logger.error(
                            "rapidapi_forbidden",
                            status=response.status,
                            hashtag=hashtag,
                            body=short_body,
                        )
                        return []

                    logger.error(
                        "rapidapi_hashtag_error",
                        status=response.status,
                        hashtag=hashtag,
                        body=short_body,
                    )
                    return []
            except Exception as e:
                if attempt <= max_retries:
                    backoff_s = min(30, (2 ** (attempt - 1))) + random.random()
                    logger.warning(
                        "rapidapi_request_exception_retry",
                        hashtag=hashtag,
                        attempt=attempt,
                        backoff_seconds=round(backoff_s, 2),
                        error=str(e)[:200],
                    )
                    await asyncio.sleep(backoff_s)
                    continue
                logger.error("rapidapi_request_exception", error=str(e))
                _diagnostic(f"RapidAPI hashtag '{hashtag}' request exception: {str(e)[:200]}")
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
    LAST_DISCOVERY_DIAGNOSTICS.clear()
    client_id = os.getenv("PHYLLO_CLIENT_ID")
    client_secret = os.getenv("PHYLLO_SECRET")
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    meta_token = os.getenv("META_ACCESS_TOKEN")
    meta_ig_user_id = os.getenv("META_IG_USER_ID")
    topyappers_key = os.getenv("TOPYAPPERS_API_KEY")
    env_profile_fetch_limit = os.getenv("TOPYAPPERS_PROFILE_FETCH_LIMIT")
    profile_fetch_limit = getattr(config.output, "profile_fetch_limit", 10)
    if env_profile_fetch_limit:
        try:
            profile_fetch_limit = int(env_profile_fetch_limit)
        except ValueError:
            _diagnostic("TOPYAPPERS_PROFILE_FETCH_LIMIT is not a valid integer; using config value.")
    semaphore = asyncio.Semaphore(50)
    
    async def bounded_search(discovery_obj, session, filters):
        async with semaphore:
            if isinstance(discovery_obj, PhylloDiscovery):
                return await discovery_obj.search_creators(session, filters, max_items=config.output.max_results)
            elif isinstance(discovery_obj, RapidAPIDiscovery):
                return await discovery_obj.search_by_hashtag(session, filters.get("hashtag", ""))
            return []

    all_profiles = []

    if topyappers_key:
        logger.info("using_topyappers_discovery", profile_fetch_limit=profile_fetch_limit)
        topyappers = TopYappersDiscovery(topyappers_key, profile_fetch_limit=profile_fetch_limit)
        async with aiohttp.ClientSession() as session:
            all_profiles.extend(await topyappers.discover(session, config))

    # Official Meta Graph API cannot search Instagram globally by hashtag,
    # category, follower range, or location. If the user provides seed handles,
    # Business Discovery can resolve public professional accounts for filtering.
    seed_usernames = [
        username.strip().lstrip("@")
        for username in getattr(config.creator, "seed_usernames", [])
        if username and username.strip()
    ]
    if seed_usernames and meta_token:
        logger.info("using_meta_graph_seed_resolution", count=len(seed_usernames))
        meta = MetaGraphDiscovery(meta_token)
        async with aiohttp.ClientSession() as session:
            ig_user_id = meta_ig_user_id or await meta.get_connected_ig_user_id(session)
            if ig_user_id:
                meta_sem = asyncio.Semaphore(10)

                async def resolve(username: str) -> Optional[RawProfile]:
                    async with meta_sem:
                        return await meta.business_discovery(session, ig_user_id, username)

                for start in range(0, len(seed_usernames), 500):
                    batch = seed_usernames[start:start + 500]
                    resolved = await asyncio.gather(*[resolve(username) for username in batch])
                    for profile in resolved:
                        if profile:
                            all_profiles.append(profile)
                    if len(all_profiles) >= config.output.max_results:
                        break
            else:
                _diagnostic("Meta seed resolution skipped: META_IG_USER_ID is missing/invalid and no connected Instagram professional account was found from /me/accounts.")
                logger.error("meta_graph_seed_resolution_skipped", reason="no_connected_ig_user_id")

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
                
    # Hybrid discovery path:
    # Seed usernames from RapidAPI hashtag feed, then resolve each via Meta Business Discovery.
    if not all_profiles and meta_token and rapidapi_key:
        logger.info("using_meta_graph_discovery")
        rapidapi = RapidAPIDiscovery(rapidapi_key)
        meta = MetaGraphDiscovery(meta_token)
        async with aiohttp.ClientSession() as session:
            ig_user_id = meta_ig_user_id or await meta.get_connected_ig_user_id(session)
            if ig_user_id:
                hashtags = config.creator.bio_hashtags or []
                # If user didn't provide hashtags, derive a few from category as a best-effort seed.
                if not hashtags:
                    cat = config.creator.category
                    if isinstance(cat, str) and cat:
                        hashtags = [cat, "wellness", "selfcare", "lifestyle"]
                    else:
                        hashtags = ["lifestyle", "wellness"]

                # Fetch hashtags sequentially to avoid burst throttling.
                seed_profiles: List[RawProfile] = []
                for h in hashtags:
                    res = await bounded_search(rapidapi, session, {"hashtag": h.strip("#")})
                    seed_profiles.extend(res)
                    if len(seed_profiles) >= 2000:
                        break
                usernames = list({p.username for p in seed_profiles if p.username and p.username != "unknown"})

                # Resolve usernames via Meta Business Discovery (professional accounts only).
                meta_sem = asyncio.Semaphore(10)
                async def resolve(u: str) -> Optional[RawProfile]:
                    async with meta_sem:
                        return await meta.business_discovery(session, ig_user_id, u)

                resolved = await asyncio.gather(*[resolve(u) for u in usernames[:2000]])
                for p in resolved:
                    if p:
                        all_profiles.append(p)
            else:
                _diagnostic("Meta Business Discovery skipped: no connected Instagram professional user id was available.")
                logger.error("meta_graph_discovery_skipped", reason="no_connected_ig_user_id")

    if not all_profiles and rapidapi_key:
        logger.info("falling_back_to_rapidapi")
        rapidapi = RapidAPIDiscovery(rapidapi_key)
        async with aiohttp.ClientSession() as session:
            hashtags = config.creator.bio_hashtags or ["instagram"]
            # Sequential fallback to reduce rate-limit bursts.
            for h in hashtags:
                res = await bounded_search(rapidapi, session, {"hashtag": h.strip("#")})
                all_profiles.extend(res)
                if len(all_profiles) >= config.output.max_results:
                    break

    if not all_profiles and getattr(config.output, "use_mock_data", False):
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
    elif not all_profiles:
        if not any([topyappers_key, client_id and client_secret, rapidapi_key, meta_token]):
            _diagnostic("No discovery credentials configured. Add TopYappers, Phyllo, RapidAPI, or Meta seed credentials, or run with --mock-data for local testing.")
        else:
            _diagnostic("No profiles discovered from configured providers. Check API credentials, subscriptions, permissions, and seed usernames.")

    unique_profiles = {p.username: p for p in all_profiles}
    logger.info("discovery_completed", count=len(unique_profiles))
    return list(unique_profiles.values())

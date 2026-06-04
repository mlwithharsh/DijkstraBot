import asyncio
import os

import aiohttp
from dotenv import load_dotenv


async def main() -> None:
    load_dotenv()
    cid = os.getenv("PHYLLO_CLIENT_ID")
    sec = os.getenv("PHYLLO_SECRET")
    print("PHYLLO_CLIENT_ID set:", bool(cid))
    print("PHYLLO_SECRET set:", bool(sec))

    url = "https://api.getphyllo.com/v1/creators/search"
    payload = {
        "platform": "instagram",
        "page": 1,
        "page_size": 5,
        "follower_count_min": 50_000,
        "follower_count_max": 100_000,
        "category": "lifestyle",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, auth=aiohttp.BasicAuth(cid or "", sec or "")) as resp:
            print("status:", resp.status)
            print("content-type:", resp.headers.get("content-type"))
            body = await resp.text()
            print("body (first 2000 chars):")
            print(body[:2000])


if __name__ == "__main__":
    asyncio.run(main())


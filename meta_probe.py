import json
import os
import asyncio

import aiohttp
from dotenv import load_dotenv


async def fetch(session: aiohttp.ClientSession, url: str, params: dict) -> tuple[int, str]:
    async with session.get(url, params=params) as resp:
        text = await resp.text()
        return resp.status, text


async def main() -> None:
    load_dotenv()
    token = os.getenv("META_ACCESS_TOKEN")
    print("META_ACCESS_TOKEN set:", bool(token))
    if not token:
        return

    base = "https://graph.facebook.com/v22.0"
    async with aiohttp.ClientSession() as session:
        status, body = await fetch(
            session,
            f"{base}/me/accounts",
            {"fields": "instagram_business_account,name", "access_token": token},
        )
        print("/me/accounts status:", status)
        print("/me/accounts body (first 2000 chars):")
        print(body[:2000])


if __name__ == "__main__":
    asyncio.run(main())


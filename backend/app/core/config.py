from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "India Influencer Finder"
    api_prefix: str = "/api"
    environment: str = "development"

    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@db:5432/influencer_finder")
    redis_url: str = Field(default="redis://redis:6379/0")

    apify_token: str = ""
    apify_google_actor: str = "apify/google-search-scraper"
    apify_instagram_actor: str = "apify/instagram-profile-scraper"
    apify_youtube_actor: str = "scrapio/youtube-scraper"
    apify_max_profiles_per_day: int = 100
    apify_google_pages_per_query: int = 2
    apify_instagram_profile_limit: int = 10

    frontend_origin: str = "http://localhost:3000"

    # Optional hosted Supabase compatibility.
    supabase_url: str = ""
    supabase_service_role_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

# India Influencer Finder

Production-ready MVP for discovering Indian Instagram creator profiles from public web sources, enriching the profiles through Apify, classifying them, and storing everything in PostgreSQL-compatible Supabase tables.

## What It Does

- Discovers public Instagram profile URLs from Google search results, public creator directories, YouTube channel references, and user-imported URLs.
- Enriches each Instagram profile through Apify's `apify/instagram-profile-scraper`.
- Classifies creators into the requested categories.
- Detects India signals from bios and profile text.
- Stores rows in `influencers` and refresh events in `refresh_jobs`.
- Supports manual refresh and scheduled refresh based on follower count.
- Exposes a FastAPI search API and a Next.js dashboard.

## Apify Strategy

This MVP does not use Meta Graph API for discovery.

Recommended Apify actors:

- `apify/google-search-scraper` for discovery
- `apify/instagram-profile-scraper` for enrichment

For low-cost operation, the app:

- Uses Google search to discover public URLs.
- Limits enrichment with `APIFY_INSTAGRAM_PROFILE_LIMIT`.
- Limits daily discovery with `APIFY_MAX_PROFILES_PER_DAY`.

You can swap actor IDs later through environment variables without changing application code.

## Folder Structure

```text
backend/
  app/
    api.py
    core/
    models.py
    repositories/
    services/
    worker.py
    scheduler.py
  Dockerfile
  requirements.txt
frontend/
  app/
  Dockerfile
  package.json
supabase/
  schema.sql
  migrations/001_init.sql
docker-compose.yml
.env.example
```

## Local Run

1. Copy `.env.example` to `.env` and fill in values.
2. Start the stack:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- FastAPI: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Environment

Required:

- `DATABASE_URL`
- `REDIS_URL`
- `APIFY_TOKEN`

Recommended:

- `APIFY_GOOGLE_ACTOR`
- `APIFY_INSTAGRAM_ACTOR`
- `APIFY_YOUTUBE_ACTOR`
- `APIFY_MAX_PROFILES_PER_DAY`
- `APIFY_INSTAGRAM_PROFILE_LIMIT`

For hosted Supabase, point `DATABASE_URL` at the Supabase PostgreSQL connection string.

## Database

Apply `supabase/schema.sql` or `supabase/migrations/001_init.sql` to your database.

The app creates tables on startup in local development as a convenience, but the SQL files are the source of truth for production.

## API

### Search

`GET /api/search`

Query parameters:

- `country`
- `category`
- `min_followers`
- `max_followers`
- `verified`

### Stats

`GET /api/stats`

### Discovery

`POST /api/discover`

Body:

- `source`: `google`, `directories`, or `youtube`
- `query`: optional custom search query
- `max_results`: cap for the job

### Manual Import

`POST /api/import`

Body:

- `urls`: list of Instagram profile URLs

### Manual Refresh

`POST /api/refresh`

Body:

- `profile_urls`: list of Instagram profile URLs

## Refresh Policy

- `followers > 100k`: refresh every 3 days
- `10k-100k`: refresh weekly
- `under 10k`: refresh monthly

## Notes

- The dashboard is intentionally simple and operational.
- The worker and scheduler are separate processes so discovery, refresh, and UI requests do not block each other.
- This MVP is built to demo tomorrow and to grow later, not to depend on brittle Meta discovery paths.

create extension if not exists pgcrypto;

create table if not exists public.influencers (
    id uuid primary key default gen_random_uuid(),
    username text not null unique,
    profile_url text not null unique,
    full_name text,
    bio text,
    followers bigint,
    following bigint,
    posts bigint,
    displayed_category text,
    derived_category text,
    country text,
    email text,
    external_url text,
    verified boolean not null default false,
    source text not null default 'apify',
    confidence_score double precision,
    country_confidence double precision,
    last_updated timestamptz not null default now(),
    created_at timestamptz not null default now(),
    next_refresh_at timestamptz
);

create index if not exists influencers_country_idx on public.influencers(country);
create index if not exists influencers_displayed_category_idx on public.influencers(displayed_category);
create index if not exists influencers_derived_category_idx on public.influencers(derived_category);
create index if not exists influencers_followers_idx on public.influencers(followers);
create index if not exists influencers_last_updated_idx on public.influencers(last_updated);

create table if not exists public.refresh_jobs (
    id uuid primary key default gen_random_uuid(),
    profile_url text not null,
    status text not null default 'pending',
    source text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists refresh_jobs_status_idx on public.refresh_jobs(status);
create index if not exists refresh_jobs_profile_url_idx on public.refresh_jobs(profile_url);

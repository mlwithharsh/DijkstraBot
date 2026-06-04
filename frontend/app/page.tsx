"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

type InfluencerRow = {
  username: string;
  profile_url: string;
  full_name?: string | null;
  followers?: number | null;
  displayed_category?: string | null;
  derived_category?: string | null;
  country?: string | null;
  verified: boolean;
  last_updated?: string | null;
};

type Stats = {
  total_influencers: number;
  by_country: Record<string, number>;
  by_category: Record<string, number>;
  follower_buckets: Record<string, number>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

export default function Page() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [rows, setRows] = useState<InfluencerRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [country, setCountry] = useState("India");
  const [category, setCategory] = useState("");
  const [minFollowers, setMinFollowers] = useState("10000");
  const [maxFollowers, setMaxFollowers] = useState("500000");
  const [verified, setVerified] = useState("all");

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (country) params.set("country", country);
    if (category) params.set("category", category);
    if (minFollowers) params.set("min_followers", minFollowers);
    if (maxFollowers) params.set("max_followers", maxFollowers);
    if (verified !== "all") params.set("verified", verified);
    params.set("limit", "100");
    return params.toString();
  }, [country, category, minFollowers, maxFollowers, verified]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, searchData] = await Promise.all([
        fetchJson<Stats>("/stats"),
        fetchJson<{ items: InfluencerRow[] }>(`/search?${query}`),
      ]);
      setStats(statsData);
      setRows(searchData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="min-h-screen px-6 py-8 lg:px-10">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-2xl border border-line bg-panel/85 p-6 shadow-soft backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="text-sm uppercase tracking-[0.25em] text-sky-300/80">India Influencer Finder</div>
              <h1 className="mt-2 text-3xl font-semibold text-white">Indian Instagram creator intelligence</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">
                Discover public profiles from Google, creator directories, YouTube links, and manual imports. Enrich them through Apify, classify them locally, and keep the database ready for daily refresh.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <Metric label="Total" value={stats?.total_influencers ?? 0} />
              <Metric label="India" value={stats?.by_country?.India ?? 0} />
              <Metric label="100k+" value={stats?.follower_buckets?.[">100k"] ?? 0} />
            </div>
          </div>
        </header>

        <section className="grid gap-4 rounded-2xl border border-line bg-panel/70 p-4 lg:grid-cols-5">
          <Field label="Country" value={country} onChange={setCountry} />
          <Field label="Category" value={category} onChange={setCategory} placeholder="Fitness" />
          <Field label="Min followers" value={minFollowers} onChange={setMinFollowers} />
          <Field label="Max followers" value={maxFollowers} onChange={setMaxFollowers} />
          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase tracking-[0.2em] text-slate-400">Verified</label>
            <select
              value={verified}
              onChange={(e) => setVerified(e.target.value)}
              className="h-11 rounded-xl border border-line bg-panel2 px-3 text-sm outline-none"
            >
              <option value="all">All</option>
              <option value="true">Verified</option>
              <option value="false">Unverified</option>
            </select>
          </div>
          <button
            onClick={() => void load()}
            className="col-span-full h-11 rounded-xl bg-sky-400 px-4 text-sm font-semibold text-slate-950 transition hover:bg-sky-300"
          >
            Refresh results
          </button>
        </section>

        {error ? (
          <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div>
        ) : null}

        <section className="overflow-hidden rounded-2xl border border-line bg-panel/70">
          <div className="border-b border-line px-4 py-3 text-sm text-slate-300">
            Search results
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-line text-left text-sm">
              <thead className="bg-panel2/80 text-slate-300">
                <tr>
                  <Th>Username</Th>
                  <Th>Followers</Th>
                  <Th>Displayed category</Th>
                  <Th>Derived category</Th>
                  <Th>Country</Th>
                  <Th>Updated</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {loading ? (
                  <tr>
                    <td className="px-4 py-6 text-slate-400" colSpan={6}>Loading...</td>
                  </tr>
                ) : rows.length ? (
                  rows.map((row) => (
                    <tr key={row.profile_url} className="hover:bg-white/5">
                      <Td>
                        <a href={row.profile_url} target="_blank" rel="noreferrer" className="font-medium text-sky-300 hover:text-sky-200">
                          @{row.username}
                        </a>
                      </Td>
                      <Td>{row.followers?.toLocaleString() ?? "-"}</Td>
                      <Td>{row.displayed_category ?? "-"}</Td>
                      <Td>{row.derived_category ?? "-"}</Td>
                      <Td>{row.country ?? "-"}</Td>
                      <Td>{row.last_updated ? new Date(row.last_updated).toLocaleString() : "-"}</Td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-4 py-6 text-slate-400" colSpan={6}>No profiles found for the current filters.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-line bg-panel2 px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-white">{value.toLocaleString()}</div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="h-11 rounded-xl border border-line bg-panel2 px-3 text-sm outline-none placeholder:text-slate-500"
      />
    </label>
  );
}

function Th({ children }: { children: ReactNode }) {
  return <th className="px-4 py-3 font-medium">{children}</th>;
}

function Td({ children }: { children: ReactNode }) {
  return <td className="px-4 py-3 align-top text-slate-200">{children}</td>;
}

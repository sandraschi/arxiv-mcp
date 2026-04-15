import { useState } from "react";
import { ExternalLink, Download } from "lucide-react";
import { apiGet, apiPost } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";
import { cn } from "@/lib/utils";

type Source = {
  id: string;
  label: string;
  js_heavy: boolean;
  sections: string[];
  known_keys: string[];
};

type PostSummary = {
  title: string;
  url: string;
  slug: string;
  published: string;
  summary: string;
};

type FetchResult = {
  success: boolean;
  source?: string;
  label?: string;
  title: string;
  published: string;
  summary: string;
  url: string;
  word_count: number;
  via?: string;
  ingested: boolean;
  error?: string;
};

// Known short keys grouped by source — seed list, user can type anything
const KNOWN_KEYS: Record<string, string[]> = {
  anthropic: [
    "model-welfare", "claude-character", "alignment-faking",
    "taking-ai-welfare-seriously", "core-views", "claude-soul",
    "model-spec", "interpretability-monosemanticity",
  ],
  "google-research": ["responsible-ai-progress", "pair"],
  deepmind: ["agi-path", "gemini-deep-think", "alphafold3", "sima"],
  "google-ai": ["responsible-ai-2026", "research-breakthroughs-2025"],
};

const SOURCE_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  "google-research": "Google Research",
  deepmind: "Google DeepMind",
  "google-ai": "Google AI Blog",
};

const VIA_LABEL: Record<string, string> = {
  html: "Direct HTML",
  jina: "Via Jina Reader",
  html_thin: "HTML (thin — Jina fallback attempted)",
};

export function LabBlogPage() {
  const { log } = useLogger();
  const [activeSource, setActiveSource] = useState("anthropic");
  const [listing, setListing] = useState<PostSummary[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [sources, setSources] = useState<Source[]>([]);

  const [slugInput, setSlugInput] = useState("");
  const [fetchResult, setFetchResult] = useState<FetchResult | null>(null);
  const [fetchLoading, setFetchLoading] = useState(false);
  const [ingestOnFetch, setIngestOnFetch] = useState(false);

  // Load source list once
  async function ensureSources() {
    if (sources.length > 0) return;
    try {
      const data = await apiGet<{ sources: Source[] }>("/api/lab/sources");
      setSources(data.sources);
    } catch (e) {
      log("error", String(e));
    }
  }

  async function loadListing() {
    await ensureSources();
    setListLoading(true);
    setListing([]);
    try {
      const data = await apiGet<{ posts: PostSummary[]; count: number }>(
        `/api/lab/posts?source=${activeSource}&limit=30`
      );
      setListing(data.posts);
      log("info", `${SOURCE_LABELS[activeSource] ?? activeSource}: ${data.count} posts`);
    } catch (e) {
      log("error", String(e));
    } finally {
      setListLoading(false);
    }
  }

  async function fetchPost(slugOrUrl: string) {
    if (!slugOrUrl.trim()) return;
    setFetchLoading(true);
    setFetchResult(null);
    try {
      const data = await apiPost<FetchResult>("/api/lab/fetch", {
        slug_or_url: slugOrUrl.trim(),
        ingest: ingestOnFetch,
      });
      setFetchResult(data);
      log(
        "info",
        `Fetched "${data.title}" [${data.source ?? "?"}] (${data.word_count} words, ${data.via ?? "?"})${data.ingested ? " — ingested" : ""}`
      );
    } catch (e) {
      log("error", String(e));
    } finally {
      setFetchLoading(false);
    }
  }

  async function ingestCurrent() {
    if (!fetchResult) return;
    setFetchLoading(true);
    try {
      const data = await apiPost<FetchResult>("/api/lab/fetch", {
        slug_or_url: fetchResult.url,
        ingest: true,
      });
      setFetchResult(data);
      log("info", `Ingested "${data.title}"`);
    } catch (e) {
      log("error", String(e));
    } finally {
      setFetchLoading(false);
    }
  }

  const currentKeys = KNOWN_KEYS[activeSource] ?? [];
  const isJsHeavy = sources.find((s) => s.id === activeSource)?.js_heavy ?? false;

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Primary sources"
        title="AI lab blogs"
        lead="Fetch posts from Anthropic, Google Research, Google DeepMind, and the Google AI Blog. Optionally ingest them into your local depot alongside arXiv papers."
      />

      {/* Source selector */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(SOURCE_LABELS).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => { setActiveSource(id); setListing([]); setFetchResult(null); }}
            className={cn(
              "px-3 py-1.5 text-sm rounded-full border transition-colors",
              activeSource === id
                ? "border-primary bg-primary/10 text-primary font-medium"
                : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {isJsHeavy && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
          This source uses client-side rendering. Post fetch automatically falls back to Jina Reader for full content. Listing may be sparse.
        </div>
      )}

      {/* Quick fetch buttons */}
      {currentKeys.length > 0 && (
        <Card>
          <CardTitle>Quick fetch — known posts</CardTitle>
          <div className="mt-3 flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                checked={ingestOnFetch}
                onChange={(e) => setIngestOnFetch(e.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              Ingest into corpus after fetch
            </label>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {currentKeys.map((k) => {
              const key = activeSource === "anthropic" ? k : `${activeSource}:${k}`;
              return (
                <Button
                  key={k}
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => { setSlugInput(key); fetchPost(key); }}
                  disabled={fetchLoading}
                >
                  {k}
                </Button>
              );
            })}
          </div>
        </Card>
      )}

      {/* Manual fetch */}
      <Card>
        <CardTitle>Fetch by key, slug, or URL</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Short key (e.g. <code className="text-xs font-mono">model-welfare</code>),
          source-prefixed (<code className="text-xs font-mono">deepmind:agi-path</code>),
          path, or full URL from any supported domain.
        </p>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
          <Input
            value={slugInput}
            onChange={(e) => setSlugInput(e.target.value)}
            placeholder="model-welfare  or  deepmind:agi-path  or  full URL…"
            className="flex-1"
            onKeyDown={(e) => e.key === "Enter" && fetchPost(slugInput)}
          />
          <Button
            type="button"
            onClick={() => fetchPost(slugInput)}
            disabled={fetchLoading || !slugInput.trim()}
          >
            {fetchLoading ? "Fetching…" : "Fetch"}
          </Button>
        </div>

        {fetchResult && (
          <div className="mt-5 space-y-3">
            <div className="rounded-lg border border-border/50 bg-muted/20 p-4 space-y-2">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="font-semibold text-base">{fetchResult.title}</div>
                {fetchResult.label && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground shrink-0">
                    {fetchResult.label}
                  </span>
                )}
              </div>
              {fetchResult.published && (
                <div className="text-xs text-muted-foreground">{fetchResult.published}</div>
              )}
              {fetchResult.summary && (
                <p className="text-sm text-muted-foreground">{fetchResult.summary}</p>
              )}
              <div className="flex flex-wrap gap-3 items-center pt-1">
                <span className="text-xs text-muted-foreground">
                  {fetchResult.word_count?.toLocaleString()} words
                </span>
                {fetchResult.via && (
                  <span className="text-xs text-muted-foreground">
                    {VIA_LABEL[fetchResult.via] ?? fetchResult.via}
                  </span>
                )}
                {fetchResult.ingested && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                    Ingested
                  </span>
                )}
                <a
                  href={fetchResult.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  Open original <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
            {!fetchResult.ingested && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="gap-1.5"
                onClick={ingestCurrent}
                disabled={fetchLoading}
              >
                <Download className="h-4 w-4" />
                Ingest into corpus
              </Button>
            )}
          </div>
        )}
      </Card>

      {/* Listing browser */}
      <Card>
        <CardTitle>Browse {SOURCE_LABELS[activeSource] ?? activeSource} posts</CardTitle>
        {isJsHeavy && (
          <p className="text-xs text-muted-foreground mt-1">
            JS-rendered site — listing may be incomplete. Use known keys above or fetch by full URL.
          </p>
        )}
        <div className="mt-3">
          <Button type="button" variant="secondary" onClick={loadListing} disabled={listLoading}>
            {listLoading ? "Loading…" : "Load listing"}
          </Button>
        </div>

        {listing.length > 0 && (
          <ul className="mt-5 space-y-3">
            {listing.map((p) => {
              const key = activeSource === "anthropic" ? p.slug : `${activeSource}:${p.slug}`;
              return (
                <li
                  key={p.url}
                  className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between rounded-lg border border-border/40 px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-sm truncate">{p.title}</div>
                    {p.published && (
                      <div className="text-xs text-muted-foreground mt-0.5">{p.published}</div>
                    )}
                    {p.summary && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{p.summary}</p>
                    )}
                  </div>
                  <div className="flex gap-2 shrink-0 mt-2 sm:mt-0 sm:ml-4">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => { setSlugInput(key); fetchPost(key); }}
                      disabled={fetchLoading}
                    >
                      Fetch
                    </Button>
                    <a href={p.url} target="_blank" rel="noreferrer">
                      <Button type="button" size="sm" variant="ghost">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </a>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        {listing.length === 0 && !listLoading && (
          <p className="text-sm text-muted-foreground mt-4">Click "Load listing" to browse posts.</p>
        )}
      </Card>
    </div>
  );
}

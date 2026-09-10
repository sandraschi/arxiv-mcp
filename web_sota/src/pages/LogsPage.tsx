import {
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiGet } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { type LogLevel, useLogger } from "@/context/LoggerContext";
import { type ChatMessage, chatComplete, loadSelection } from "@/lib/llm";
import { cn } from "@/lib/utils";

type ServerEntry = {
  id: string;
  ts: string;
  level: string;
  message: string;
  source: string;
  logger?: string;
};

const LEVELS: { key: LogLevel | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "info", label: "Info" },
  { key: "warn", label: "Warn" },
  { key: "error", label: "Error" },
  { key: "debug", label: "Debug" },
];

export function LogsPage() {
  const { entries: clientEntries, clear, log } = useLogger();
  const [levelFilter, setLevelFilter] = useState<LogLevel | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [serverEntries, setServerEntries] = useState<ServerEntry[]>([]);
  const [_totalServer, setTotalServer] = useState(0);
  const [loadingServer, setLoadingServer] = useState(false);
  const [sourceFilter, setSourceFilter] = useState<"all" | "client" | "server">(
    "all",
  );
  const [page, setPage] = useState(0);
  const pageSize = 100;
  const scrollRef = useRef<HTMLDivElement>(null);
  // Newest-first is the default; toggle for chronological reading.
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<{
    model: string;
    content: string;
  } | null>(null);
  const [exportingAll, setExportingAll] = useState(false);

  const fetchServer = useCallback(async () => {
    if (sourceFilter === "client") return;
    setLoadingServer(true);
    try {
      const p = new URLSearchParams({
        limit: String(pageSize),
        offset: String(page * pageSize),
      });
      if (levelFilter !== "all") p.set("level", levelFilter);
      if (searchQuery) p.set("search", searchQuery);
      const data = await apiGet<{ entries: ServerEntry[]; total: number }>(
        `/api/logs?${p}`,
      );
      setServerEntries(data.entries);
      setTotalServer(data.total);
    } catch (e) {
      log("error", `Failed to fetch server logs: ${e}`);
    }
    setLoadingServer(false);
  }, [page, levelFilter, searchQuery, sourceFilter, log]);

  useEffect(() => {
    if (sourceFilter !== "client") fetchServer();
  }, [fetchServer, sourceFilter]);

  const mergedRaw = useMemo(() => {
    if (sourceFilter === "server") {
      let items = serverEntries;
      if (levelFilter !== "all")
        items = items.filter(
          (e) =>
            e.level === levelFilter ||
            (levelFilter === "warn" && e.level === "warning"),
        );
      if (searchQuery)
        items = items.filter((e) =>
          e.message.toLowerCase().includes(searchQuery.toLowerCase()),
        );
      const total = items.length;
      return {
        entries: items.slice(page * pageSize, (page + 1) * pageSize),
        total,
      };
    }
    if (sourceFilter === "client") {
      let items = clientEntries.map((e) => ({
        ...e,
        source: "client" as const,
      }));
      if (levelFilter !== "all")
        items = items.filter((e) => e.level === levelFilter);
      if (searchQuery)
        items = items.filter((e) =>
          e.message.toLowerCase().includes(searchQuery.toLowerCase()),
        );
      items.reverse();
      const total = items.length;
      return {
        entries: items.slice(page * pageSize, (page + 1) * pageSize),
        total,
      };
    }
    // "all" — merge both sources
    let items: ServerEntry[] = [
      ...serverEntries,
      ...clientEntries.map((e) => ({ ...e, source: "client" as const })),
    ];
    if (levelFilter !== "all")
      items = items.filter(
        (e) =>
          e.level === levelFilter ||
          (levelFilter === "warn" && e.level === "warning"),
      );
    if (searchQuery)
      items = items.filter((e) =>
        e.message.toLowerCase().includes(searchQuery.toLowerCase()),
      );
    items.sort((a, b) => (a.ts < b.ts ? 1 : -1));
    const total = items.length;
    return {
      entries: items.slice(page * pageSize, (page + 1) * pageSize),
      total,
    };
  }, [
    clientEntries,
    serverEntries,
    levelFilter,
    searchQuery,
    page,
    sourceFilter,
  ]);

  const totalPages = Math.max(1, Math.ceil(mergedRaw.total / pageSize));

  // Display order: newest-first default, chronological on toggle.
  const merged = useMemo(() => {
    if (sortDir === "asc")
      return {
        total: mergedRaw.total,
        entries: [...mergedRaw.entries].reverse(),
      };
    return mergedRaw;
  }, [mergedRaw, sortDir]);

  const handleExportJSON = useCallback(() => {
    const blob = new Blob([JSON.stringify(merged.entries, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `arxiv-mcp-logs-${levelFilter}-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [merged.entries, levelFilter]);

  const handleExportCSV = useCallback(() => {
    const header = "ts,level,source,message\n";
    const rows = merged.entries
      .map(
        (e) =>
          `"${e.ts}","${e.level}","${e.source}","${(e.message || "").replace(/"/g, '""')}"`,
      )
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `arxiv-mcp-logs-${levelFilter}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [merged.entries, levelFilter]);

  // Export the FULL server buffer, not just the current view: page through
  // /api/logs to its total (capped), then download one JSON file.
  const handleExportAll = useCallback(async () => {
    setExportingAll(true);
    try {
      const first = await apiGet<{ entries: ServerEntry[]; total: number }>(
        `/api/logs?limit=1&offset=0`,
      );
      const total = Math.min(first.total, 20000);
      const all: ServerEntry[] = [];
      for (let off = 0; off < total; off += 1000) {
        const d = await apiGet<{ entries: ServerEntry[]; total: number }>(
          `/api/logs?limit=1000&offset=${off}`,
        );
        all.push(...d.entries);
        if (d.entries.length === 0) break;
      }
      const blob = new Blob([JSON.stringify(all, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `arxiv-mcp-logs-full-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      log("info", `Exported full server buffer: ${all.length} entries`);
    } catch (e) {
      log("error", `Full export failed: ${e}`);
    }
    setExportingAll(false);
  }, [log]);

  // AI analyze: send the current view (capped + truncated) to the selected
  // model with an analyst prompt. Reuses chatComplete — no new backend.
  const handleAnalyze = useCallback(async () => {
    const sel = loadSelection();
    const m = (sel.model || "").trim();
    if (!m) {
      setAnalysis({
        model: "",
        content: "No model selected — pick one in AI settings first.",
      });
      return;
    }
    if (merged.entries.length === 0) {
      setAnalysis({
        model: m,
        content: "Nothing to analyze — the current view is empty.",
      });
      return;
    }
    setAnalyzing(true);
    try {
      const corpus = merged.entries
        .slice(0, 120)
        .map(
          (e) =>
            `${e.ts} [${e.level}] (${e.source}) ${(e.message || "").slice(0, 300)}`,
        )
        .join("\n")
        .slice(0, 14000);
      const msgs: ChatMessage[] = [
        {
          role: "system",
          content:
            "You are a log analyst for a research MCP server. Given log entries, report: 1) error clusters (repeated failures with counts), 2) warnings worth attention, 3) performance anomalies (slow calls, retries), 4) one-line health verdict. Be terse. Quote exact messages sparingly.",
        },
        {
          role: "user",
          content: `Analyze these ${merged.entries.length} log entries (level filter: ${levelFilter}):\n\n${corpus}`,
        },
      ];
      const out = await chatComplete(sel.provider || "ollama", m, msgs);
      setAnalysis({ model: m, content: out });
      if (scrollRef.current)
        scrollRef.current.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
    } catch (e) {
      setAnalysis({ model: m, content: `Analysis failed: ${e}` });
    }
    setAnalyzing(false);
  }, [merged.entries, levelFilter]);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Diagnostics"
        title="Logs"
        lead="Client-side (browser) + server-side log buffer. Server entries persist in a ring buffer (up to 5000)."
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1">
          {LEVELS.map((lv) => (
            <button
              key={lv.key}
              type="button"
              onClick={() => {
                setLevelFilter(lv.key);
                setPage(0);
              }}
              className={cn(
                "px-3 py-1 rounded-md text-xs font-medium transition-colors",
                levelFilter === lv.key
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {lv.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1">
          {(["all", "client", "server"] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setSourceFilter(s);
                setPage(0);
              }}
              className={cn(
                "px-2.5 py-1 rounded-md text-xs font-medium transition-colors",
                sourceFilter === s
                  ? "bg-secondary text-secondary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {s === "all" ? "Both" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        <div className="relative flex-1 min-w-[160px] max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(0);
            }}
            placeholder="Search messages..."
            className="pl-8 h-8 text-xs"
          />
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            clear();
            setServerEntries([]);
          }}
        >
          <Trash2 className="h-3.5 w-3.5 mr-1" /> Clear
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={fetchServer}
          disabled={loadingServer}
        >
          <RefreshCw
            className={cn("h-3.5 w-3.5 mr-1", loadingServer && "animate-spin")}
          />{" "}
          Refresh
        </Button>
        <Button variant="outline" size="sm" onClick={handleExportJSON}>
          <Download className="h-3.5 w-3.5 mr-1" /> JSON
        </Button>
        <Button variant="outline" size="sm" onClick={handleExportCSV}>
          <Download className="h-3.5 w-3.5 mr-1" /> CSV
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void handleExportAll()}
          disabled={exportingAll}
          title="Download the full server buffer (all pages), not just this view"
        >
          <Download className="h-3.5 w-3.5 mr-1" />
          {exportingAll ? "Exporting…" : "Full"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
          title={
            sortDir === "desc"
              ? "Newest first — switch to chronological"
              : "Chronological — switch to newest first"
          }
        >
          <ArrowUpDown className="h-3.5 w-3.5 mr-1" />
          {sortDir === "desc" ? "Newest" : "Oldest"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void handleAnalyze()}
          disabled={analyzing}
          title="Ask the selected model to analyze the current view"
        >
          <Sparkles className="h-3.5 w-3.5 mr-1" />
          {analyzing ? "Analyzing…" : "Analyze"}
        </Button>
      </div>

      {analysis && (
        <Card data-testid="log-analysis">
          <div className="flex items-center justify-between">
            <CardTitle>
              Analysis{analysis.model ? ` · ${analysis.model}` : ""}
            </CardTitle>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  void navigator.clipboard
                    .writeText(analysis.content)
                    .catch(() => {});
                }}
                title="Copy analysis"
              >
                <Copy className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setAnalysis(null)}
                title="Dismiss"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
          <p className="mt-2 text-sm whitespace-pre-wrap break-words">
            {analyzing ? "Analyzing…" : analysis.content}
          </p>
        </Card>
      )}

      <Card>
        <CardTitle>
          Entries ({merged.total})
          {sourceFilter !== "client" &&
          !loadingServer &&
          serverEntries.length === 0 &&
          merged.total === 0
            ? " — pull server logs with Refresh"
            : null}
        </CardTitle>
        <div
          ref={scrollRef}
          className="mt-4 max-h-[60vh] overflow-y-auto space-y-1 font-mono text-sm"
        >
          {merged.entries.length === 0 && (
            <p className="text-muted-foreground">
              No log entries match the current filters.
            </p>
          )}
          {merged.entries.map((e: ServerEntry) => (
            <div
              key={e.id}
              className="border-b border-border/30 py-1.5 flex gap-2"
            >
              <span
                className="text-muted-foreground shrink-0 w-20 truncate"
                title={e.ts}
              >
                {e.ts.slice(11, 23)}
              </span>
              <span
                className={cn(
                  "uppercase w-12 shrink-0 font-semibold",
                  e.level === "error" && "text-destructive",
                  e.level === "warn" && "text-amber-500",
                  e.level === "debug" && "text-muted-foreground",
                  e.level === "info" && "text-primary",
                )}
              >
                {e.level}
              </span>
              {e.source ? (
                <span className="text-muted-foreground w-12 shrink-0 text-xs">
                  {e.source}
                </span>
              ) : null}
              <span className="break-all">{e.message}</span>
            </div>
          ))}
        </div>

        {totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between border-t border-border/30 pt-3">
            <span className="text-xs text-muted-foreground">
              Page {page + 1} of {totalPages} ({merged.total} total)
            </span>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

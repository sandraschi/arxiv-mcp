import { ArrowRight, CheckCheck, Inbox, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";
import {
  type FavoriteEntry,
  type HistoryEntry,
  loadFavorites,
  loadHistory,
  removeFavorite,
  removeHistoryEntry,
} from "@/lib/searchQueryStorage";

type InboxItem = {
  id: string;
  kind: "query" | "favorite";
  label: string;
  detail: string;
  at: number;
};

function toItems(
  history: HistoryEntry[],
  favorites: FavoriteEntry[],
): InboxItem[] {
  const items: InboxItem[] = [];
  for (const h of history) {
    items.push({
      id: `q:${h.id}`,
      kind: "query",
      label: h.q,
      detail: `Searched ${new Date(h.at).toLocaleString()}`,
      at: h.at,
    });
  }
  for (const f of favorites) {
    items.push({
      id: `f:${f.id}`,
      kind: "favorite",
      label: f.q,
      detail: `Favorite${f.topic ? ` · ${f.topic}` : ""}`,
      at: f.at,
    });
  }
  return items.sort((a, b) => b.at - a.at);
}

export function InboxPage() {
  const { log } = useLogger();
  const [history, setHistory] = useState<HistoryEntry[]>(() => {
    try {
      return loadHistory();
    } catch {
      return [];
    }
  });
  const [favorites, setFavorites] = useState<FavoriteEntry[]>(() => {
    try {
      return loadFavorites();
    } catch {
      return [];
    }
  });
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  const items = useMemo(() => {
    const all = toItems(history, favorites);
    const q = filter.trim().toLowerCase();
    if (!q) return all;
    return all.filter((i) => i.label.toLowerCase().includes(q));
  }, [history, favorites, filter]);

  function dismiss(item: InboxItem) {
    try {
      if (item.kind === "query") {
        setHistory(removeHistoryEntry(item.id.slice(2)));
      } else {
        setFavorites(removeFavorite(item.id.slice(2)));
      }
      log("info", `Inbox: dismissed ${item.kind} ${item.label.slice(0, 60)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Dismiss failed — retry.");
    }
  }

  function dismissAll() {
    try {
      for (const item of items) {
        if (item.kind === "query") removeHistoryEntry(item.id.slice(2));
        else removeFavorite(item.id.slice(2));
      }
      setHistory(loadHistory());
      setFavorites(loadFavorites());
      log("info", `Inbox: cleared ${items.length} items`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Clear failed — retry.");
    }
  }

  return (
    <div className="space-y-8" data-testid="inbox">
      <PageHero eyebrow="Triage queue" title="Inbox" size="large">
        <p className="text-muted-foreground text-sm md:text-base">
          Recent searches and favorites waiting for review. Re-run a query, open
          it in Search, or dismiss it when handled.
        </p>
      </PageHero>

      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-52" data-testid="inbox-search">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter inbox…"
              aria-label="Filter inbox"
              className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <span
            className="text-sm text-muted-foreground"
            data-testid="inbox-count"
          >
            {items.length} open item{items.length === 1 ? "" : "s"}
          </span>
          {items.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={dismissAll}
              data-testid="inbox-clear"
            >
              <CheckCheck className="h-4 w-4" /> Mark all handled
            </Button>
          )}
        </div>
        {error && (
          <div
            className="mt-4 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm"
            data-testid="inbox-error"
          >
            {error}{" "}
            <Button variant="ghost" size="sm" onClick={() => setError(null)}>
              Retry
            </Button>
          </div>
        )}
      </Card>

      {items.length === 0 ? (
        <Card>
          <div
            className="flex flex-col items-center gap-3 py-10 text-center"
            data-testid="inbox-empty"
          >
            <Inbox className="h-10 w-10 text-muted-foreground" />
            <CardTitle>All caught up</CardTitle>
            <p className="text-sm text-muted-foreground max-w-md">
              Nothing waiting. Run a search to start a new research thread — it
              will land here for triage.
            </p>
            <Link to="/search">
              <Button size="sm">
                Search arXiv <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.id} data-testid="inbox-item">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{item.label}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {item.kind === "favorite" ? "Favorite" : "Recent query"} ·{" "}
                    {item.detail}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Link
                    to={`/search?q=${encodeURIComponent(item.label)}`}
                    data-testid="inbox-open"
                  >
                    <Button variant="outline" size="sm">
                      Open <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Dismiss ${item.label}`}
                    onClick={() => dismiss(item)}
                    data-testid="inbox-dismiss"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

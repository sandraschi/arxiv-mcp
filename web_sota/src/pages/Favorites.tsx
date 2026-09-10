import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpen,
  ExternalLink,
  Plus,
  Search,
  Star,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiDelete, apiGet, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogger } from "@/context/LoggerContext";
import { cn } from "@/lib/utils";

type Fav = {
  arxiv_id: string;
  title: string | null;
  note: string | null;
  created_at: number;
};

type DepotPaper = {
  arxiv_id: string;
  title: string;
  primary_mode?: string | null;
};

export function Favorites() {
  const { log } = useLogger();
  const [list, setList] = useState<Fav[]>([]);
  const [depotPapers, setDepotPapers] = useState<DepotPaper[]>([]);
  const [selectedDepotId, setSelectedDepotId] = useState("");
  const [depotSearch, _setDepotSearch] = useState("");

  // External add state
  const [showManualAdd, setShowManualAdd] = useState(false);
  const [manualId, setManualId] = useState("");
  const [manualTitle, setManualTitle] = useState("");
  const [manualNote, setManualNote] = useState("");

  // Favorites search filter
  const [filterQuery, setFilterQuery] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await apiGet<{ favorites: Fav[] }>("/api/favorites");
      setList(data.favorites || []);
    } catch (e) {
      log("error", String(e));
    }
  }, [log]);

  const loadDepot = useCallback(async () => {
    try {
      const data = await apiGet<{ ingested: DepotPaper[] }>(
        "/api/corpus?limit=500",
      );
      setDepotPapers(data.ingested || []);
    } catch {
      // Non-fatal
    }
  }, []);

  useEffect(() => {
    load();
    loadDepot();
  }, [load, loadDepot]);

  // Candidates in depot not yet favorited
  const availableDepotPapers = useMemo(() => {
    const existing = new Set(list.map((f) => f.arxiv_id));
    let available = depotPapers.filter((p) => !existing.has(p.arxiv_id));
    if (depotSearch.trim()) {
      const q = depotSearch.toLowerCase().trim();
      available = available.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.arxiv_id.toLowerCase().includes(q),
      );
    }
    return available;
  }, [depotPapers, list, depotSearch]);

  async function addFromDepot() {
    if (!selectedDepotId) return;
    const paper = depotPapers.find((p) => p.arxiv_id === selectedDepotId);
    try {
      await apiPost("/api/favorites", {
        arxiv_id: selectedDepotId,
        title: paper?.title || null,
        note: null,
      });
      log("info", `Favorited ${selectedDepotId} from depot`);
      setSelectedDepotId("");
      await load();
    } catch (e) {
      log("error", String(e));
    }
  }

  async function addManual() {
    if (!manualId.trim()) return;
    try {
      await apiPost("/api/favorites", {
        arxiv_id: manualId.trim(),
        title: manualTitle.trim() || null,
        note: manualNote.trim() || null,
      });
      log("info", `Favorited external paper ${manualId}`);
      setManualId("");
      setManualTitle("");
      setManualNote("");
      setShowManualAdd(false);
      await load();
    } catch (e) {
      log("error", String(e));
    }
  }

  async function remove(arxivId: string) {
    try {
      await apiDelete(`/api/favorites/${encodeURIComponent(arxivId)}`);
      await load();
    } catch (e) {
      log("error", String(e));
    }
  }

  const filteredList = useMemo(() => {
    if (!filterQuery.trim()) return list;
    const q = filterQuery.toLowerCase().trim();
    return list.filter(
      (f) =>
        f.arxiv_id.toLowerCase().includes(q) ||
        f.title?.toLowerCase().includes(q) ||
        f.note?.toLowerCase().includes(q),
    );
  }, [list, filterQuery]);

  return (
    <div className="space-y-6" data-testid="favorites-page">
      <PageHero
        eyebrow="Bookmarks"
        title="Favorite papers"
        lead="Saved papers with 1-click access to the Depot Reader and arXiv references. Star papers from the Depot or pick them below."
      />

      {/* Add Workflow Card */}
      <Card>
        <CardTitle className="text-sm font-semibold">
          Add to Favorites
        </CardTitle>

        {/* Primary flow: Pick from Depot */}
        <div className="mt-3 space-y-3">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <div className="flex-1 relative">
              <select
                value={selectedDepotId}
                onChange={(e) => setSelectedDepotId(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">
                  {availableDepotPapers.length === 0
                    ? "All depot papers are already favorited"
                    : "Select a paper from your Depot..."}
                </option>
                {availableDepotPapers.map((p) => (
                  <option key={p.arxiv_id} value={p.arxiv_id}>
                    [{p.arxiv_id}] {p.title}
                  </option>
                ))}
              </select>
            </div>
            <Button
              onClick={addFromDepot}
              disabled={!selectedDepotId}
              size="sm"
              className="gap-1.5 h-9 text-xs shrink-0"
            >
              <Star className="h-3.5 w-3.5 fill-current" />
              Add to Favorites
            </Button>
          </div>

          {/* Collapsible Manual external input */}
          <div className="pt-2 border-t border-border/30">
            <button
              type="button"
              onClick={() => setShowManualAdd(!showManualAdd)}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 font-medium transition-colors"
            >
              <Plus
                className={cn(
                  "h-3.5 w-3.5 transition-transform",
                  showManualAdd && "rotate-45",
                )}
              />
              {showManualAdd
                ? "Hide manual arXiv ID entry"
                : "Add paper by raw arXiv ID or external paper"}
            </button>

            <AnimatePresence>
              {showManualAdd && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    <Input
                      placeholder="arXiv ID (e.g. 2401.00001)"
                      value={manualId}
                      onChange={(e) => setManualId(e.target.value)}
                      className="text-xs"
                    />
                    <Input
                      placeholder="Title (optional)"
                      value={manualTitle}
                      onChange={(e) => setManualTitle(e.target.value)}
                      className="text-xs"
                    />
                    <Input
                      placeholder="Personal note (optional)"
                      value={manualNote}
                      onChange={(e) => setManualNote(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <Button
                    size="sm"
                    className="mt-3 text-xs"
                    onClick={addManual}
                    disabled={!manualId.trim()}
                  >
                    Save favorite
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </Card>

      {/* Saved Favorites List */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border/40">
          <div className="flex items-center gap-2">
            <Star className="h-4 w-4 fill-amber-500 text-amber-500" />
            <CardTitle>Saved Papers ({list.length})</CardTitle>
          </div>

          {list.length > 0 && (
            <div className="relative w-full sm:w-64">
              <Search className="h-3.5 w-3.5 text-muted-foreground absolute left-2.5 top-1/2 -translate-y-1/2" />
              <Input
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                placeholder="Filter favorites..."
                className="pl-8 text-xs h-8 bg-background"
              />
              {filterQuery && (
                <button
                  type="button"
                  onClick={() => setFilterQuery("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          )}
        </div>

        {list.length === 0 ? (
          <div className="py-16 text-center text-muted-foreground space-y-2">
            <Star className="h-10 w-10 text-muted-foreground/30 mx-auto stroke-1" />
            <p className="text-sm font-medium">No favorites saved yet</p>
            <p className="text-xs text-muted-foreground/70 max-w-sm mx-auto">
              Click the star icon next to any paper in the Depot or pick one
              above to bookmark it here for quick access.
            </p>
          </div>
        ) : filteredList.length === 0 ? (
          <div className="py-12 text-center text-xs text-muted-foreground">
            No favorites match &quot;{filterQuery}&quot;.
          </div>
        ) : (
          <div className="mt-4 divide-y divide-border/30">
            {filteredList.map((f) => {
              const inDepot = depotPapers.some(
                (p) => p.arxiv_id === f.arxiv_id,
              );
              const formattedDate = f.created_at
                ? new Date(f.created_at * 1000).toLocaleDateString()
                : null;

              return (
                <div
                  key={f.arxiv_id}
                  className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
                >
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-primary">
                        {f.arxiv_id}
                      </span>
                      {inDepot ? (
                        <span className="text-[10px] rounded bg-primary/10 text-primary px-1.5 py-0.5 font-medium">
                          in depot
                        </span>
                      ) : (
                        <span className="text-[10px] rounded bg-muted text-muted-foreground px-1.5 py-0.5">
                          external
                        </span>
                      )}
                      {formattedDate && (
                        <span className="text-[10px] text-muted-foreground">
                          saved {formattedDate}
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-semibold leading-snug">
                      {f.title || f.arxiv_id}
                    </h3>
                    {f.note && (
                      <p className="text-xs text-muted-foreground/90 italic bg-muted/20 p-1.5 rounded-md">
                        {f.note}
                      </p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <Link to={`/depot?focus=${encodeURIComponent(f.arxiv_id)}`}>
                      <Button
                        size="sm"
                        variant="default"
                        className="h-8 text-xs gap-1.5"
                      >
                        <BookOpen className="h-3.5 w-3.5" />
                        Read in Depot
                      </Button>
                    </Link>

                    <a
                      href={`https://arxiv.org/abs/${f.arxiv_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs border border-border/60 hover:bg-muted/50 rounded-md px-2.5 h-8 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      arXiv <ExternalLink className="h-3 w-3" />
                    </a>

                    <a
                      href={`https://arxiv.org/pdf/${f.arxiv_id}.pdf`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs border border-border/60 hover:bg-muted/50 rounded-md px-2.5 h-8 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      PDF <ExternalLink className="h-3 w-3" />
                    </a>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => remove(f.arxiv_id)}
                      className="h-8 px-2 text-muted-foreground hover:text-red-500 hover:bg-red-500/10"
                      title="Remove from favorites"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}

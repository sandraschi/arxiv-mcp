import { AnimatePresence, motion } from "framer-motion";
import {
  BookMarked,
  BookOpen,
  ChevronDown,
  ExternalLink,
  FileText,
  Library,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "@/api/client";
import { cn } from "@/lib/utils";

export type Paper = {
  paper_id: string;
  title: string;
  summary: string;
  authors: string[];
  categories: string[];
  published: string | null;
  server?: string;
  html_url: string | null;
  pdf_url: string | null;
};

type BtnState = "idle" | "storing" | "stored" | "error";

function ActionBtn({
  state,
  error,
  onClick,
  label,
  icon: Icon,
  storedLabel,
  color,
}: {
  state: BtnState;
  error: string | null;
  onClick: () => void;
  label: string;
  icon: typeof Library;
  storedLabel: string;
  color: string;
}) {
  const isDone = state === "stored";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={state === "storing" || isDone}
      className={cn(
        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all whitespace-nowrap",
        isDone
          ? "border-green-600/40 text-green-400 bg-green-950/30 cursor-default"
          : state === "error"
            ? "border-red-500/40 text-red-400 bg-red-950/30 hover:bg-red-950/50"
            : state === "storing"
              ? "border-border/40 text-muted-foreground cursor-wait animate-pulse"
              : color === "primary"
                ? "border-primary/30 text-primary bg-primary/5 hover:bg-primary/10"
                : "border-border/40 text-muted-foreground hover:bg-muted/50 hover:text-foreground",
      )}
      title={error ?? undefined}
      data-testid={`action-${label.toLowerCase().replace(/\s+/g, "-")}`}
    >
      <Icon className={cn("h-3.5 w-3.5", isDone && "text-green-400")} />
      {state === "storing"
        ? `${label}...`
        : state === "stored"
          ? storedLabel
          : state === "error"
            ? "Retry"
            : label}
    </button>
  );
}

const serverColors: Record<string, string> = {
  arxiv: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  biorxiv: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  medrxiv: "bg-teal-500/10 text-teal-400 border-teal-500/20",
  chemrxiv: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  researchsquare: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

export function PaperCard({
  p,
  inDepot,
  onQuickView,
}: {
  p: Paper;
  inDepot?: boolean;
  onQuickView?: (p: Paper) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [storeState, setStoreState] = useState<BtnState>(
    inDepot ? "stored" : "idle",
  );
  const [storeError, setStoreError] = useState<string | null>(null);
  const [calibreState, setCalibreState] = useState<BtnState>("idle");
  const [calibreError, setCalibreError] = useState<string | null>(null);
  const [depotChecked, setDepotChecked] = useState(!!inDepot);

  useEffect(() => {
    if (depotChecked || inDepot) return;
    apiGet<{ arxiv_id: string }>(
      `/api/corpus/item?arxiv_id=${encodeURIComponent(p.paper_id)}`,
    )
      .then(() => {
        setStoreState("stored");
        setDepotChecked(true);
      })
      .catch(() => setDepotChecked(true));
  }, [p.paper_id, inDepot, depotChecked]);

  const handleStore = useCallback(async () => {
    setStoreState("storing");
    setStoreError(null);
    try {
      await apiPost("/api/depot/ingest", { paper_id: p.paper_id });
      setStoreState("stored");
    } catch (e) {
      setStoreState("error");
      setStoreError(String(e));
    }
  }, [p.paper_id]);

  const handleCalibre = useCallback(async () => {
    setCalibreState("storing");
    setCalibreError(null);
    try {
      await apiPost("/api/calibre/ingest", { paper_id: p.paper_id });
      setCalibreState("stored");
    } catch (e) {
      setCalibreState("error");
      setCalibreError(String(e));
    }
  }, [p.paper_id]);

  const absUrl = p.html_url ?? `https://arxiv.org/abs/${p.paper_id}`;

  return (
    <motion.div
      layout
      className="border border-border/40 rounded-xl bg-card/30 hover:bg-card/40 transition-colors"
      data-testid="paper-card"
    >
      <button
        type="button"
        className="p-3 sm:p-4 cursor-pointer w-full text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              {p.server ? (
                <span
                  className={`px-1.5 py-0.5 rounded text-[11px] font-medium border ${serverColors[p.server] || "bg-white/5 text-muted-foreground border-border"}`}
                >
                  {p.server === "researchsquare" ? "R Sq" : p.server}
                </span>
              ) : null}
              {storeState === "stored" && (
                <span className="px-1.5 py-0.5 rounded text-[11px] font-medium border border-green-600/30 text-green-400 bg-green-950/30">
                  In library
                </span>
              )}
            </div>
            <a
              href={absUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-semibold leading-snug text-foreground hover:underline line-clamp-2"
              onClick={(e) => e.stopPropagation()}
            >
              {p.title}
            </a>
            <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
              {p.authors?.slice(0, 5).join(", ")}
              {p.authors?.length > 5 ? ` et al.` : ""}
            </p>
          </div>
          <ChevronDown
            className={cn(
              "h-5 w-5 text-muted-foreground shrink-0 mt-1 transition-transform duration-200",
              expanded && "rotate-180",
            )}
          />
        </div>

        <p
          className={cn(
            "text-xs text-muted-foreground leading-relaxed mt-2",
            expanded ? "" : "line-clamp-2",
          )}
        >
          {p.summary}
        </p>

        {!expanded && (
          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            {p.categories?.slice(0, 3).map((cat) => (
              <span
                key={cat}
                className="px-1.5 py-0.5 rounded text-[11px] font-medium bg-primary/5 text-primary/80 border border-primary/10"
              >
                {cat}
              </span>
            ))}
            {p.published ? (
              <span className="text-[11px] text-muted-foreground ml-auto">
                {p.published.slice(0, 10)}
              </span>
            ) : null}
          </div>
        )}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-border/40"
          >
            <div className="p-3 sm:p-4 space-y-3">
              {p.categories?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {p.categories.map((cat) => (
                    <span
                      key={cat}
                      className="px-1.5 py-0.5 rounded text-[11px] font-medium bg-primary/5 text-primary/80 border border-primary/10"
                    >
                      {cat}
                    </span>
                  ))}
                </div>
              )}

              <div className="flex flex-wrap gap-2" data-testid="paper-actions">
                <ActionBtn
                  state={storeState}
                  error={storeError}
                  onClick={handleStore}
                  label="Save to library"
                  icon={Library}
                  storedLabel="Saved"
                  color="primary"
                />
                <ActionBtn
                  state={calibreState}
                  error={calibreError}
                  onClick={handleCalibre}
                  label="To Calibre"
                  icon={BookMarked}
                  storedLabel="Added"
                  color="default"
                />
                {onQuickView && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onQuickView(p);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border/40 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-all whitespace-nowrap"
                    data-testid="action-quick-view"
                  >
                    <FileText className="h-3.5 w-3.5" /> Quick view
                  </button>
                )}
                <a
                  href={absUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border/40 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-all whitespace-nowrap"
                  onClick={(e) => e.stopPropagation()}
                  data-testid="action-open-arxiv"
                >
                  <ExternalLink className="h-3.5 w-3.5" /> Open arXiv
                </a>
                {p.pdf_url && (
                  <a
                    href={p.pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border/40 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-all whitespace-nowrap"
                    onClick={(e) => e.stopPropagation()}
                    data-testid="action-pdf"
                  >
                    <BookOpen className="h-3.5 w-3.5" /> PDF
                  </a>
                )}
              </div>

              {p.published && (
                <p className="text-[11px] text-muted-foreground">
                  Published: {p.published.slice(0, 10)}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

import { motion } from "framer-motion";
import { BookMarked, BookOpen, ExternalLink, Library, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "@/api/client";
import { Button } from "@/components/ui/button";
import type { Paper } from "./PaperCard";

type BtnState = "idle" | "storing" | "stored" | "error";

export function PaperDetailModal({ paper, onClose }: { paper: Paper; onClose: () => void }) {
  const [storeState, setStoreState] = useState<BtnState>("idle");
  const [storeError, setStoreError] = useState<string | null>(null);
  const [calibreState, setCalibreState] = useState<BtnState>("idle");
  const [calibreError, setCalibreError] = useState<string | null>(null);
  const [fullText, setFullText] = useState<string | null>(null);
  const [fetchingText, setFetchingText] = useState(false);

  useEffect(() => {
    apiGet<{ arxiv_id: string }>(`/api/corpus/item?arxiv_id=${encodeURIComponent(paper.paper_id)}`)
      .then(() => setStoreState("stored")).catch(() => {});
  }, [paper.paper_id]);

  const handleStore = useCallback(async () => {
    setStoreState("storing"); setStoreError(null);
    try { await apiPost("/api/depot/ingest", { paper_id: paper.paper_id }); setStoreState("stored"); }
    catch (e) { setStoreState("error"); setStoreError(String(e)); }
  }, [paper.paper_id]);

  const handleCalibre = useCallback(async () => {
    setCalibreState("storing"); setCalibreError(null);
    try { await apiPost("/api/calibre/ingest", { paper_id: paper.paper_id }); setCalibreState("stored"); }
    catch (e) { setCalibreState("error"); setCalibreError(String(e)); }
  }, [paper.paper_id]);

  const fetchFullText = useCallback(async () => {
    setFetchingText(true);
    try {
      const data = await apiGet<{ markdown: string }>(`/api/paper/full-text?paper_id=${encodeURIComponent(paper.paper_id)}`);
      setFullText(data.markdown?.slice(0, 10000) ?? "(no content)");
    } catch (e) {
      setFullText(`Failed to fetch: ${e}`);
    } finally {
      setFetchingText(false);
    }
  }, [paper.paper_id]);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose} data-testid="paper-detail-modal">
      <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }} transition={{ duration: 0.15 }}
        className="bg-card border border-border rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-border/60">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mb-1">
              <span>{paper.paper_id}</span>
              {paper.server && <span className="text-primary font-sans">#{paper.server}</span>}
            </div>
            <h2 className="font-semibold leading-snug line-clamp-2">{paper.title}</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors shrink-0">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <p className="text-xs text-muted-foreground leading-relaxed">{paper.authors?.join(", ") || "Unknown authors"}</p>
          {paper.published && <p className="text-xs text-muted-foreground">Published: {paper.published.slice(0, 10)}</p>}

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Abstract</h3>
            <p className="text-xs leading-relaxed text-foreground/90">{paper.summary}</p>
          </div>

          {paper.categories && paper.categories.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {paper.categories.map((cat) => (
                <span key={cat} className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary/5 text-primary/80 border border-primary/10">{cat}</span>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-2" data-testid="modal-actions">
            <Button size="sm" onClick={handleStore} disabled={storeState === "storing" || storeState === "stored"}>
              <Library className="h-3.5 w-3.5 mr-1.5" />
              {storeState === "stored" ? "Saved" : storeState === "storing" ? "Saving..." : "Save to library"}
            </Button>
            <Button size="sm" variant="secondary" onClick={handleCalibre} disabled={calibreState === "storing" || calibreState === "stored"}>
              <BookMarked className="h-3.5 w-3.5 mr-1.5" />
              {calibreState === "stored" ? "Added" : calibreState === "storing" ? "Adding..." : "To Calibre"}
            </Button>
            {!fullText && !fetchingText && (
              <Button size="sm" variant="outline" onClick={fetchFullText}>
                <BookOpen className="h-3.5 w-3.5 mr-1.5" /> Fetch full text
              </Button>
            )}
            <a href={paper.html_url ?? `https://arxiv.org/abs/${paper.paper_id}`} target="_blank" rel="noopener noreferrer">
              <Button size="sm" variant="outline"><ExternalLink className="h-3.5 w-3.5 mr-1.5" /> Open arXiv</Button>
            </a>
          </div>

          {storeError && <p className="text-xs text-red-400">{storeError}</p>}
          {calibreError && <p className="text-xs text-red-400">{calibreError}</p>}

          {fetchingText && <p className="text-xs text-muted-foreground animate-pulse">Fetching full text...</p>}
          {fullText && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Full text (preview)</h3>
              <pre className="text-xs leading-relaxed text-foreground/80 whitespace-pre-wrap font-sans bg-muted/30 rounded-lg p-3 max-h-64 overflow-y-auto border border-border/40">{fullText}</pre>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

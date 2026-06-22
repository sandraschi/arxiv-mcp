import React from "react";
import { apiPost } from "@/api/client";

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

function Btn({
  state, error, onClick, labels,
}: {
  state: "idle" | "storing" | "stored" | "error";
  error: string | null;
  onClick: () => void;
  labels: { idle: string; storing: string; stored: string; retry: string };
}) {
  return (
    <button
      onClick={onClick}
      disabled={state === "storing" || state === "stored"}
      className={[
        "px-2 py-0.5 rounded text-xs font-medium border transition-colors whitespace-nowrap",
        state === "stored"
          ? "border-green-500 text-green-600 bg-green-50 cursor-default"
          : state === "error"
            ? "border-red-400 text-red-600 bg-red-50 hover:bg-red-100"
            : state === "storing"
              ? "border-border text-muted-foreground cursor-wait"
              : "border-border text-foreground hover:bg-accent hover:text-accent-foreground",
      ].join(" ")}
      title={error ?? undefined}
    >
      {state === "storing" ? labels.storing : state === "stored" ? `\u2713 ${labels.stored}` : state === "error" ? labels.retry : labels.idle}
    </button>
  );
}

export function PaperHit({ p }: { p: Paper }) {
  const [storeState, setStoreState] = React.useState<"idle" | "storing" | "stored" | "error">("idle");
  const [storeError, setStoreError] = React.useState<string | null>(null);
  const [calibreState, setCalibreState] = React.useState<"idle" | "storing" | "stored" | "error">("idle");
  const [calibreError, setCalibreError] = React.useState<string | null>(null);

  async function handleStore() {
    setStoreState("storing");
    setStoreError(null);
    try {
      await apiPost("/api/depot/ingest", { paper_id: p.paper_id });
      setStoreState("stored");
    } catch (e) {
      setStoreState("error");
      setStoreError(String(e));
    }
  }

  async function handleCalibre() {
    setCalibreState("storing");
    setCalibreError(null);
    try {
      await apiPost("/api/calibre/ingest", { paper_id: p.paper_id });
      setCalibreState("stored");
    } catch (e) {
      setCalibreState("error");
      setCalibreError(String(e));
    }
  }

  const serverColors: Record<string, string> = {
    arxiv: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    biorxiv: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    medrxiv: "bg-teal-500/10 text-teal-400 border-teal-500/20",
    chemrxiv: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    researchsquare: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  };

  return (
    <div className="border border-border/40 rounded-lg p-3 sm:p-4 space-y-2 bg-card/30">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            {p.server ? (
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${serverColors[p.server] || "bg-white/5 text-muted-foreground border-border"}`}>
                {p.server === "researchsquare" ? "R Sq" : p.server}
              </span>
            ) : null}
          </div>
          <a
            href={p.html_url ?? `https://arxiv.org/abs/${p.paper_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold leading-snug text-foreground hover:underline line-clamp-2"
          >
            {p.title}
          </a>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
            {p.authors?.slice(0, 5).join(", ")}{p.authors?.length > 5 ? ` et al.` : ""}
          </p>
        </div>
        <div className="flex flex-col gap-1 shrink-0">
          <Btn state={storeState} error={storeError} onClick={handleStore} labels={{ idle: "Save to library", storing: "Saving…", stored: "Saved", retry: "Retry" }} />
          <Btn state={calibreState} error={calibreError} onClick={handleCalibre} labels={{ idle: "To Calibre", storing: "Adding…", stored: "Added", retry: "Retry" }} />
        </div>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">{p.summary}</p>
      <div className="flex flex-wrap items-center gap-1.5">
        {p.categories?.slice(0, 4).map((cat) => (
          <span key={cat} className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary/5 text-primary/80 border border-primary/10">
            {cat}
          </span>
        ))}
        {p.published ? <span className="text-[10px] text-muted-foreground ml-auto">{p.published.slice(0, 10)}</span> : null}
      </div>
    </div>
  );
}

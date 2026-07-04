import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Filter, Maximize2, Minimize2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useSearchParams } from "react-router-dom";
import { apiGet, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogger } from "@/context/LoggerContext";
import { cn } from "@/lib/utils";

type EpistemicItem = { kind: string; label: string; detail: string };
type ClaimRow = {
  claim: string; evidence_mode: string; confidence: string;
  needs_human_judgment: boolean; needs_bench: boolean; needs_telescope_or_instrument: boolean;
  needs_formal_verification: boolean; needs_simulation_compute: boolean;
  falsifier: string | null; section_hint: string | null;
};
type AggregateNeeds = { needs_human_judgment?: boolean; needs_bench?: boolean; needs_telescope_or_instrument?: boolean; needs_formal_verification?: boolean; needs_simulation_compute?: boolean; };
type EpistemicProfile = {
  primary_mode: string; knowing_requires: string[]; still_needs_human_or_physical: EpistemicItem[];
  automation_readiness: string; summary: string; deep_summary?: string; analyzer?: string;
  evidence_signals?: Record<string, number>; claims?: ClaimRow[]; aggregate_needs?: AggregateNeeds;
};
type Row = { arxiv_id: string; title: string; ingested_at: number; source: string; primary_mode?: string | null; claim_count?: number; aggregate_needs?: AggregateNeeds | null; };
type Item = { arxiv_id: string; title: string; markdown: string; source: string; ingested_at: number; meta?: { epistemic_profile?: EpistemicProfile }; };

const MODES = ["", "formal_proof", "simulation", "computational", "observational_instrumental", "interventional_experiment", "mixed"] as const;

function flagBadges(c: ClaimRow) {
  const f: string[] = [];
  if (c.needs_bench) f.push("bench");
  if (c.needs_telescope_or_instrument) f.push("telescope");
  if (c.needs_formal_verification) f.push("formal");
  if (c.needs_simulation_compute) f.push("compute");
  if (c.needs_human_judgment) f.push("human");
  return f;
}

function EpistemicCard({ profile }: { profile: EpistemicProfile }) {
  const [showClaims, setShowClaims] = useState(false);
  const summary = profile.deep_summary || profile.summary;
  const hasClaims = (profile.claims?.length ?? 0) > 0;

  return (
    <div className="rounded-lg border border-border/50 bg-muted/20 p-4 text-sm space-y-3" data-testid="epistemic-card">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium capitalize px-2 py-0.5 rounded bg-primary/10 text-primary text-xs">
          {profile.primary_mode.replace(/_/g, " ")}
        </span>
        {profile.analyzer && <span className="text-[10px] font-mono text-muted-foreground">{profile.analyzer}</span>}
        {hasClaims && <span className="text-[10px] rounded bg-secondary px-1.5 py-0.5 text-muted-foreground">{profile.claims!.length} claims</span>}
      </div>

      <p className="text-xs text-muted-foreground leading-relaxed">{summary}</p>

      {hasClaims && (
        <div className="flex items-center gap-2">
          <button onClick={() => setShowClaims(!showClaims)}
            className="flex items-center gap-1 text-xs text-primary hover:underline">
            {showClaims ? "Hide" : "View"} claim table <ChevronDown className={cn("h-3 w-3 transition-transform", showClaims && "rotate-180")} />
          </button>
        </div>
      )}

      <AnimatePresence>
        {hasClaims && showClaims && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="overflow-x-auto border border-border/30 rounded-lg">
              <table className="w-full text-[11px] border-collapse">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-border/40 bg-muted/30">
                    <th className="py-1.5 px-2 font-medium">Claim</th>
                    <th className="py-1.5 px-2 font-medium">Mode</th>
                    <th className="py-1.5 px-2 font-medium">Needs</th>
                    <th className="py-1.5 px-2 font-medium">Falsifier</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.claims!.slice(0, showClaims ? undefined : 3).map((c, i) => (
                    <tr key={i} className="border-b border-border/20 align-top">
                      <td className="py-1.5 px-2 max-w-[180px]">{c.claim}</td>
                      <td className="py-1.5 px-2 whitespace-nowrap capitalize">{c.evidence_mode.replace(/_/g, " ")}</td>
                      <td className="py-1.5 px-2"><div className="flex flex-wrap gap-0.5">{flagBadges(c).map((f) => <span key={f} className="rounded bg-secondary px-1 text-[10px]">{f}</span>)}{!flagBadges(c).length ? <span className="text-muted-foreground">&mdash;</span> : null}</div></td>
                      <td className="py-1.5 px-2 text-muted-foreground max-w-[140px]">{c.falsifier || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(profile.claims!.length > 3) && !showClaims && (
                <p className="text-[10px] text-muted-foreground text-center py-1">+{profile.claims!.length - 3} more claims</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-2 text-xs">
        <div><span className="font-semibold text-muted-foreground">Knowing requires: </span><span className="text-muted-foreground">{profile.knowing_requires.join("; ")}</span></div>
        {profile.still_needs_human_or_physical.length > 0 && (
          <div>
            <span className="font-semibold text-muted-foreground">Still needs: </span>
            <span className="text-muted-foreground">{profile.still_needs_human_or_physical.map((i) => i.label).join(", ")}</span>
          </div>
        )}
        <div className="text-muted-foreground">AI fit: {profile.automation_readiness.replace(/_/g, " ")}</div>
      </div>
    </div>
  );
}

function buildCorpusQuery(filters: { primary_mode: string; needs_bench: boolean | null; needs_telescope: boolean | null; needs_formal: boolean | null; has_deep_claims: boolean | null }) {
  const p = new URLSearchParams({ limit: "200" });
  if (filters.primary_mode) p.set("primary_mode", filters.primary_mode);
  if (filters.needs_bench !== null) p.set("needs_bench", String(filters.needs_bench));
  if (filters.needs_telescope !== null) p.set("needs_telescope_or_instrument", String(filters.needs_telescope));
  if (filters.needs_formal !== null) p.set("needs_formal_verification", String(filters.needs_formal));
  if (filters.has_deep_claims !== null) p.set("has_deep_claims", String(filters.has_deep_claims));
  return `/api/corpus?${p.toString()}`;
}

export function Depot() {
  const { log } = useLogger();
  const [params] = useSearchParams();
  const focus = params.get("focus");
  const [rows, setRows] = useState<Row[]>([]);
  const [filtered, setFiltered] = useState(false);
  const [pid, setPid] = useState("2603.26524v1");
  const [ingesting, setIngesting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [deepAnalyzing, setDeepAnalyzing] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<Item | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [primaryMode, setPrimaryMode] = useState("");
  const [needsBench, setNeedsBench] = useState<boolean | null>(null);
  const [needsTelescope, setNeedsTelescope] = useState<boolean | null>(null);
  const [needsFormal, setNeedsFormal] = useState<boolean | null>(null);
  const [hasDeepClaims, setHasDeepClaims] = useState<boolean | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const path = buildCorpusQuery({ primary_mode: primaryMode, needs_bench: needsBench, needs_telescope: needsTelescope, needs_formal: needsFormal, has_deep_claims: hasDeepClaims });
      const data = await apiGet<{ ingested: Row[]; filtered?: boolean }>(path);
      setRows(data.ingested); setFiltered(Boolean(data.filtered));
    } catch (e) { log("error", String(e)); }
  }, [log, primaryMode, needsBench, needsTelescope, needsFormal, hasDeepClaims]);

  const loadDetail = useCallback(async (arxivId: string) => {
    setLoadingDetail(true);
    try { const d = await apiGet<Item>(`/api/corpus/item?arxiv_id=${encodeURIComponent(arxivId)}`); setDetail(d); }
    catch (e) { setDetail(null); log("error", String(e)); }
    finally { setLoadingDetail(false); }
  }, [log]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { if (focus) setSelected(focus); }, [focus]);
  useEffect(() => { if (!selected) { setDetail(null); return; } loadDetail(selected); }, [selected, loadDetail]);

  async function ingest(deep = false) {
    if (deep) setAnalyzing(true); else setIngesting(true);
    try {
      const path = deep ? "/api/depot/ingest-analyze?deep=true" : "/api/depot/ingest";
      const r = await apiPost<Record<string, unknown>>(path, { paper_id: pid });
      log("info", deep ? `Ingest+analyze ${JSON.stringify(r.epistemic_profile)}` : `Ingested ${JSON.stringify(r)}`);
      await refresh();
      if (r.arxiv_id) { setSelected(String(r.arxiv_id)); await loadDetail(String(r.arxiv_id)); }
    } catch (e) { log("error", String(e)); }
    finally { setIngesting(false); setAnalyzing(false); }
  }

  async function deepAnalyze(forceRefresh = false) {
    const target = selected || pid;
    if (!target.trim()) return;
    setDeepAnalyzing(true);
    try {
      const q = forceRefresh ? "?force_refresh=true" : "";
      const r = await apiPost<{ arxiv_id?: string; epistemic_profile?: EpistemicProfile; cached?: boolean }>(`/api/depot/deep-analyze${q}`, { paper_id: target });
      log("info", r.cached ? "Deep profile (cached)" : "Deep profile saved");
      await refresh();
      if (r.arxiv_id) { setSelected(r.arxiv_id); await loadDetail(r.arxiv_id); }
    } catch (e) { log("error", String(e)); }
    finally { setDeepAnalyzing(false); }
  }

  function cycleTriState(value: boolean | null, setter: (v: boolean | null) => void) {
    if (value === null) setter(true); else if (value === true) setter(false); else setter(null);
  }

  const profile = detail?.meta?.epistemic_profile;
  const [readerTab, setReaderTab] = useState<"profile" | "text">("profile");
  const [fullscreen, setFullscreen] = useState(false);

  return (
    <div className="space-y-6" data-testid="depot-page">
      <PageHero eyebrow="Your library" title="Depot" lead="Ingested papers, epistemic profiles, and full text."
        size="default" />

      <Card data-testid="depot-ingest">
        <div className="flex items-center justify-between">
          <CardTitle>Ingest paper</CardTitle>
          <Button variant="outline" size="sm" onClick={refresh}><RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh</Button>
        </div>
        <div className="mt-3 flex flex-col sm:flex-row gap-2">
          <Input value={pid} onChange={(e) => setPid(e.target.value)} placeholder="arXiv id or URL" className="flex-1" />
          <div className="flex gap-2">
            <Button onClick={() => ingest(false)} disabled={ingesting || analyzing || deepAnalyzing}>
              {ingesting ? "Fetching..." : "Ingest"}
            </Button>
            <Button variant="secondary" onClick={() => ingest(true)} disabled={ingesting || analyzing || deepAnalyzing}>
              {analyzing ? "Analyzing..." : "Ingest + analyze"}
            </Button>
          </div>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">Deep analyze needs Ollama or MCP sampling.</p>
      </Card>

      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)} data-testid="depot-filters-toggle">
          <Filter className="h-3.5 w-3.5 mr-1" /> Filters {filtered ? "(active)" : ""}
          <ChevronDown className={cn("h-3 w-3 ml-1 transition-transform", showFilters && "rotate-180")} />
        </Button>
        <p className="text-xs text-muted-foreground">{rows.length} paper{rows.length !== 1 ? "s" : ""} in depot</p>
      </div>

      <AnimatePresence>
        {showFilters && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <Card>
              <div className="flex flex-wrap gap-2 items-center text-xs">
                <label className="flex items-center gap-1">
                  Mode
                  <select className="rounded border border-border bg-background px-2 py-1" value={primaryMode}
                    onChange={(e) => setPrimaryMode(e.target.value)}>
                    {MODES.map((m) => <option key={m || "all"} value={m}>{m ? m.replace(/_/g, " ") : "any"}</option>)}
                  </select>
                </label>
                {(["bench", "telescope", "formal", "claims"] as const).map((label) => {
                  const val = label === "bench" ? needsBench : label === "telescope" ? needsTelescope : label === "formal" ? needsFormal : hasDeepClaims;
                  const setter = label === "bench" ? setNeedsBench : label === "telescope" ? setNeedsTelescope : label === "formal" ? setNeedsFormal : setHasDeepClaims;
                  return (
                    <Button variant="outline" size="sm" type="button" onClick={() => cycleTriState(val, setter)}
                      key={label}>
                      {label} {val === null ? "any" : val ? "yes" : "no"}
                    </Button>
                  );
                })}
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-4 lg:grid-cols-5" data-testid="depot-panels">
        <Card className="lg:col-span-2 min-h-[280px]">
          <CardTitle>Papers</CardTitle>
          <div className="mt-3 space-y-1 max-h-[480px] overflow-y-auto text-sm">
            {rows.length === 0 && <p className="text-xs text-muted-foreground">No papers ingested yet.</p>}
            {rows.map((r) => (
              <button key={r.arxiv_id} type="button"
                className={cn("w-full text-left rounded-md px-2 py-1.5 hover:bg-muted/50 transition-colors", selected === r.arxiv_id && "bg-secondary")}
                onClick={() => setSelected(r.arxiv_id)}>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-mono text-[11px] text-primary">{r.arxiv_id}</span>
                  {r.primary_mode && <span className="text-[10px] capitalize text-muted-foreground bg-muted/50 px-1 rounded">{r.primary_mode.replace(/_/g, " ")}</span>}
                  {(r.claim_count ?? 0) > 0 && <span className="text-[10px] text-primary">{r.claim_count}cl</span>}
                </div>
                <div className="text-xs line-clamp-1 mt-0.5">{r.title}</div>
              </button>
            ))}
          </div>
        </Card>

        <Card className="lg:col-span-3 min-h-[280px]" data-testid="depot-reader">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>Reader</CardTitle>
            {selected && (
              <div className="flex gap-1">
                <div className="flex rounded-lg border border-border/40 overflow-hidden text-xs">
                  <button onClick={() => setReaderTab("profile")}
                    className={cn("px-2.5 py-1 transition-colors", readerTab === "profile" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground")}>
                    Profile
                  </button>
                  <button onClick={() => setReaderTab("text")}
                    className={cn("px-2.5 py-1 transition-colors", readerTab === "text" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground")}>
                    Full text
                  </button>
                </div>
                <Button size="sm" variant="secondary" disabled={deepAnalyzing} onClick={() => deepAnalyze(false)}>
                  {deepAnalyzing ? "Deep..." : "Deep analyze"}
                </Button>
                <Button size="sm" variant="outline" disabled={deepAnalyzing} onClick={() => deepAnalyze(true)}>Re-run</Button>
                <button type="button" onClick={() => setFullscreen(!fullscreen)}
                  className="p-1.5 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
                  title={fullscreen ? "Exit fullscreen" : "Fullscreen"}>
                  {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </button>
              </div>
            )}
          </div>

          {loadingDetail && <p className="text-sm text-muted-foreground mt-4">Loading...</p>}

          {!loadingDetail && detail && (
            <div className="mt-3 space-y-3">
              <div>
                <h2 className="font-semibold text-sm">{detail.title}</h2>
                <span className="text-[11px] text-muted-foreground font-mono">{detail.arxiv_id}</span>
              </div>
              {readerTab === "profile" && (
                profile ? <EpistemicCard profile={profile} />
                  : <p className="text-xs text-muted-foreground">No epistemic profile — use Ingest + deep analyze.</p>
              )}
              {readerTab === "text" && (
                <div className="text-sm leading-relaxed max-w-none max-h-[480px] overflow-y-auto border border-border/40 rounded-lg p-4 bg-background/40 [&_a]:text-primary">
                  <ReactMarkdown>{detail.markdown}</ReactMarkdown>
                </div>
              )}
            </div>
          )}

          {!loadingDetail && !detail && (
            <p className="text-sm text-muted-foreground mt-4">Select a paper from the list.</p>
          )}
        </Card>
      </div>

      {fullscreen && detail && (
        <div className="fixed inset-0 z-50 bg-background flex flex-col" data-testid="depot-fullscreen">
          <div className="flex items-center justify-between border-b border-border/40 px-4 py-2">
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold truncate">{detail.title}</h2>
              <span className="text-[11px] text-muted-foreground font-mono">{detail.arxiv_id}</span>
            </div>
            <div className="flex items-center gap-2 ml-4">
              <div className="flex rounded-lg border border-border/40 overflow-hidden text-xs">
                <button onClick={() => setReaderTab("profile")}
                  className={cn("px-2.5 py-1 transition-colors", readerTab === "profile" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground")}>
                  Profile
                </button>
                <button onClick={() => setReaderTab("text")}
                  className={cn("px-2.5 py-1 transition-colors", readerTab === "text" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground")}>
                  Full text
                </button>
              </div>
              <button type="button" onClick={() => setFullscreen(false)}
                className="p-1.5 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground" title="Exit fullscreen">
                <Minimize2 className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-6">
            {readerTab === "profile" && (profile ? <EpistemicCard profile={profile} />
              : <p className="text-xs text-muted-foreground">No epistemic profile.</p>)}
            {readerTab === "text" && (
              <div className="max-w-3xl mx-auto text-sm leading-relaxed max-w-none [&_a]:text-primary">
                <ReactMarkdown>{detail.markdown}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

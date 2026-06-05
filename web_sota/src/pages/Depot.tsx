import { useCallback, useEffect, useState } from "react";

import { useSearchParams } from "react-router-dom";

import ReactMarkdown from "react-markdown";

import { apiGet, apiPost } from "@/api/client";

import { Button } from "@/components/ui/button";

import { Input } from "@/components/ui/input";

import { Card, CardTitle } from "@/components/ui/card";

import { PageHero } from "@/components/layout/PageHero";

import { useLogger } from "@/context/LoggerContext";



type EpistemicItem = {

  kind: string;

  label: string;

  detail: string;

};



type ClaimRow = {

  claim: string;

  evidence_mode: string;

  confidence: string;

  needs_human_judgment: boolean;

  needs_bench: boolean;

  needs_telescope_or_instrument: boolean;

  needs_formal_verification: boolean;

  needs_simulation_compute: boolean;

  falsifier: string | null;

  section_hint: string | null;

};



type AggregateNeeds = {

  needs_human_judgment?: boolean;

  needs_bench?: boolean;

  needs_telescope_or_instrument?: boolean;

  needs_formal_verification?: boolean;

  needs_simulation_compute?: boolean;

};



type EpistemicProfile = {

  primary_mode: string;

  knowing_requires: string[];

  still_needs_human_or_physical: EpistemicItem[];

  automation_readiness: string;

  summary: string;

  deep_summary?: string;

  analyzer?: string;

  evidence_signals?: Record<string, number>;

  claims?: ClaimRow[];

  aggregate_needs?: AggregateNeeds;

};



type Row = {

  arxiv_id: string;

  title: string;

  ingested_at: number;

  source: string;

  primary_mode?: string | null;

  claim_count?: number;

  aggregate_needs?: AggregateNeeds | null;

};



type Item = {

  arxiv_id: string;

  title: string;

  markdown: string;

  source: string;

  ingested_at: number;

  meta?: { epistemic_profile?: EpistemicProfile };

};



const MODES = [

  "",

  "formal_proof",

  "simulation",

  "computational",

  "observational_instrumental",

  "interventional_experiment",

  "mixed",

] as const;



function flagBadges(claim: ClaimRow) {

  const flags: string[] = [];

  if (claim.needs_bench) flags.push("bench");

  if (claim.needs_telescope_or_instrument) flags.push("telescope");

  if (claim.needs_formal_verification) flags.push("formal");

  if (claim.needs_simulation_compute) flags.push("compute");

  if (claim.needs_human_judgment) flags.push("human");

  return flags;

}



function EpistemicCard({ profile }: { profile: EpistemicProfile }) {

  const summary = profile.deep_summary || profile.summary;

  const hasClaims = (profile.claims?.length ?? 0) > 0;



  return (

    <div className="rounded-lg border border-border/50 bg-muted/20 p-3 text-sm space-y-3">

      <div className="flex flex-wrap items-center gap-2">

        <div className="font-medium capitalize">{profile.primary_mode.replace(/_/g, " ")}</div>

        {profile.analyzer ? (

          <span className="text-[10px] font-mono text-muted-foreground">{profile.analyzer}</span>

        ) : null}

        {hasClaims ? (

          <span className="text-[10px] rounded bg-primary/15 px-1.5 py-0.5 text-primary">

            {profile.claims!.length} claims

          </span>

        ) : null}

      </div>

      <p className="text-muted-foreground text-xs leading-relaxed">{summary}</p>



      {hasClaims ? (

        <div className="overflow-x-auto">

          <div className="text-xs font-semibold mb-1">Claim table (v2)</div>

          <table className="w-full text-[11px] border-collapse">

            <thead>

              <tr className="text-left text-muted-foreground border-b border-border/40">

                <th className="py-1 pr-2 font-medium">Claim</th>

                <th className="py-1 pr-2 font-medium">Mode</th>

                <th className="py-1 pr-2 font-medium">Needs</th>

                <th className="py-1 font-medium">Falsifier</th>

              </tr>

            </thead>

            <tbody>

              {profile.claims!.map((c, i) => (

                <tr key={`${i}-${c.claim.slice(0, 24)}`} className="border-b border-border/20 align-top">

                  <td className="py-1.5 pr-2 max-w-[200px]">{c.claim}</td>

                  <td className="py-1.5 pr-2 whitespace-nowrap capitalize">{c.evidence_mode.replace(/_/g, " ")}</td>

                  <td className="py-1.5 pr-2">

                    <div className="flex flex-wrap gap-0.5">

                      {flagBadges(c).map((f) => (

                        <span key={f} className="rounded bg-secondary px-1 text-[10px]">

                          {f}

                        </span>

                      ))}

                      {!flagBadges(c).length ? <span className="text-muted-foreground">—</span> : null}

                    </div>

                  </td>

                  <td className="py-1.5 text-muted-foreground max-w-[160px]">{c.falsifier || "—"}</td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      ) : (

        <p className="text-xs text-muted-foreground">Rule-only profile — run Deep analyze for claim-level LLM pass.</p>

      )}



      <div>

        <div className="text-xs font-semibold mt-1">Knowing requires</div>

        <ul className="list-disc pl-4 text-xs text-muted-foreground mt-1 space-y-1">

          {profile.knowing_requires.map((line) => (

            <li key={line}>{line}</li>

          ))}

        </ul>

      </div>

      <div>

        <div className="text-xs font-semibold mt-1">Still needs human or physical loop</div>

        <ul className="text-xs text-muted-foreground mt-1 space-y-2">

          {profile.still_needs_human_or_physical.map((item) => (

            <li key={`${item.kind}-${item.label}`}>

              <span className="font-mono text-[10px] text-primary">{item.kind}</span> — {item.label}: {item.detail}

            </li>

          ))}

        </ul>

      </div>

      <div className="text-[10px] text-muted-foreground">AI fit: {profile.automation_readiness.replace(/_/g, " ")}</div>

    </div>

  );

}



function buildCorpusQuery(filters: {

  primary_mode: string;

  needs_bench: boolean | null;

  needs_telescope: boolean | null;

  needs_formal: boolean | null;

  has_deep_claims: boolean | null;

}) {

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



  const refresh = useCallback(async () => {

    try {

      const path = buildCorpusQuery({

        primary_mode: primaryMode,

        needs_bench: needsBench,

        needs_telescope: needsTelescope,

        needs_formal: needsFormal,

        has_deep_claims: hasDeepClaims,

      });

      const data = await apiGet<{ ingested: Row[]; filtered?: boolean }>(path);

      setRows(data.ingested);

      setFiltered(Boolean(data.filtered));

    } catch (e) {

      log("error", String(e));

    }

  }, [log, primaryMode, needsBench, needsTelescope, needsFormal, hasDeepClaims]);



  const loadDetail = useCallback(

    async (arxivId: string) => {

      setLoadingDetail(true);

      try {

        const d = await apiGet<Item>(`/api/corpus/item?arxiv_id=${encodeURIComponent(arxivId)}`);

        setDetail(d);

      } catch (e) {

        setDetail(null);

        log("error", String(e));

      } finally {

        setLoadingDetail(false);

      }

    },

    [log],

  );



  useEffect(() => {

    refresh();

  }, [refresh]);



  useEffect(() => {

    if (focus) setSelected(focus);

  }, [focus]);



  useEffect(() => {

    if (!selected) {

      setDetail(null);

      return;

    }

    loadDetail(selected);

  }, [selected, loadDetail]);



  async function ingest(deep = false) {

    if (deep) setAnalyzing(true);

    else setIngesting(true);

    try {

      const path = deep ? "/api/depot/ingest-analyze?deep=true" : "/api/depot/ingest";

      const r = await apiPost<Record<string, unknown>>(path, { paper_id: pid });

      log("info", deep ? `Ingest+analyze ${JSON.stringify(r.epistemic_profile)}` : `Ingested ${JSON.stringify(r)}`);

      await refresh();

      if (r.arxiv_id) {

        setSelected(String(r.arxiv_id));

        await loadDetail(String(r.arxiv_id));

      }

    } catch (e) {

      log("error", String(e));

    } finally {

      setIngesting(false);

      setAnalyzing(false);

    }

  }



  async function deepAnalyze(forceRefresh = false) {

    const target = selected || pid;

    if (!target.trim()) return;

    setDeepAnalyzing(true);

    try {

      const q = forceRefresh ? "?force_refresh=true" : "";

      const r = await apiPost<{ arxiv_id?: string; epistemic_profile?: EpistemicProfile; cached?: boolean }>(

        `/api/depot/deep-analyze${q}`,

        { paper_id: target },

      );

      log("info", r.cached ? "Deep profile (cached)" : "Deep profile saved");

      await refresh();

      if (r.arxiv_id) {

        setSelected(r.arxiv_id);

        await loadDetail(r.arxiv_id);

      }

    } catch (e) {

      log("error", String(e));

    } finally {

      setDeepAnalyzing(false);

    }

  }



  function cycleTriState(value: boolean | null, setter: (v: boolean | null) => void) {

    if (value === null) setter(true);

    else if (value === true) setter(false);

    else setter(null);

  }



  const profile = detail?.meta?.epistemic_profile;



  return (

    <div className="space-y-6">

      <PageHero

        eyebrow="Your library"

        title="Depot — ingest, analyze, know"

        lead="HTML-first ingest, rule tags, then deep LLM claim tables: what each claim rests on and what still needs bench, telescope, formal verification, or human judgment."

      />



      <Card>

        <CardTitle>Ingest paper</CardTitle>

        <div className="mt-4 flex flex-col sm:flex-row gap-2">

          <Input value={pid} onChange={(e) => setPid(e.target.value)} placeholder="arXiv id or URL" className="flex-1" />

          <Button onClick={() => ingest(false)} disabled={ingesting || analyzing || deepAnalyzing}>

            {ingesting ? "Fetching…" : "Ingest HTML"}

          </Button>

          <Button variant="secondary" onClick={() => ingest(true)} disabled={ingesting || analyzing || deepAnalyzing}>

            {analyzing ? "Analyzing…" : "Ingest + deep analyze"}

          </Button>

          <Button variant="outline" type="button" onClick={refresh}>

            Refresh list

          </Button>

        </div>

        <p className="mt-2 text-xs text-muted-foreground">

          Deep analyze needs ARXIV_MCP_SAMPLING_BASE_URL (e.g. Ollama http://localhost:11434/v1) or MCP sampling in Cursor.

        </p>

      </Card>



      <Card>

        <CardTitle>Epistemic filters{filtered ? " (active)" : ""}</CardTitle>

        <div className="mt-3 flex flex-wrap gap-2 items-center text-xs">

          <label className="flex items-center gap-1">

            Mode

            <select

              className="rounded border border-border bg-background px-2 py-1"

              value={primaryMode}

              onChange={(e) => setPrimaryMode(e.target.value)}

            >

              {MODES.map((m) => (

                <option key={m || "all"} value={m}>

                  {m ? m.replace(/_/g, " ") : "any"}

                </option>

              ))}

            </select>

          </label>

          <Button variant="outline" size="sm" type="button" onClick={() => cycleTriState(needsBench, setNeedsBench)}>

            bench {needsBench === null ? "any" : needsBench ? "yes" : "no"}

          </Button>

          <Button variant="outline" size="sm" type="button" onClick={() => cycleTriState(needsTelescope, setNeedsTelescope)}>

            telescope {needsTelescope === null ? "any" : needsTelescope ? "yes" : "no"}

          </Button>

          <Button variant="outline" size="sm" type="button" onClick={() => cycleTriState(needsFormal, setNeedsFormal)}>

            formal {needsFormal === null ? "any" : needsFormal ? "yes" : "no"}

          </Button>

          <Button variant="outline" size="sm" type="button" onClick={() => cycleTriState(hasDeepClaims, setHasDeepClaims)}>

            deep claims {hasDeepClaims === null ? "any" : hasDeepClaims ? "yes" : "no"}

          </Button>

        </div>

      </Card>



      <div className="grid gap-4 lg:grid-cols-2">

        <Card className="min-h-[320px]">

          <CardTitle>Ingested</CardTitle>

          <ul className="mt-4 space-y-1 max-h-[480px] overflow-y-auto text-sm">

            {rows.map((r) => (

              <li key={r.arxiv_id}>

                <button

                  type="button"

                  className={`w-full text-left rounded-md px-2 py-1.5 hover:bg-muted/50 ${

                    selected === r.arxiv_id ? "bg-secondary" : ""

                  }`}

                  onClick={() => setSelected(r.arxiv_id)}

                >

                  <div className="flex flex-wrap items-center gap-1">

                    <span className="font-mono text-xs text-primary">{r.arxiv_id}</span>

                    {r.primary_mode ? (

                      <span className="text-[10px] capitalize text-muted-foreground">{r.primary_mode.replace(/_/g, " ")}</span>

                    ) : null}

                    {(r.claim_count ?? 0) > 0 ? (

                      <span className="text-[10px] text-primary">{r.claim_count} claims</span>

                    ) : null}

                  </div>

                  <div className="line-clamp-2">{r.title}</div>

                </button>

              </li>

            ))}

          </ul>

        </Card>



        <Card className="min-h-[320px]">

          <div className="flex flex-wrap items-center justify-between gap-2">

            <CardTitle>Reader</CardTitle>

            {selected ? (

              <div className="flex gap-1">

                <Button size="sm" variant="secondary" disabled={deepAnalyzing} onClick={() => deepAnalyze(false)}>

                  {deepAnalyzing ? "Deep…" : "Deep analyze"}

                </Button>

                <Button size="sm" variant="outline" disabled={deepAnalyzing} onClick={() => deepAnalyze(true)}>

                  Re-run

                </Button>

              </div>

            ) : null}

          </div>

          {loadingDetail && <p className="text-sm text-muted-foreground mt-4">Loading…</p>}

          {!loadingDetail && detail && (

            <div className="mt-4 space-y-3">

              <h2 className="font-semibold">{detail.title}</h2>

              <div className="text-xs text-muted-foreground font-mono">{detail.arxiv_id}</div>

              {profile ? (

                <EpistemicCard profile={profile} />

              ) : (

                <p className="text-xs text-muted-foreground">No epistemic profile — use Ingest + deep analyze.</p>

              )}

              <div className="text-sm leading-relaxed max-w-none max-h-[420px] overflow-y-auto border border-border/40 rounded-lg p-3 bg-background/40 [&_a]:text-primary">

                <ReactMarkdown>{detail.markdown}</ReactMarkdown>

              </div>

            </div>

          )}

          {!loadingDetail && !detail && (

            <p className="text-sm text-muted-foreground mt-4">Select a paper or ingest one.</p>

          )}

        </Card>

      </div>

    </div>

  );

}


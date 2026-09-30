import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogger } from "@/context/LoggerContext";

type CategoryRow = { code: string; name: string; group: string };

// Curated one-line scope notes. arXiv taxonomy is near-static, so these age
// slowly; codes missing here render with a fallback (see below).
const SCOPE_NOTES: Record<string, string> = {
  "cs.AI":
    "Broad AI: agents, reasoning, planning, knowledge representation, applied AI systems.",
  "cs.CL": "Language tech: NLP, LLMs, translation, summarization, dialogue.",
  "cs.CR":
    "Security research: cryptography, network and systems security, privacy. Not true-crime anecdotes.",
  "cs.CV":
    "Vision by learning: detection, segmentation, generation, video understanding.",
  "cs.DB":
    "Databases: query processing, indexing, transactions, data management.",
  "cs.DC":
    "Distributed and parallel computing: clusters, cloud, consensus, fault tolerance.",
  "cs.DS":
    "Algorithms and complexity theory: data structures, hardness, proofs.",
  "cs.HC":
    "Human-computer interaction: UX, user studies, interfaces, accessibility.",
  "cs.IR": "Retrieval: search engines, ranking, recommendation.",
  "cs.IT":
    "Information theory proper: coding, compression, Shannon theory. Math-heavy.",
  "cs.LG":
    "The ML flagship: methods and systems, statistical and deep. For the statistics-side view see stat.ML.",
  "cs.MA":
    "Multi-agent systems: cooperation, competition, negotiation, game theory.",
  "cs.NE":
    "Bio-inspired computing: neural nets from the biology angle, evolutionary and genetic algorithms.",
  "cs.PL":
    "Programming languages: compilers, type systems, semantics, verification.",
  "cs.RO": "Robotics: motion planning, control, SLAM, robot perception.",
  "cs.SE":
    "Software engineering process: testing, maintenance, requirements, mining repos.",
  "eess.AS":
    "Audio and speech: recognition, synthesis, enhancement, speaker ID.",
  "eess.IV":
    "Image/video processing, signal-side: filters, transforms, restoration. Sibling of cs.CV, less learning.",
  "eess.SP":
    "Signal processing: estimation, filtering, array and communications signals.",
  "math.NA": "Numerical analysis: solvers, discretization, error bounds.",
  "math.OC":
    "Optimization and control: convex optimization, optimal and robust control.",
  "math.PR":
    "Probability theory: measure-theoretic foundations, stochastic processes.",
  "math.ST":
    "Statistics theory: asymptotics, inference foundations. Often cross-listed with stat.TH.",
  "cond-mat":
    "Condensed matter physics. The full archive has nine sub-areas; this entry is the top level.",
  "hep-th":
    "High-energy theory: QFT, strings, formal and mathematical physics.",
  "quant-ph":
    "Quantum information and computing: entanglement, algorithms, error correction.",
  "q-bio.NC":
    "Computational neuroscience: neural modeling, cognition, brain theory.",
  "q-bio.QM":
    "Quantitative methods for biology: bioinformatics pipelines, systems modeling. The vaguest q-bio code.",
  "q-fin.CP":
    "Computational finance: pricing engines, numerics, trading systems.",
  "q-fin.ST": "Statistical finance: econometrics, time series, risk.",
  "stat.ME":
    "Applied statistics: methodology, experimental design, causal inference.",
  "stat.ML":
    "Machine learning from the statistics side: learning theory, consistency, high-dimensional inference.",
  "stat.TH":
    "Statistics foundations. Overlaps math.ST; check both when hunting theory.",
};

const CONFUSING_PAIRS: Array<[string, string]> = [
  [
    "cs.LG",
    "stat.ML — methods/systems flagship vs statistics-side learning theory. Check both.",
  ],
  ["math.ST", "stat.TH — near-twins, routinely cross-listed. Search both."],
  [
    "cs.CV",
    "eess.IV — learning-based vision vs signal-processing imaging. Different communities.",
  ],
  [
    "cs.CR",
    "anything with 'crime' — it is cryptography/security research, not incident reports.",
  ],
];

export default function CategoriesPage() {
  const { log } = useLogger();
  const [catalog, setCatalog] = useState<CategoryRow[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<{ categories: CategoryRow[] }>("/api/categories")
      .then((d) => setCatalog(d.categories ?? []))
      .catch((e) => {
        setError(String(e));
        log("error", "Failed to load category catalog");
      });
  }, [log]);

  const groups = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const m = new Map<string, CategoryRow[]>();
    for (const row of catalog) {
      const note = SCOPE_NOTES[row.code] ?? "";
      if (
        q &&
        !`${row.code} ${row.name} ${row.group} ${note}`
          .toLowerCase()
          .includes(q)
      )
        continue;
      const g = row.group || "Other";
      if (!m.has(g)) m.set(g, []);
      m.get(g)?.push(row);
    }
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [catalog, filter]);

  const total = groups.reduce((n, [, rows]) => n + rows.length, 0);

  return (
    <div className="space-y-6" data-testid="categories-page">
      <PageHero eyebrow="Reference" title="arXiv categories" size="large">
        <p className="text-muted-foreground text-sm md:text-base">
          What each category code actually covers — {catalog.length} codes in
          this depot's catalog. Names alone mislead; scope notes do not.
        </p>
      </PageHero>

      <Card>
        <CardTitle>Commonly confused pairs</CardTitle>
        <ul className="mt-2 space-y-1.5 text-sm text-muted-foreground">
          {CONFUSING_PAIRS.map(([code, note]) => (
            <li key={code} className="flex gap-2">
              <code className="shrink-0 px-1.5 py-0.5 rounded text-[11px] font-mono bg-primary/5 text-primary border border-primary/10 h-fit">
                {code}
              </code>
              <span className="text-xs leading-relaxed">{note}</span>
            </li>
          ))}
        </ul>
      </Card>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter categories (e.g. vision, quantum, finance)…"
          className="pl-9"
          data-testid="categories-search"
        />
      </div>

      {error && (
        <p className="text-sm text-destructive">
          Catalog failed to load: {error}
        </p>
      )}

      {groups.map(([group, rows]) => (
        <section key={group}>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            {group} ({rows.length})
          </h2>
          <div className="grid gap-2 md:grid-cols-2">
            {rows.map((row) => (
              <div
                key={row.code}
                className="border border-border/40 rounded-xl bg-card/30 p-3"
              >
                <div className="flex items-baseline gap-2 flex-wrap">
                  <code className="px-1.5 py-0.5 rounded text-[11px] font-mono bg-primary/5 text-primary border border-primary/10">
                    {row.code}
                  </code>
                  <span className="text-sm font-medium">{row.name}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  {SCOPE_NOTES[row.code] ?? "Scope note pending for this code."}
                </p>
              </div>
            ))}
          </div>
        </section>
      ))}

      {total === 0 && !error && (
        <p className="text-sm text-muted-foreground">
          No categories match this filter.
        </p>
      )}
    </div>
  );
}

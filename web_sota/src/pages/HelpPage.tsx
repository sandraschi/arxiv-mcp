import { useState } from "react";
import { PageHero } from "@/components/layout/PageHero";
import { Card, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const TABS = ["About arXiv", "App guide", "API & MCP", "Workflows"] as const;

export function HelpPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("About arXiv");

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHero
        eyebrow="Reference"
        title="Help"
        lead="How arXiv works, what this app does, and how to use it."
      />

      <div className="flex gap-1 border-b border-border/60 overflow-x-auto">
        {TABS.map((t) => (
          <button
            type="button"
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors -mb-px",
              tab === t
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "About arXiv" && (
        <div className="space-y-4">
          <Card>
            <CardTitle>What arXiv is</CardTitle>
            <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
              arXiv (pronounced "archive") is an open-access preprint repository
              hosted by Cornell University. Researchers upload manuscripts
              before or alongside journal submission. It covers physics,
              mathematics, computer science, quantitative biology, statistics,
              and more. For ML/AI, it is the primary publication channel —
              nearly every major result appears on arXiv first.
            </p>
          </Card>

          <Card>
            <CardTitle>Preprint vs peer-reviewed article</CardTitle>
            <div className="mt-3 space-y-3 text-sm text-muted-foreground">
              <p>
                A <strong className="text-foreground">preprint</strong> is a
                manuscript posted by the authors without formal peer review.
                arXiv moderation checks for topical relevance and basic
                scholarly standards but does not validate methods, results, or
                claims.
              </p>
              <p>
                A{" "}
                <strong className="text-foreground">
                  peer-reviewed article
                </strong>{" "}
                has passed through journal or conference review. The gap
                matters: influential results (GPT-3, ImageNet, AlphaFold)
                appeared on arXiv months to years before any peer-reviewed
                publication. Conversely, some arXiv papers are never accepted or
                are quietly withdrawn.
              </p>
              <p className="text-xs text-muted-foreground/70 border-l-2 border-border/40 pl-3">
                Guideline: treat arXiv papers as "claims I should verify" not
                "established truth." Check if the same authors have a conference
                version, look for replication attempts, and track how claims
                evolve across versions.
              </p>
            </div>
          </Card>

          <Card>
            <CardTitle>Why arXiv matters for ML/AI progress</CardTitle>
            <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
              <li>
                Virtually all frontier AI research appears on arXiv first, often
                long before conference deadlines.
              </li>
              <li>
                Safety and alignment work, capability benchmarks, and new
                architectures all land here concurrently.
              </li>
              <li>
                Version history lets you track how a paper changed between
                initial upload and camera-ready.
              </li>
              <li>
                Cross-listing (e.g. cs.AI + cs.LG + cs.CY) makes
                interdisciplinary work discoverable.
              </li>
              <li>
                The arXiv API is free, open, and requires no authentication —
                enabling programmatic curation tools like this one.
              </li>
            </ul>
          </Card>

          <Card>
            <CardTitle>What arXiv is not</CardTitle>
            <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
              <li>
                <strong className="text-foreground">Not peer review.</strong>{" "}
                Moderation checks scope, not correctness. A paper can be wrong,
                fraudulent, or never finish review.
              </li>
              <li>
                <strong className="text-foreground">Not a journal.</strong>{" "}
                There is no acceptance rate, impact factor, or editorial
                selection. Quality varies wildly.
              </li>
              <li>
                <strong className="text-foreground">Not permanent.</strong>{" "}
                Authors can withdraw papers (though replacement with a new
                version is more common).
              </li>
              <li>
                <strong className="text-foreground">
                  Not the only preprint server.
                </strong>{" "}
                There are others — see below.
              </li>
            </ul>
          </Card>

          <Card>
            <CardTitle>Other preprint servers (the "xiv" family)</CardTitle>
            <div className="mt-3 space-y-3 text-sm text-muted-foreground">
              <p>
                arXiv is the oldest and largest, but several discipline-specific
                preprint servers have emerged:
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {[
                  {
                    name: "bioRxiv",
                    url: "biorxiv.org",
                    field: "Biology and life sciences",
                    note: "Cold Spring Harbor Lab",
                  },
                  {
                    name: "medRxiv",
                    url: "medrxiv.org",
                    field: "Medicine and clinical research",
                    note: "Cold Spring Harbor Lab, BMJ, Yale",
                  },
                  {
                    name: "ChemRxiv",
                    url: "chemrxiv.org",
                    field: "Chemistry",
                    note: "American Chemical Society",
                  },
                  {
                    name: "Research Square",
                    url: "researchsquare.com",
                    field: "Multidisciplinary",
                    note: "Now part of Springer Nature",
                  },
                  {
                    name: "SocArXiv",
                    url: "osf.io/preprints/socarxiv",
                    field: "Social sciences",
                    note: "Open Society Foundations",
                  },
                  {
                    name: "PsyArXiv",
                    url: "psyarxiv.com",
                    field: "Psychology",
                    note: "Society for the Improvement of Psychological Science",
                  },
                ].map((srv) => (
                  <div
                    key={srv.name}
                    className="rounded-lg border border-border/40 bg-card/30 p-3"
                  >
                    <p className="font-medium text-sm text-foreground">
                      {srv.name}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {srv.field}
                    </p>
                    <p className="text-[11px] text-muted-foreground/60 mt-0.5">
                      {srv.note} ·{" "}
                      <a
                        href={`https://${srv.url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline"
                      >
                        {srv.url}
                      </a>
                    </p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                This app can search arXiv, bioRxiv, medRxiv, ChemRxiv, and
                Research Square simultaneously via the Search page (toggle
                servers under Options).
              </p>
            </div>
          </Card>
        </div>
      )}

      {tab === "App guide" && (
        <div className="space-y-4">
          <Card>
            <CardTitle>Ports and layout</CardTitle>
            <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
              <li>
                Backend API (and MCP over HTTP) on port{" "}
                <strong className="text-foreground">10770</strong>.
              </li>
              <li>
                Vite frontend preview on port{" "}
                <strong className="text-foreground">10771</strong>.
              </li>
              <li>
                Sidebar navigation, top status bar, and a collapsible log panel
                at the bottom.
              </li>
            </ul>
          </Card>

          <Card>
            <CardTitle>What is the depot?</CardTitle>
            <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
              Your <strong className="text-foreground">depot</strong> is the
              local paper library: files and a SQLite database on your machine.
              Ingesting a paper downloads its full text so you can search it
              later. Favorites are bookmarks only — they do not download the
              paper unless you also ingest it.
            </p>
          </Card>

          <Card>
            <CardTitle>Pages at a glance</CardTitle>
            <div className="mt-3 space-y-2 text-sm text-muted-foreground">
              {[
                {
                  name: "Search arXiv",
                  desc: "Keyword search across arXiv (and optionally other preprint servers). Filter by category, look up a paper ID, or browse new submissions.",
                },
                {
                  name: "Sweeps",
                  desc: "Saved query templates, favorites, and search history. Click a starter query to jump to Search with it pre-filled.",
                },
                {
                  name: "Search library",
                  desc: "Full-text search over your ingested papers. Supports keyword (FTS), semantic (vector), and hybrid mode.",
                },
                {
                  name: "Your library (depot)",
                  desc: "All ingested papers with epistemic profiles — structured breakdowns of what kind of evidence each paper provides.",
                },
                {
                  name: "Favorites",
                  desc: "Bookmarked arXiv IDs and saved search queries.",
                },
                {
                  name: "Chat",
                  desc: "LLM chat with the arxiv-researcher skill as the system prompt.",
                },
                {
                  name: "Skills",
                  desc: "Markdown skill definitions that MCP clients can load.",
                },
                {
                  name: "Lab Blogs",
                  desc: "Fetch recent posts from Anthropic, Google Research, and DeepMind blogs.",
                },
                {
                  name: "Fleet apps",
                  desc: "Auto-discovered MCP webapps on the same machine.",
                },
                {
                  name: "Settings",
                  desc: "LLM provider selection, media fetch policy, and API key status.",
                },
              ].map((p) => (
                <p key={p.name}>
                  <strong className="text-foreground">{p.name}</strong> —{" "}
                  {p.desc}
                </p>
              ))}
            </div>
          </Card>

          <Card>
            <CardTitle>Skills and usage tips</CardTitle>
            <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
              <li>
                Use Search as your incoming feed; use Your library for anything
                worth revisiting.
              </li>
              <li>
                Save 3-6 favorite queries by topic (AI safety, evals,
                interpretability, governance).
              </li>
              <li>
                Use category latest for "what changed today"; use keyword search
                for specific hypotheses.
              </li>
              <li>
                When a paper matters, ingest it immediately so quote-level
                search works later.
              </li>
            </ul>
          </Card>
        </div>
      )}

      {tab === "API & MCP" && (
        <div className="space-y-4">
          <Card>
            <CardTitle>How this app talks to arXiv</CardTitle>
            <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
              The backend uses the official{" "}
              <a
                className="text-primary hover:underline"
                href="https://arxiv.org/help/api"
                target="_blank"
                rel="noreferrer"
              >
                arXiv public API
              </a>{" "}
              via the <strong className="text-foreground">arxiv</strong> Python
              library, which wraps the Atom feed at{" "}
              <code className="text-xs">export.arxiv.org/api/query</code>. No
              account or API key required.
            </p>
          </Card>

          <Card>
            <CardTitle>Rate limits</CardTitle>
            <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
              <li>
                arXiv asks for at most{" "}
                <strong className="text-foreground">
                  1 request every 3 seconds
                </strong>
                ; enforced automatically.
              </li>
              <li>
                Result sets capped at{" "}
                <strong className="text-foreground">2000 per query</strong> —
                use date filters or narrower categories to stay under this.
              </li>
              <li>
                PDF downloads are not explicitly rate-limited but the robots
                policy asks for a delay between requests.
              </li>
            </ul>
          </Card>

          <Card>
            <CardTitle>MCP (Model Context Protocol)</CardTitle>
            <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
              This server exposes all its tools over MCP at{" "}
              <code className="text-xs">http://127.0.0.1:10770/mcp</code>.
              Clients like Cursor, Claude Desktop, and opencode can connect and
              use the same search, ingest, and analysis tools programmatically.
              The web UI is a thin layer on top of the same backend — everything
              the browser can do, an MCP client can do too.
            </p>
          </Card>
        </div>
      )}

      {tab === "Workflows" && (
        <div className="space-y-4">
          <Card>
            <CardTitle>Practical SI reading protocol</CardTitle>
            <ol className="mt-3 text-sm text-muted-foreground space-y-2 list-decimal pl-5">
              <li>
                Run one broad sweep (new submissions) plus one focused query
                (alignment, evals, interpretability, etc.).
              </li>
              <li>
                For each candidate paper, write one sentence: what claim would
                matter if true?
              </li>
              <li>
                Check evaluation realism: toy benchmark or deployment-relevant
                setting?
              </li>
              <li>
                Ingest only the high-signal papers into your depot; skip noise.
              </li>
              <li>
                Use Search library to track repeated assumptions, metrics, and
                failure modes across papers.
              </li>
            </ol>
          </Card>

          <Card>
            <CardTitle>Agentic workflows (copy into your AI client)</CardTitle>
            <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
              <li>
                <strong className="text-foreground">Daily sweep:</strong> "Run a
                24h sweep in cs.AI, then search for alignment, evals, and
                interpretability. Return top 5 papers with one-line
                why-it-matters notes."
              </li>
              <li>
                <strong className="text-foreground">Compare claims:</strong>{" "}
                "Ingest these 2 papers and compare threat model, assumptions,
                eval setup, and deployment relevance."
              </li>
              <li>
                <strong className="text-foreground">Track trend:</strong> "For
                the last 7 days in cs.LG, extract recurring benchmark names and
                whether safety constraints are discussed."
              </li>
            </ul>
          </Card>

          <Card>
            <CardTitle>Prompt examples</CardTitle>
            <div className="mt-3 space-y-2 text-sm text-muted-foreground">
              <p className="font-mono text-xs bg-background/60 border border-border/40 rounded p-2">
                Find recent papers on scalable oversight and summarize key
                methods in 5 bullets.
              </p>
              <p className="font-mono text-xs bg-background/60 border border-border/40 rounded p-2">
                Compare these papers on objective robustness. Highlight any
                reward hacking blind spots.
              </p>
              <p className="font-mono text-xs bg-background/60 border border-border/40 rounded p-2">
                Build a weekly SI reading list: 3 capability papers, 3 safety
                papers, and 2 governance papers.
              </p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

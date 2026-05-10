import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";

export function HelpPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <PageHero
        eyebrow="Reference"
        title="Help"
        lead="How this web UI is laid out, why arXiv is important for SI work, what “depot” means, and where to read more. For install and MCP setup, use the project README on GitHub."
      />

      <Card>
        <CardTitle>Ports and layout</CardTitle>
        <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
          <li>
            Layout follows the fleet webapp guide:{" "}
            <a
              className="text-primary hover:underline"
              href="https://github.com/sandraschi/mcp-central-docs/blob/master/standards/WEBAPP_STANDARDS.md"
              target="_blank"
              rel="noreferrer"
            >
              WEBAPP_STANDARDS.md
            </a>
          </li>
          <li>
            Backend API (and MCP over HTTP) use port <strong className="text-foreground">10770</strong>. This Vite
            preview uses <strong className="text-foreground">10771</strong>.
          </li>
          <li>Sidebar navigation, header strip, and the log panel at the bottom.</li>
        </ul>
      </Card>

      <Card>
        <CardTitle>Why arXiv matters (especially for SI)</CardTitle>
        <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
          <li>Most frontier AI results appear first as arXiv preprints, often long before peer review.</li>
          <li>
            That includes both <strong className="text-foreground">capability jumps</strong> and safety proposals, so
            timing matters.
          </li>
          <li>
            SI work needs rapid triage: what is novel, what is hype, what changes risk models, and what needs follow-up.
          </li>
          <li>This app helps by turning fast scanning into a reusable local library and query history.</li>
        </ul>
      </Card>

      <Card>
        <CardTitle>What is the depot?</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          Your <strong className="text-foreground">depot</strong> is the local paper library: files and a database on
          your machine. Ingesting adds full text so you can search it on the Search library page. Favorites are only
          bookmarks unless you also ingested the paper.
        </p>
      </Card>

      <Card>
        <CardTitle>Practical SI reading protocol</CardTitle>
        <ol className="mt-3 text-sm text-muted-foreground space-y-2 list-decimal pl-5">
          <li>Run one broad sweep (new submissions) plus one focused query (alignment, evals, interpretability, etc.).</li>
          <li>For each candidate paper, write one sentence: what claim would matter if true?</li>
          <li>Check evaluation realism: toy benchmark or deployment-relevant setting?</li>
          <li>Ingest only the high-signal papers into your depot; skip low-value noise.</li>
          <li>Use Search library to track repeated assumptions, metrics, and failure modes across papers.</li>
        </ol>
      </Card>

      <Card>
        <CardTitle>Agentic workflows (copy these into your AI client)</CardTitle>
        <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
          <li>
            <strong className="text-foreground">Daily sweep:</strong> “Run a 24h sweep in `cs.AI`, then search for
            alignment, evals, and interpretability. Return top 5 papers with one-line why-it-matters notes.”
          </li>
          <li>
            <strong className="text-foreground">Compare claims:</strong> “Ingest these 2 papers and compare threat model,
            assumptions, eval setup, and deployment relevance.”
          </li>
          <li>
            <strong className="text-foreground">Track trend:</strong> “For the last 7 days in `cs.LG`, extract recurring
            benchmark names and whether safety constraints are discussed.”
          </li>
        </ul>
      </Card>

      <Card>
        <CardTitle>Prompt examples</CardTitle>
        <div className="mt-3 space-y-2 text-sm text-muted-foreground">
          <p className="font-mono text-xs bg-background/60 border border-border/40 rounded p-2">
            Find recent papers on scalable oversight and summarize key methods in 5 bullets.
          </p>
          <p className="font-mono text-xs bg-background/60 border border-border/40 rounded p-2">
            Compare these papers on objective robustness. Highlight any reward hacking blind spots.
          </p>
          <p className="font-mono text-xs bg-background/60 border border-border/40 rounded p-2">
            Build a weekly SI reading list: 3 capability papers, 3 safety papers, and 2 governance papers.
          </p>
        </div>
      </Card>

      <Card>
        <CardTitle>Skills and usage tips</CardTitle>
        <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
          <li>Use Search as your incoming feed; use Your library for anything worth revisiting.</li>
          <li>Save 3-6 favorite queries by topic (AI safety/SI, evals, governance, interpretability).</li>
          <li>Use category latest for “what changed today”; use keyword search for specific hypotheses.</li>
          <li>When a paper matters, ingest it immediately so quote-level search works later.</li>
        </ul>
      </Card>

      <Card>
        <CardTitle>arXiv API — how this app talks to arXiv</CardTitle>
        <div className="mt-3 space-y-3 text-sm text-muted-foreground">
          <p className="leading-relaxed">
            All paper data comes from the{" "}
            <a
              className="text-primary hover:underline"
              href="https://arxiv.org/help/api"
              target="_blank"
              rel="noreferrer"
            >
              arXiv public API
            </a>{" "}
            — no account or API key required. The backend uses the official{" "}
            <strong className="text-foreground">arxiv</strong> Python library, which wraps the
            Atom/XML feed endpoint at{" "}
            <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
              export.arxiv.org/api/query
            </code>
            .
          </p>
          <div>
            <p className="font-medium text-foreground mb-1">What gets returned</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Paper ID, title, authors, abstract, submission and update dates</li>
              <li>Category list (primary + cross-listed)</li>
              <li>Links to abstract page, PDF, and HTML (where available)</li>
              <li>DOI and journal ref when the author supplied them</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">Rate limits and etiquette</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                arXiv asks for at most{" "}
                <strong className="text-foreground">1 request every 3 seconds</strong>; the library
                enforces this automatically.
              </li>
              <li>
                Result sets are capped at <strong className="text-foreground">2,000 per query</strong> by
                the API; use date filters or narrower categories to stay under this.
              </li>
              <li>Bulk harvesting of full text should use the OAI-PMH endpoint instead, not this API.</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">What the API does not provide</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                Full paper text — PDF fetch and parsing is handled separately by the ingest pipeline when
                you depot a paper.
              </li>
              <li>Citation counts or download statistics — those are not exposed.</li>
              <li>Peer-review or acceptance status — arXiv is a preprint server; moderation is not peer review.</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">Useful direct URLs</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                Abstract page:{" "}
                <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
                  https://arxiv.org/abs/&lt;id&gt;
                </code>
              </li>
              <li>
                PDF:{" "}
                <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
                  https://arxiv.org/pdf/&lt;id&gt;
                </code>
              </li>
              <li>
                HTML (where available):{" "}
                <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
                  https://arxiv.org/html/&lt;id&gt;
                </code>
              </li>
              <li>
                Raw Atom feed:{" "}
                <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
                  https://export.arxiv.org/api/query?search_query=…&amp;max_results=10
                </code>
              </li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">Full document download (the point of this repo)</p>
            <p className="leading-relaxed mb-2">
              When you ingest a paper, the backend fetches the full PDF from{" "}
              <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
                https://arxiv.org/pdf/&lt;id&gt;
              </code>{" "}
              and stores it locally in your depot. That local copy is what powers full-text search in Your
              library — the Atom API only supplies metadata, never content.
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                PDFs are served directly by arXiv with no auth. The URL{" "}
                <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
                  /pdf/&lt;id&gt;
                </code>{" "}
                redirects to the latest version;{" "}
                <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
                  /pdf/&lt;id&gt;v2
                </code>{" "}
                pins a specific version.
              </li>
              <li>
                HTML full text (
                <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
                  /html/&lt;id&gt;
                </code>
                ) is available for most papers submitted after mid-2023 and is easier to parse than PDF.
                The ingest pipeline prefers HTML where present.
              </li>
              <li>
                arXiv does not rate-limit PDF downloads explicitly, but their{" "}
                <a
                  className="text-primary hover:underline"
                  href="https://arxiv.org/help/robots"
                  target="_blank"
                  rel="noreferrer"
                >
                  robots policy
                </a>{" "}
                asks for a delay between requests. The ingest pipeline respects this — do not bypass it.
              </li>
              <li>
                A small number of older papers were submitted as PS or DVI source only, with no compiled
                PDF. The PDF fetch fails gracefully in these cases and only metadata is stored in the depot.
              </li>
            </ul>
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>Source code</CardTitle>
        <a
          className="text-primary text-sm hover:underline"
          href="https://github.com/sandraschi/arxiv-mcp"
          target="_blank"
          rel="noreferrer"
        >
          github.com/sandraschi/arxiv-mcp
        </a>
      </Card>
    </div>
  );
}

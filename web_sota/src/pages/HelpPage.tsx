import { Card, CardTitle } from "@/components/ui/card";

export function HelpPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold">Help</h1>

      <Card>
        <CardTitle>SOTA alignment</CardTitle>
        <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
          <li>
            Webapp standards:{" "}
            <a
              className="text-primary hover:underline"
              href="https://github.com/sandraschi/mcp-central-docs/blob/master/standards/WEBAPP_STANDARDS.md"
              target="_blank"
              rel="noreferrer"
            >
              WEBAPP_STANDARDS.md
            </a>
          </li>
          <li>Ports: backend <strong className="text-foreground">10770</strong>, Vite <strong className="text-foreground">10771</strong> (adjacent pair).</li>
          <li>Iron shell: sidebar, top context, logger panel (bottom).</li>
        </ul>
      </Card>

      <Card>
        <CardTitle>Depot RAG</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Chunks are indexed with SQLite FTS5 when you ingest. This is full-text retrieval with BM25, not embedding
          similarity. Pair with your IDE MCP for vector RAG if needed.
        </p>
      </Card>

      <Card>
        <CardTitle>Repo</CardTitle>
        <a className="text-primary text-sm hover:underline" href="https://github.com/sandraschi/arxiv-mcp" target="_blank" rel="noreferrer">
          github.com/sandraschi/arxiv-mcp
        </a>
      </Card>
    </div>
  );
}

import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";

export function HelpPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <PageHero
        eyebrow="Reference"
        title="Help"
        lead="How this web UI is laid out, what “depot” means, and where to read more. For install and MCP setup, use the project README on GitHub."
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
        <CardTitle>What is the depot?</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          Your <strong className="text-foreground">depot</strong> is the local paper library: files and a database on
          your machine. Ingesting adds full text so you can search it on the Search library page. Favorites are only
          bookmarks unless you also ingested the paper.
        </p>
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

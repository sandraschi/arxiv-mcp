import { PageHero } from "@/components/layout/PageHero";

export function ApiDocsPage() {
  return (
    <div className="space-y-4 h-[calc(100vh-8rem)] flex flex-col">
      <PageHero
        eyebrow="FastAPI"
        title="API docs"
        lead="Interactive OpenAPI (Swagger) for REST endpoints on port 10770. MCP tools use /mcp separately."
      />
      <iframe
        title="OpenAPI docs"
        src="/docs"
        className="flex-1 w-full rounded-lg border border-border bg-background min-h-[480px]"
      />
    </div>
  );
}

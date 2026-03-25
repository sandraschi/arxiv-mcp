import { useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";

type Tool = {
  name: string;
  description: string;
  params?: Record<string, string>;
  kind?: string;
};

export function ToolsPage() {
  const { log } = useLogger();
  const [tools, setTools] = useState<Tool[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiGet<{ tools: Tool[]; mcp_http_path: string }>("/api/tools");
        setTools(data.tools);
        log("info", `Loaded ${data.tools.length} tool manifests`);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="For coding agents"
        title="Tools the MCP server exposes"
        lead="These are the actions an AI assistant can run when arxiv-mcp is connected (for example from Cursor or Claude Desktop). You do not run them from this screen—you configure the client to call the server over stdio or HTTP at /mcp."
      />
      <div className="grid gap-4 md:grid-cols-2">
        {tools.map((t) => (
          <Card key={t.name}>
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-base font-mono">{t.name}</CardTitle>
              {t.kind && (
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground border border-border rounded px-1.5 py-0.5">
                  {t.kind}
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-2">{t.description}</p>
            {t.params && (
              <pre className="mt-3 text-[11px] bg-background/60 rounded p-2 overflow-x-auto">
                {JSON.stringify(t.params, null, 2)}
              </pre>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

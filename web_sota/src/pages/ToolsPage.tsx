import { useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";
import { cn } from "@/lib/utils";

type Tool = {
  name: string;
  description: string;
  params?: Record<string, string>;
  kind?: string;
};

type Prompt = {
  name: string;
  description: string;
  params?: Record<string, string>;
  tags?: string[];
};

const KIND_LABEL: Record<string, string> = {
  app: "Prefab",
  prompt: "Prompt",
};

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

function promptUsageSnippet(p: Prompt): string {
  const args = p.params
    ? Object.entries(p.params)
        .map(([k, v]) => `"${k}": "${v.split(" ")[0]}"`)
        .join(", ")
    : "";
  return `get_prompt("${p.name}", {${args}})`;
}

export function ToolsPage() {
  const { log } = useLogger();
  const [tools, setTools] = useState<Tool[]>([]);
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [tab, setTab] = useState<"tools" | "prompts">("tools");
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiGet<{ tools: Tool[]; mcp_http_path: string }>("/api/tools");
        setTools(data.tools);
        log("info", `Loaded ${data.tools.length} tools`);
      } catch (e) {
        log("error", String(e));
      }
    })();
    (async () => {
      try {
        const data = await apiGet<{ prompts: Prompt[] }>("/api/prompts");
        setPrompts(data.prompts);
        log("info", `Loaded ${data.prompts.length} prompts`);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  function handleCopy(text: string, key: string) {
    copyToClipboard(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 1500);
  }

  const tabClass = (active: boolean) =>
    cn(
      "px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors",
      active
        ? "border-primary text-primary bg-background"
        : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
    );

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Reference"
        title="MCP tools & prompts"
        lead="Tools are actions an AI assistant can call when arxiv-mcp is connected via stdio or HTTP. Prompts are reusable instruction templates loaded with get_prompt() — use them in Claude Desktop before a research session."
      />

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-border">
        <button type="button" className={tabClass(tab === "tools")} onClick={() => setTab("tools")}>
          Tools ({tools.length})
        </button>
        <button type="button" className={tabClass(tab === "prompts")} onClick={() => setTab("prompts")}>
          Prompts ({prompts.length})
        </button>
      </div>

      {tab === "tools" && (
        <div className="grid gap-4 md:grid-cols-2">
          {tools.map((t) => (
            <Card key={t.name}>
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-base font-mono">{t.name}</CardTitle>
                {t.kind && (
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground border border-border rounded px-1.5 py-0.5">
                    {KIND_LABEL[t.kind] ?? t.kind}
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-2">{t.description}</p>
              {t.params && Object.keys(t.params).length > 0 && (
                <pre className="mt-3 text-[11px] bg-background/60 rounded p-2 overflow-x-auto">
                  {JSON.stringify(t.params, null, 2)}
                </pre>
              )}
            </Card>
          ))}
        </div>
      )}

      {tab === "prompts" && (
        <div className="grid gap-4 md:grid-cols-2">
          {prompts.map((p) => {
            const snippet = promptUsageSnippet(p);
            const isCopied = copied === p.name;
            return (
              <Card key={p.name}>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base font-mono">{p.name}</CardTitle>
                  <button
                    type="button"
                    onClick={() => handleCopy(snippet, p.name)}
                    className="text-[11px] shrink-0 px-2 py-1 rounded border border-border/60 bg-muted/40 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                    title="Copy usage snippet"
                  >
                    {isCopied ? "Copied!" : "Copy"}
                  </button>
                </div>
                <p className="text-sm text-muted-foreground mt-2">{p.description}</p>
                {p.params && Object.keys(p.params).length > 0 && (
                  <div className="mt-3 space-y-1">
                    {Object.entries(p.params).map(([k, v]) => (
                      <div key={k} className="flex gap-2 text-xs">
                        <span className="font-mono text-foreground shrink-0">{k}</span>
                        <span className="text-muted-foreground">{v}</span>
                      </div>
                    ))}
                  </div>
                )}
                {p.tags && p.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {p.tags.map((t) => (
                      <span
                        key={t}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                <pre className="mt-3 text-[11px] bg-background/60 rounded p-2 overflow-x-auto text-muted-foreground">
                  {snippet}
                </pre>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

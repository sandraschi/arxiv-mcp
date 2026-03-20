import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { apiGet } from "@/api/client";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";

type Hub = {
  id: string;
  label: string;
  webapp_url: string;
  api_url?: string;
  tags?: string[];
};

export function AppsPage() {
  const { log } = useLogger();
  const [hubs, setHubs] = useState<Hub[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiGet<{ hubs: Hub[] }>("/api/fleet");
        setHubs(data.hubs);
        log("info", `Fleet hubs: ${data.hubs.length}`);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Fleet apps</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Curated from <code className="text-primary">arxiv_mcp/data/fleet_default.json</code> — edit to match your machine.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {hubs.map((h) => (
          <Card key={h.id}>
            <CardTitle className="flex items-center justify-between gap-2">
              {h.label}
              <a href={h.webapp_url} target="_blank" rel="noreferrer" className="text-primary">
                <ExternalLink className="h-4 w-4" />
              </a>
            </CardTitle>
            <div className="text-xs font-mono text-muted-foreground mt-2 break-all">{h.webapp_url}</div>
            {h.api_url && <div className="text-xs font-mono text-muted-foreground mt-1 break-all">API {h.api_url}</div>}
            {h.tags && (
              <div className="flex flex-wrap gap-1 mt-3">
                {h.tags.map((t) => (
                  <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-muted">
                    {t}
                  </span>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
      {hubs.length === 0 && <p className="text-sm text-muted-foreground">No fleet entries. Add JSON under server data.</p>}
    </div>
  );
}

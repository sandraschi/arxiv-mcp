import { useLogger } from "@/context/LoggerContext";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";

export function LogsPage() {
  const { entries, clear } = useLogger();

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Diagnostics"
        title="Session logs"
        lead="Client-side log buffer from dashboard API calls and actions. Clears on refresh unless you export."
      />
      <div className="flex gap-2">
        <Button variant="outline" size="sm" type="button" onClick={clear}>
          Clear
        </Button>
        <Button
          variant="secondary"
          size="sm"
          type="button"
          onClick={() => {
            const blob = new Blob([JSON.stringify(entries, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "arxiv-mcp-logs.json";
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          Export JSON
        </Button>
      </div>
      <Card>
        <CardTitle>Entries ({entries.length})</CardTitle>
        <ul className="mt-4 max-h-[60vh] overflow-y-auto space-y-1 font-mono text-[11px]">
          {entries.length === 0 && <li className="text-muted-foreground">No log entries yet.</li>}
          {[...entries].reverse().map((e) => (
            <li key={e.id} className="border-b border-border/30 py-1">
              <span className="text-muted-foreground">{e.ts}</span>{" "}
              <span className={e.level === "error" ? "text-destructive" : "text-primary"}>[{e.level}]</span> {e.message}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

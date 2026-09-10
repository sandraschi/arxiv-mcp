import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Health = { status: string; service: string };

function currentTheme(): string {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.classList.contains("light")
    ? "light"
    : "dark";
}

export function SettingsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [theme, setTheme] = useState(currentTheme);

  useEffect(() => {
    (async () => {
      try {
        const h = await apiGet<Health>("/api/health");
        setHealth(h);
      } catch {
        setHealth(null);
      }
    })();
  }, []);

  return (
    <div className="space-y-4" data-testid="settings-page">
      <Card className="p-4">
        <p className="text-xs text-muted-foreground">Backend</p>
        <p className="text-sm mt-1 flex items-center gap-2">
          <span
            data-testid="backend-status-dot"
            className={cn(
              "h-2 w-2 rounded-full",
              health ? "bg-green-500" : "bg-red-500",
            )}
          />
          <span data-testid="backend-status-text">
            {health ? `${health.service} · ${health.status}` : "Offline"}
          </span>
        </p>
      </Card>

      <Card className="p-4">
        <p className="text-xs text-muted-foreground">Theme</p>
        <div className="mt-2">
          <Button
            size="sm"
            variant="secondary"
            data-testid="theme-toggle"
            onClick={() => {
              const next = theme === "dark" ? "light" : "dark";
              document.documentElement.classList.toggle(
                "light",
                next === "light",
              );
              setTheme(next);
            }}
          >
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </Button>
        </div>
      </Card>

      <Card className="p-4">
        <p className="text-xs text-muted-foreground">AI settings</p>
        <p className="text-sm mt-1">
          Providers, models, API keys, VRAM, and kick-out moved to{" "}
          <Link
            to="/ai-settings"
            data-testid="settings-ai-link"
            className="text-primary hover:underline"
          >
            AI settings
          </Link>
          .
        </p>
      </Card>
    </div>
  );
}

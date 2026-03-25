import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  BookMarked,
  Boxes,
  FileSearch,
  Heart,
  HelpCircle,
  Home,
  LayoutGrid,
  Library,
  Menu,
  Search,
  Settings,
  Terminal,
  X,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { LoggerPanel } from "@/components/layout/LoggerPanel";

const nav = [
  { to: "/dashboard", label: "Home", icon: Home },
  { to: "/search", label: "Search arXiv", icon: Search },
  { to: "/semantic", label: "Search library", icon: FileSearch },
  { to: "/depot", label: "Your library", icon: Library },
  { to: "/favorites", label: "Favorites", icon: Heart },
  { to: "/tools", label: "Tools", icon: Terminal },
  { to: "/apps", label: "Fleet apps", icon: LayoutGrid },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/help", label: "Help", icon: HelpCircle },
] as const;

export function AppLayout() {
  const [open, setOpen] = useState(true);
  const [mobile, setMobile] = useState(false);
  const loc = useLocation();

  return (
    <div className="min-h-screen flex text-foreground">
      <aside
        className={cn(
          "hidden md:flex flex-col border-r border-border bg-card/40 backdrop-blur-xl h-screen sticky top-0 z-30 transition-all duration-300",
          open ? "w-64" : "w-[4.5rem]",
        )}
      >
        <div className="h-14 flex items-center gap-2 px-4 border-b border-border/60">
          <BookMarked className="h-8 w-8 text-primary shrink-0" />
          {open && (
            <div>
              <div className="font-bold leading-tight">arxiv-mcp</div>
              <div className="text-[10px] text-muted-foreground">Vite · 10771</div>
            </div>
          )}
        </div>
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive ? "bg-secondary text-secondary-foreground" : "hover:bg-muted/50",
                  !open && "justify-center px-2",
                )
              }
              title={!open ? label : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {open && label}
            </NavLink>
          ))}
        </nav>
        <div className="p-2 border-t border-border/60">
          <Button variant="ghost" className="w-full" size="sm" onClick={() => setOpen(!open)}>
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </div>
      </aside>

      {/* Mobile header */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 h-12 border-b border-border bg-background/90 backdrop-blur flex items-center px-3 gap-2">
        <Button variant="ghost" size="icon" onClick={() => setMobile(!mobile)}>
          <Menu className="h-5 w-5" />
        </Button>
        <span className="font-semibold text-sm">arxiv-mcp</span>
      </div>
      {mobile && (
        <div className="md:hidden fixed inset-0 z-40 bg-background/95 pt-14 px-3 pb-6 overflow-y-auto">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobile(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-3 text-sm mb-1",
                loc.pathname === to ? "bg-secondary" : "hover:bg-muted/50",
              )}
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0 min-h-screen pt-12 md:pt-0 pb-24 md:pb-28">
        <header className="hidden md:flex h-14 items-center border-b border-border/60 px-6 bg-background/40 backdrop-blur-sm sticky top-0 z-20">
          <div className="text-sm text-muted-foreground">
            MCP HTTP proxied at <code className="text-primary">/mcp</code> · API{" "}
            <code className="text-primary">/api</code>
          </div>
        </header>
        <main className="flex-1 p-4 md:p-6 max-w-6xl w-full mx-auto">
          <Outlet />
        </main>
      </div>

      <LoggerPanel />
    </div>
  );
}

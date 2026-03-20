import { useCallback, useEffect, useState } from "react";

type Health = { status: string; service: string };

export function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [q, setQ] = useState("cat:cs.AI");
  const [loading, setLoading] = useState(false);
  const [payload, setPayload] = useState<string>("");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((j) => setHealth(j as Health))
      .catch(() => setHealth({ status: "error", service: "arxiv-mcp" }));
  }, []);

  const runSearch = useCallback(async () => {
    setLoading(true);
    setPayload("");
    try {
      const u = new URL("/api/search", window.location.origin);
      u.searchParams.set("q", q);
      u.searchParams.set("limit", "8");
      const r = await fetch(u.toString());
      const j = await r.json();
      setPayload(JSON.stringify(j, null, 2));
    } catch (e) {
      setPayload(String(e));
    } finally {
      setLoading(false);
    }
  }, [q]);

  return (
    <div className="app">
      <header className="hero">
        <h1>arxiv-mcp</h1>
        <p>
          Dashboard for the FastMCP 3.1 server. Experimental HTML full text is fetched
          server-side at <code>arxiv.org/html/…</code> when available.
        </p>
        <p className="status">
          API:{" "}
          {health ? (
            <>
              {health.status} · {health.service}
            </>
          ) : (
            "checking…"
          )}
        </p>
      </header>

      <section className="panel">
        <div className="row">
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="arXiv query (e.g. cat:cs.LG AND all:diffusion)"
            aria-label="Search query"
          />
          <button type="button" disabled={loading} onClick={runSearch}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
        {payload ? <pre>{payload}</pre> : null}
      </section>
    </div>
  );
}

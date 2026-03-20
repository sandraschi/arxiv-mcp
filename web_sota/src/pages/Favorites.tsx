import { useCallback, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";

type Fav = { arxiv_id: string; title: string | null; note: string | null; created_at: number };

export function Favorites() {
  const { log } = useLogger();
  const [list, setList] = useState<Fav[]>([]);
  const [id, setId] = useState("");
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await apiGet<{ favorites: Fav[] }>("/api/favorites");
      setList(data.favorites);
    } catch (e) {
      log("error", String(e));
    }
  }, [log]);

  useEffect(() => {
    load();
  }, [load]);

  async function add() {
    if (!id.trim()) return;
    try {
      await apiPost("/api/favorites", { arxiv_id: id.trim(), title: title.trim() || null, note: note.trim() || null });
      log("info", `Favorite ${id}`);
      setId("");
      setTitle("");
      setNote("");
      await load();
    } catch (e) {
      log("error", String(e));
    }
  }

  async function remove(arxivId: string) {
    try {
      await apiDelete(`/api/favorites/${encodeURIComponent(arxivId)}`);
      await load();
    } catch (e) {
      log("error", String(e));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Favorites</h1>
        <p className="text-sm text-muted-foreground mt-1">Local SQLite — sync is this machine only.</p>
      </div>

      <Card>
        <CardTitle>Add</CardTitle>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <Input placeholder="arxiv id" value={id} onChange={(e) => setId(e.target.value)} />
          <Input placeholder="title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
          <Input placeholder="note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <Button className="mt-3" onClick={add}>
          Save favorite
        </Button>
      </Card>

      <Card>
        <CardTitle>Saved ({list.length})</CardTitle>
        <ul className="mt-4 space-y-3">
          {list.map((f) => (
            <li key={f.arxiv_id} className="flex flex-wrap items-start justify-between gap-2 border-b border-border/30 pb-3">
              <div>
                <div className="font-mono text-sm text-primary">{f.arxiv_id}</div>
                {f.title && <div className="font-medium">{f.title}</div>}
                {f.note && <div className="text-sm text-muted-foreground">{f.note}</div>}
              </div>
              <Button variant="outline" size="sm" onClick={() => remove(f.arxiv_id)}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

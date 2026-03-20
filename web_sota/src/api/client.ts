const base = "";

async function parseErr(r: Response): Promise<string> {
  try {
    const j = await r.json();
    if (j && typeof j.detail === "string") return j.detail;
    return JSON.stringify(j);
  } catch {
    return await r.text();
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(`${base}${path}`);
  if (!r.ok) throw new Error(await parseErr(r));
  return r.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseErr(r));
  return r.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  const r = await fetch(`${base}${path}`, { method: "DELETE" });
  if (!r.ok) throw new Error(await parseErr(r));
}

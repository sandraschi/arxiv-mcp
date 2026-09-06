/** Empty in Vite dev (proxy); direct backend in production / Tauri. */
const base = import.meta.env.DEV ? "" : "http://127.0.0.1:10770";

/** Base prefix for raw fetch calls (streaming bypasses the timeout wrapper). */
export const API_BASE = base;
const TIMEOUT_MS = 30_000;

async function parseErr(r: Response): Promise<string> {
  try {
    const text = await r.text();
    try {
      const j = JSON.parse(text);
      if (j && typeof j.detail === "string") return j.detail;
      return JSON.stringify(j);
    } catch {
      return text || `HTTP ${r.status}`;
    }
  } catch {
    return `HTTP ${r.status}`;
  }
}

function fetchWithTimeout(
  url: string,
  init: RequestInit = {},
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  return fetch(url, { ...init, signal: controller.signal })
    .catch((e) => {
      if (e instanceof DOMException && e.name === "AbortError") {
        throw new Error(`Request timed out after ${TIMEOUT_MS / 1000}s`);
      }
      throw e;
    })
    .finally(() => clearTimeout(timer));
}

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetchWithTimeout(`${base}${path}`);
  if (!r.ok) throw new Error(await parseErr(r));
  return r.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetchWithTimeout(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseErr(r));
  return r.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  const r = await fetchWithTimeout(`${base}${path}`, { method: "DELETE" });
  if (!r.ok) throw new Error(await parseErr(r));
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const r = await fetchWithTimeout(`${base}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await parseErr(r));
  return r.json() as Promise<T>;
}

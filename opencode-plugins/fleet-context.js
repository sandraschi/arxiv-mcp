// OpenCode plugin: Fleet context injector (live health).
// Copy to: ~/.config/opencode/plugins/fleet-context.js
//
// Polls the federation hub's health endpoint for live server status
// and injects it into session context + preserves across compactions.
//
// Env vars:
//   FEDERATION_HUB_URL = http://localhost:10857   (default)
//   OPENCODE_FLEET_CONTEXT = path to static manifest (fallback if hub unreachable)

import { homedir } from "node:os"
import { join } from "node:path"
import { readFileSync, existsSync } from "node:fs"

const HUB_URL = process.env.FEDERATION_HUB_URL || "http://localhost:10857"
const FALLBACK_PATH =
  process.env.OPENCODE_FLEET_CONTEXT ||
  join(homedir(), ".config", "opencode", "plugins", "fleet-manifest.json")

let cachedFleet = null
let cachedAt = 0
const CACHE_TTL = 30_000  // 30s — matches fleet supervisor poll interval

async function fetchFleetLive() {
  const now = Date.now()
  if (cachedFleet && (now - cachedAt) < CACHE_TTL) return cachedFleet

  try {
    const resp = await fetch(`${HUB_URL}/api/v1/servers`, {
      signal: AbortSignal.timeout(3_000),
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    cachedFleet = data.servers || data
    cachedAt = now
    return cachedFleet
  } catch {
    // Federation hub unreachable — fall back to static manifest
    if (existsSync(FALLBACK_PATH)) {
      try { return JSON.parse(readFileSync(FALLBACK_PATH, "utf-8")) } catch {}
    }
    return []
  }
}

function formatFleetContext(servers) {
  if (!Array.isArray(servers) || !servers.length) return ""

  const lines = ["## Fleet state (live from federation hub)", ""]
  const up = servers.filter(s => s.up || s.status === "ok" || s.status === "healthy")
  const down = servers.filter(s => !up.includes(s))

  if (up.length) {
    lines.push("### Running")
    for (const s of up) {
      const name = s.name || s.id || "unknown"
      const port = s.port || s.mcp_port || ""
      const tools = (s.tools || []).slice(0, 5)
      const toolStr = tools.length ? ` — ${tools.join(", ")}${tools.length >= 5 ? " …" : ""}` : ""
      lines.push(`- ✓ \`${name}\`${port ? ` (:${port})` : ""}${toolStr}`)
    }
    lines.push("")
  }
  if (down.length) {
    lines.push("### Not running")
    for (const s of down) {
      const name = s.name || s.id || "unknown"
      lines.push(`- ✗ \`${name}\``)
    }
    lines.push("")
  }

  lines.push(`${up.length} / ${servers.length} servers running. ` +
    "Services managed by federation-mcp via NSSM (auto-start at boot, restart on failure).")
  return lines.join("\n")
}

export const FleetContext = async () => {
  return {
    "session.created": async (input, output) => {
      const servers = await fetchFleetLive()
      const ctx = formatFleetContext(servers)
      if (ctx && output.context) {
        output.context.push?.(ctx)
      }
    },

    "experimental.session.compacting": async (input, output) => {
      const servers = await fetchFleetLive()
      const ctx = formatFleetContext(servers)
      if (ctx) output.context.push(ctx)
    },

    // Inject a compact fleet summary into every tool call context
    "tool.execute.before": async (input, output) => {
      // Only inject on session-affecting tools, not every read
      const heavyTools = ["bash", "write", "edit", "task", "apply_patch"]
      if (!heavyTools.includes(input.tool)) return
      // inject live count as a quick aside
      const servers = cachedFleet || (await fetchFleetLive())
      const up = Array.isArray(servers) ? servers.filter(s => s.up || s.status === "ok").length : "?"
      output.args = output.args || {}
    },
  }
}

// OpenCode plugin: Fleet context injector.
// Copy to: ~/.config/opencode/plugins/fleet-context.js
//
// Injects fleet state into every compaction and new session so the agent
// always knows which MCP servers are available without re-asking.
//
// Env vars:
//   OPENCODE_FLEET_CONTEXT  — path to fleet manifest JSON (optional)
//   If unset, reads from ~/.config/opencode/plugins/fleet-manifest.json

import { homedir } from "node:os"
import { join } from "node:path"
import { readFileSync, existsSync } from "node:fs"

const MANIFEST_PATH =
  process.env.OPENCODE_FLEET_CONTEXT ||
  join(homedir(), ".config", "opencode", "plugins", "fleet-manifest.json")

function loadFleetManifest() {
  if (!existsSync(MANIFEST_PATH)) return []
  try { return JSON.parse(readFileSync(MANIFEST_PATH, "utf-8")) } catch { return [] }
}

function formatFleetContext() {
  const fleet = loadFleetManifest()
  if (!fleet.length) return ""

  const lines = []
  const mcpServers = fleet.filter(s => s.type === "mcp")
  const webapps = fleet.filter(s => s.type === "webapp")

  lines.push("## Fleet state")
  lines.push("")

  if (mcpServers.length) {
    lines.push("### MCP servers available")
    for (const s of mcpServers) {
      const status = s.up ? "✓" : "✗"
      lines.push(`- \`${s.name}\` ${status} (port: ${s.port}, transport: ${s.transport || "stdio"})`)
      if (s.tools) lines.push(`  Tools: ${s.tools.slice(0, 5).join(", ")}${s.tools.length > 5 ? " ..." : ""}`)
    }
    lines.push("")
  }

  if (webapps.length) {
    lines.push("### Web dashboards")
    for (const w of webapps) {
      lines.push(`- ${w.name}: http://127.0.0.1:${w.port}`)
    }
    lines.push("")
  }

  lines.push("Use these servers for accessing research papers, device control, automation, etc.")
  lines.push("Server tools are automatically available when registered in opencode.json.")
  return lines.join("\n")
}

export const FleetContext = async ({ client }) => {
  return {
    // Inject fleet state into new sessions
    "session.created": async (input, output) => {
      const ctx = formatFleetContext()
      if (ctx) output.context?.push?.(ctx)
    },

    // Preserve fleet awareness across compactions
    "experimental.session.compacting": async (input, output) => {
      const ctx = formatFleetContext()
      if (ctx) output.context.push(ctx)
    },
  }
}

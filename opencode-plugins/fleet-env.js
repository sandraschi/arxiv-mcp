// OpenCode plugin: Fleet env injector.
// Copy to: ~/.config/opencode/plugins/fleet-env.js
//
// Injects fleet-standard environment variables into every shell (AI tools
// and user terminal) so MCP servers and Python scripts get consistent config.
//
// Reads from: ~/.config/opencode/plugins/fleet-env.json

import { homedir } from "node:os"
import { join } from "node:path"
import { readFileSync, existsSync } from "node:fs"

const ENV_PATH = join(homedir(), ".config", "opencode", "plugins", "fleet-env.json")

function loadEnv() {
  if (!existsSync(ENV_PATH)) return {}
  try { return JSON.parse(readFileSync(ENV_PATH, "utf-8")) } catch { return {} }
}

export const FleetEnv = async () => {
  return {
    "shell.env": async (input, output) => {
      const injected = loadEnv()
      // Only inject keys not already set in the environment
      for (const [k, v] of Object.entries(injected)) {
        if (!process.env[k]) {
          output.env[k] = v
        }
      }
    },
  }
}

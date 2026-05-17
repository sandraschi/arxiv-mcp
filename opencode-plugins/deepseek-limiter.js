// OpenCode plugin: DeepSeek cost limiter
// Copy to: ~/.config/opencode/plugins/deepseek-limiter.js

// Env vars:
//   OPENCODE_DEEPSEEK_DAILY_BUDGET_USD = 1.00
//   OPENCODE_DEEPSEEK_INPUT_COST_PER_1K  = 0.27   (DeepSeek V3)
//   OPENCODE_DEEPSEEK_OUTPUT_COST_PER_1K = 1.10
// Log: ~/.config/opencode/plugins/deepseek-usage.json

import { homedir } from "node:os";
import { join } from "node:path";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";

// ── Config ────────────────────────────────────────────────────────────────

const DAILY_BUDGET = Number.parseFloat(process.env.OPENCODE_DEEPSEEK_DAILY_BUDGET_USD || "1.00");
const INPUT_COST = Number.parseFloat(process.env.OPENCODE_DEEPSEEK_INPUT_COST_PER_1K || "0.27") / 1000;
const OUTPUT_COST = Number.parseFloat(process.env.OPENCODE_DEEPSEEK_OUTPUT_COST_PER_1K || "1.10") / 1000;
const STORE = join(homedir(), ".config", "opencode", "plugins", "deepseek-usage.json");

// ── State ──────────────────────────────────────────────────────────────────

let tokensIn = 0;
let tokensOut = 0;
let budgetBlocked = false;
let lastToastAt = 0;

function today() { return new Date().toISOString().slice(0, 10); }

function loadStore() {
  if (!existsSync(STORE)) return {};
  try { return JSON.parse(readFileSync(STORE, "utf-8")); } catch { return {}; }
}
function saveStore(data) {
  mkdirSync(join(homedir(), ".config", "opencode", "plugins"), { recursive: true });
  writeFileSync(STORE, JSON.stringify(data, null, 2), "utf-8");
}

function dailyCost() {
  const store = loadStore();
  const t = today();
  const past = (store[t] || {}).cost || 0;
  return past + tokensIn * INPUT_COST + tokensOut * OUTPUT_COST;
}

function formatUSD(n) {
  return "$" + n.toFixed(3);
}

// ── Plugin ──────────────────────────────────────────────────────────────────

export const DeepSeekLimiter = async ({ client }) => {

  return {
    // Track token usage from assistant messages
    "message.updated": async (input, output) => {
      const msg = output.message;
      if (msg?.role !== "assistant") return;
      const usage = msg.usage;
      if (!usage) return;
      tokensIn += usage.inputTokens || 0;
      tokensOut += usage.outputTokens || 0;
    },

    // Block tools when budget exceeded (read-only still works)
    "tool.execute.before": async (input) => {
      const cost = dailyCost();
      if (cost >= DAILY_BUDGET && !budgetBlocked) {
        budgetBlocked = true;
        const store = loadStore();
        store[today()] = { input: tokensIn, output: tokensOut, cost };
        saveStore(store);
      }
      if (budgetBlocked) {
        const readOnly = ["read", "glob", "grep", "list", "lsp"];
        if (!readOnly.includes(input.tool)) {
          const msg = `[deepseek-limiter] Daily budget ${formatUSD(cost)}/${formatUSD(DAILY_BUDGET)} exceeded. ` +
                      `Open a new session or increase OPENCODE_DEEPSEEK_DAILY_BUDGET_USD.`;
          throw new Error(msg);
        }
      }
    },

    // Persist + reset on session end
    event: async ({ event }) => {
      if (event.type === "session.idle" || event.type === "session.deleted") {
        if (tokensIn + tokensOut > 0) {
          const store = loadStore();
          const t = today();
          const cur = store[t] || { input: 0, output: 0, cost: 0 };
          store[t] = {
            input: cur.input + tokensIn,
            output: cur.output + tokensOut,
            cost: cur.cost + tokensIn * INPUT_COST + tokensOut * OUTPUT_COST,
          };
          saveStore(store);
        }
        tokensIn = 0;
        tokensOut = 0;
        budgetBlocked = false;
      }
    },

    // Toast at 80%+
    "tui.toast.show": async (input, output) => {
      const cost = dailyCost();
      const pct = (cost / DAILY_BUDGET) * 100;
      if (pct >= 80) {
        const now = Date.now();
        if (now - lastToastAt < 60_000) return; // rate limit: 1/min
        lastToastAt = now;
        output.message = `[DeepSeek] ${pct.toFixed(0)}% daily budget used (${formatUSD(cost)})`;
      }
    },
  };
};

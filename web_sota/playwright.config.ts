import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  retries: 1,
  use: {
    baseURL: "http://127.0.0.1:10771",
    headless: true,
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "uv run python -m arxiv_mcp --serve",
      port: 10770,
      cwd: "..",
      timeout: 60000,
      reuseExistingServer: true,
    },
    {
      command: "npm run dev",
      port: 10771,
      cwd: ".",
      timeout: 60000,
      reuseExistingServer: true,
    },
  ],
});

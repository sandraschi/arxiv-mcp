import { test, expect } from "@playwright/test";

test.describe("Frontend", () => {
  test("Dashboard loads with KPIs", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByTestId("dashboard")).toBeVisible();
    await expect(page.getByTestId("backend-dot")).toBeVisible();
    await expect(page.getByText("arxiv-mcp")).toBeVisible();
  });

  test("Sidebar navigation works across all pages", async ({ page }) => {
    await page.goto("/dashboard");
    const nav = page.locator("aside nav");
    const links = [
      { name: "Search arXiv", url: /\/search/ },
      { name: "Your library", url: /\/depot/ },
      { name: "Favorites", url: /\/favorites/ },
      { name: "Tools & Prompts", url: /\/tools/ },
      { name: "Chat", url: /\/chat/ },
      { name: "Skills", url: /\/skills/ },
      { name: "Logs", url: /\/logs/ },
      { name: "Settings", url: /\/settings/ },
      { name: "Help", url: /\/help/ },
    ];
    for (const { name, url } of links) {
      await nav.getByRole("link", { name, exact: true }).click();
      await expect(page).toHaveURL(url);
    }
  });

  test("Search page has presets and input", async ({ page }) => {
    await page.goto("/search");
    await expect(page.getByTestId("search-page")).toBeVisible();
    await expect(page.getByTestId("search-card")).toBeVisible();
    await expect(page.getByTestId("search-button")).toBeVisible();
    await expect(page.getByText("Consciousness & AI")).toBeVisible();
    await expect(page.getByText("Mechanistic interpretability")).toBeVisible();
  });

  test("Tools page lists tools", async ({ page }) => {
    await page.goto("/tools");
    await expect(page.getByText("MCP tools & prompts")).toBeVisible();
  });

  test("Chat page has personality selector, export, and clear", async ({ page }) => {
    await page.goto("/chat");
    await expect(page.getByTestId("chat-page")).toBeVisible();
    await expect(page.getByTestId("chat-controls")).toBeVisible();
    await expect(page.getByTestId("personality-select")).toBeVisible();
    await expect(page.getByTestId("chat-export")).toBeDisabled();
    await expect(page.getByTestId("chat-clear")).toBeDisabled();
    await expect(page.getByTestId("chat-input")).toBeVisible();
    await expect(page.getByTestId("chat-send")).toBeDisabled();
    // Check all 4 personality options exist
    const select = page.getByTestId("personality-select");
    const options = await select.locator("option").allTextContents();
    expect(options).toContain("Research Assistant");
    expect(options).toContain("Expert Reviewer");
    expect(options).toContain("Quick Summarizer");
    expect(options).toContain("Custom");
  });

  test("Depot page has ingest and filters", async ({ page }) => {
    await page.goto("/depot");
    await expect(page.getByTestId("depot-page")).toBeVisible();
    await expect(page.getByTestId("depot-ingest")).toBeVisible();
    await expect(page.getByTestId("depot-filters-toggle")).toBeVisible();
    await expect(page.getByTestId("depot-panels")).toBeVisible();
    await expect(page.getByTestId("depot-reader")).toBeVisible();
  });

  test("API docs page loads", async ({ page }) => {
    await page.goto("/swagger");
    await expect(page.getByRole("heading", { name: "API docs" })).toBeVisible();
  });

  test("Skills page loads", async ({ page }) => {
    await page.goto("/skills");
    await expect(page.getByText("Bundled skills")).toBeVisible();
  });

  test("Logs page loads", async ({ page }) => {
    await page.goto("/logs");
    await expect(page.getByText("Session logs")).toBeVisible();
  });

  test("Settings page loads", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByText("Configuration")).toBeVisible();
  });

  test("Help page loads", async ({ page }) => {
    await page.goto("/help");
    await expect(page.getByText("How this web UI is laid out")).toBeVisible();
  });

  test("Framer Motion page transitions work", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Chat", exact: true }).click();
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.getByTestId("chat-page")).toBeVisible();
    await page.getByRole("link", { name: "Search arXiv", exact: true }).click();
    await expect(page).toHaveURL(/\/search/);
    await expect(page.getByTestId("search-page")).toBeVisible();
  });
});

test.describe("REST API", () => {
  test("GET /api/health returns ok", async ({ request }) => {
    const resp = await request.get("/api/health");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe("ok");
  });

  test("GET /api/capabilities returns tools", async ({ request }) => {
    const resp = await request.get("/api/capabilities");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.tool_count).toBeGreaterThan(10);
  });

  test("GET /api/skills returns arxiv-researcher", async ({ request }) => {
    const resp = await request.get("/api/skills");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.count).toBeGreaterThan(0);
  });
});

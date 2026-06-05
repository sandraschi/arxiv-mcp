import { test, expect } from "@playwright/test";

test.describe("Frontend", () => {
  test("Dashboard loads", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("arxiv-mcp", { exact: false }).first()).toBeVisible();
  });

  test("Tools page loads", async ({ page }) => {
    await page.goto("/tools");
    await expect(page.getByText("MCP tools & prompts")).toBeVisible();
  });

  test("API docs page loads", async ({ page }) => {
    await page.goto("/swagger");
    await expect(page.getByRole("heading", { name: "API docs" })).toBeVisible();
  });

  test("Chat page loads", async ({ page }) => {
    await page.goto("/chat");
    await expect(page.getByRole("heading", { name: "Chat" })).toBeVisible();
  });

  test("Logs page loads", async ({ page }) => {
    await page.goto("/logs");
    await expect(page.getByText("Session logs")).toBeVisible();
  });

  test("Skills page loads", async ({ page }) => {
    await page.goto("/skills");
    await expect(page.getByText("Bundled skills")).toBeVisible();
  });

  test("Navigation to depot works", async ({ page }) => {
    await page.goto("/dashboard");
    await page.locator("aside nav").getByRole("link", { name: "Your library", exact: true }).click();
    await expect(page).toHaveURL(/\/depot/);
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

# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: arxiv-mcp.spec.ts >> Frontend >> Dashboard loads with KPIs
- Location: e2e\arxiv-mcp.spec.ts:4:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('arxiv-mcp')
Expected: visible
Error: strict mode violation: getByText('arxiv-mcp') resolved to 4 elements:
    1) <div class="font-bold leading-tight">arxiv-mcp</div> aka getByRole('complementary').getByText('arxiv-mcp')
    2) <span class="font-semibold text-sm">arxiv-mcp</span> aka locator('span').filter({ hasText: 'arxiv-mcp' })
    3) <p class="text-xs font-semibold uppercase tracking-wider text-primary">arxiv-mcp</p> aka getByLabel('Read and file arXiv papers').getByText('arxiv-mcp')
    4) <p class="text-2xl font-semibold mt-1">arxiv-mcp</p> aka getByTestId('kpi-server').getByText('arxiv-mcp')

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByText('arxiv-mcp')

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]:
      - img [ref=e6]
      - generic [ref=e9]:
        - generic [ref=e10]: arxiv-mcp
        - generic [ref=e11]: Vite · 10771
      - button "Collapse sidebar" [ref=e12] [cursor=pointer]:
        - img [ref=e13]
    - navigation [ref=e15]:
      - link "Home" [ref=e16] [cursor=pointer]:
        - /url: /dashboard
        - img [ref=e17]
        - text: Home
      - link "Search arXiv" [ref=e20] [cursor=pointer]:
        - /url: /search
        - img [ref=e21]
        - text: Search arXiv
      - link "Sweeps" [ref=e24] [cursor=pointer]:
        - /url: /sweeps
        - img [ref=e25]
        - text: Sweeps
      - link "Search library" [ref=e28] [cursor=pointer]:
        - /url: /semantic
        - img [ref=e29]
        - text: Search library
      - link "Your library" [ref=e34] [cursor=pointer]:
        - /url: /depot
        - img [ref=e35]
        - text: Your library
      - link "Favorites" [ref=e37] [cursor=pointer]:
        - /url: /favorites
        - img [ref=e38]
        - text: Favorites
      - link "Tools & Prompts" [ref=e40] [cursor=pointer]:
        - /url: /tools
        - img [ref=e41]
        - text: Tools & Prompts
      - link "Chat" [ref=e43] [cursor=pointer]:
        - /url: /chat
        - img [ref=e44]
        - text: Chat
      - link "Skills" [ref=e46] [cursor=pointer]:
        - /url: /skills
        - img [ref=e47]
        - text: Skills
      - link "API docs" [ref=e49] [cursor=pointer]:
        - /url: /swagger
        - img [ref=e50]
        - text: API docs
      - link "Logs" [ref=e55] [cursor=pointer]:
        - /url: /logs
        - img [ref=e56]
        - text: Logs
      - link "Lab Blogs" [ref=e59] [cursor=pointer]:
        - /url: /anthropic
        - img [ref=e60]
        - text: Lab Blogs
      - link "Fleet apps" [ref=e63] [cursor=pointer]:
        - /url: /apps
        - img [ref=e64]
        - text: Fleet apps
      - link "Settings" [ref=e69] [cursor=pointer]:
        - /url: /settings
        - img [ref=e70]
        - text: Settings
      - link "Help" [ref=e73] [cursor=pointer]:
        - /url: /help
        - img [ref=e74]
        - text: Help
  - generic [ref=e77]:
    - banner [ref=e78]:
      - generic [ref=e79]:
        - text: MCP HTTP proxied at
        - code [ref=e80]: /mcp
        - text: · API
        - code [ref=e81]: /api
    - main [ref=e82]:
      - generic [ref=e84]:
        - region "Read and file arXiv papers without tab chaos" [ref=e85]:
          - generic [ref=e86]:
            - paragraph [ref=e87]: arxiv-mcp
            - heading "Read and file arXiv papers without tab chaos" [level=1] [ref=e88]
            - generic [ref=e89]:
              - paragraph [ref=e90]:
                - text: Use this app in the browser or let a coding agent drive the same features over MCP.
                - strong [ref=e91]: Search arXiv
                - text: is live on the internet. Your
                - strong [ref=e92]: depot
                - text: "is everything you keep on this machine: downloaded paper text, search index, and bookmarks—nothing is sent to a third-party \"cloud\" by this UI."
              - paragraph [ref=e93]: "For SI work, arXiv matters because new capability and safety ideas appear there months before formal journal cycles. The goal of this app is simple: help you run a fast daily triage loop, keep the high-signal papers, and turn them into searchable notes you can reuse."
              - list [ref=e94]:
                - listitem [ref=e95]:
                  - strong [ref=e96]: Search arXiv
                  - text: — find papers online by words, subjects, or "what just appeared."
                - listitem [ref=e97]:
                  - strong [ref=e98]: Your library (depot)
                  - text: — pull papers onto disk, then read or search them without juggling browser tabs.
                - listitem [ref=e99]:
                  - strong [ref=e100]: MCP
                  - text: — Cursor, Claude, and other clients can run the same tools for you.
              - generic [ref=e101]:
                - link "Search arXiv" [ref=e102] [cursor=pointer]:
                  - /url: /search
                  - text: Search arXiv
                  - img [ref=e103]
                - link "Open your library" [ref=e105] [cursor=pointer]:
                  - /url: /depot
        - generic [ref=e106]:
          - 'heading "Start here: 5-minute daily SI sweep" [level=2] [ref=e107]'
          - list [ref=e108]:
            - listitem [ref=e109]:
              - text: Open
              - strong [ref=e110]: Search arXiv
              - text: and choose an SI starter query.
            - listitem [ref=e111]:
              - text: Run
              - strong [ref=e112]: New submissions in one subject
              - text: for a 24h or 72h window.
            - listitem [ref=e113]:
              - text: Pick 1-3 promising papers and ingest them into
              - strong [ref=e114]: Your library
              - text: .
            - listitem [ref=e115]:
              - text: Use
              - strong [ref=e116]: Search library
              - text: to compare recurring claims and methods.
            - listitem [ref=e117]: Save recurring queries as favorites so tomorrow starts in one click.
          - generic [ref=e118]:
            - link "Start sweep" [ref=e119] [cursor=pointer]:
              - /url: /search
            - link "Read SI guide" [ref=e120] [cursor=pointer]:
              - /url: /help
            - link "Agentic workflow examples" [ref=e121] [cursor=pointer]:
              - /url: /help
        - generic [ref=e122]:
          - heading "Status" [level=2] [ref=e123]
          - paragraph [ref=e124]: Backend connection and local library size.
        - generic [ref=e125]:
          - generic [ref=e126]: Connected
          - button "Refresh" [ref=e129] [cursor=pointer]:
            - img [ref=e130]
            - text: Refresh
        - generic [ref=e135]:
          - generic [ref=e136]:
            - heading "Server" [level=2] [ref=e137]:
              - img [ref=e138]
              - text: Server
            - paragraph [ref=e140]: arxiv-mcp
          - generic [ref=e141]:
            - heading "Papers in your library" [level=2] [ref=e142]
            - paragraph [ref=e143]: "5"
          - generic [ref=e144]:
            - heading "Indexed text chunks" [level=2] [ref=e145]
            - paragraph [ref=e146]: "1518"
          - generic [ref=e147]:
            - heading "Favorites" [level=2] [ref=e148]
            - paragraph [ref=e149]: "0"
        - generic [ref=e150]:
          - heading "Pages" [level=2] [ref=e151]
          - paragraph [ref=e152]: Jump to a workflow.
        - generic [ref=e153]:
          - link "Search arXiv Find papers by keywords, filter by subject, or browse new submissions in a category." [ref=e154] [cursor=pointer]:
            - /url: /search
            - generic [ref=e156]:
              - img [ref=e157]
              - generic [ref=e160]:
                - heading "Search arXiv" [level=2] [ref=e161]
                - paragraph [ref=e162]: Find papers by keywords, filter by subject, or browse new submissions in a category.
          - link "Search library Keyword search across text you already saved in your depot on this computer." [ref=e163] [cursor=pointer]:
            - /url: /semantic
            - generic [ref=e165]:
              - img [ref=e166]
              - generic [ref=e169]:
                - heading "Search library" [level=2] [ref=e170]
                - paragraph [ref=e171]: Keyword search across text you already saved in your depot on this computer.
          - 'link "Your library Download papers from arXiv into your depot: stored files plus search index." [ref=e172] [cursor=pointer]':
            - /url: /depot
            - generic [ref=e174]:
              - img [ref=e175]
              - generic [ref=e177]:
                - heading "Your library" [level=2] [ref=e178]
                - paragraph [ref=e179]: "Download papers from arXiv into your depot: stored files plus search index."
          - link "Favorites Bookmarked arXiv IDs and short notes." [ref=e180] [cursor=pointer]:
            - /url: /favorites
            - generic [ref=e182]:
              - img [ref=e183]
              - generic [ref=e185]:
                - heading "Favorites" [level=2] [ref=e186]
                - paragraph [ref=e187]: Bookmarked arXiv IDs and short notes.
  - generic [ref=e189]:
    - button "Logger (2)" [ref=e190] [cursor=pointer]:
      - img [ref=e191]
      - text: Logger (2)
    - generic [ref=e193]:
      - button "Pause" [ref=e194] [cursor=pointer]
      - button "Clear logs" [ref=e195] [cursor=pointer]:
        - img [ref=e196]
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   |
  3   | test.describe("Frontend", () => {
  4   |   test("Dashboard loads with KPIs", async ({ page }) => {
  5   |     await page.goto("/dashboard");
  6   |     await expect(page.getByTestId("dashboard")).toBeVisible();
  7   |     await expect(page.getByTestId("backend-dot")).toBeVisible();
> 8   |     await expect(page.getByText("arxiv-mcp")).toBeVisible();
      |                                               ^ Error: expect(locator).toBeVisible() failed
  9   |   });
  10  |
  11  |   test("Sidebar navigation works across all pages", async ({ page }) => {
  12  |     await page.goto("/dashboard");
  13  |     const nav = page.locator("aside nav");
  14  |     const links = [
  15  |       { name: "Search arXiv", url: /\/search/ },
  16  |       { name: "Your library", url: /\/depot/ },
  17  |       { name: "Favorites", url: /\/favorites/ },
  18  |       { name: "Tools & Prompts", url: /\/tools/ },
  19  |       { name: "Chat", url: /\/chat/ },
  20  |       { name: "Skills", url: /\/skills/ },
  21  |       { name: "Logs", url: /\/logs/ },
  22  |       { name: "Settings", url: /\/settings/ },
  23  |       { name: "Help", url: /\/help/ },
  24  |     ];
  25  |     for (const { name, url } of links) {
  26  |       await nav.getByRole("link", { name, exact: true }).click();
  27  |       await expect(page).toHaveURL(url);
  28  |     }
  29  |   });
  30  |
  31  |   test("Search page has presets and input", async ({ page }) => {
  32  |     await page.goto("/search");
  33  |     await expect(page.getByTestId("search-page")).toBeVisible();
  34  |     await expect(page.getByTestId("search-card")).toBeVisible();
  35  |     await expect(page.getByTestId("search-button")).toBeVisible();
  36  |     await expect(page.getByText("Consciousness & AI")).toBeVisible();
  37  |     await expect(page.getByText("Mechanistic interpretability")).toBeVisible();
  38  |   });
  39  |
  40  |   test("Tools page lists tools", async ({ page }) => {
  41  |     await page.goto("/tools");
  42  |     await expect(page.getByText("MCP tools & prompts")).toBeVisible();
  43  |   });
  44  |
  45  |   test("Chat page has personality selector, export, and clear", async ({ page }) => {
  46  |     await page.goto("/chat");
  47  |     await expect(page.getByTestId("chat-page")).toBeVisible();
  48  |     await expect(page.getByTestId("chat-controls")).toBeVisible();
  49  |     await expect(page.getByTestId("personality-select")).toBeVisible();
  50  |     await expect(page.getByTestId("chat-export")).toBeDisabled();
  51  |     await expect(page.getByTestId("chat-clear")).toBeDisabled();
  52  |     await expect(page.getByTestId("chat-input")).toBeVisible();
  53  |     await expect(page.getByTestId("chat-send")).toBeDisabled();
  54  |     // Check all 4 personality options exist
  55  |     const select = page.getByTestId("personality-select");
  56  |     const options = await select.locator("option").allTextContents();
  57  |     expect(options).toContain("Research Assistant");
  58  |     expect(options).toContain("Expert Reviewer");
  59  |     expect(options).toContain("Quick Summarizer");
  60  |     expect(options).toContain("Custom");
  61  |   });
  62  |
  63  |   test("Depot page has ingest and filters", async ({ page }) => {
  64  |     await page.goto("/depot");
  65  |     await expect(page.getByTestId("depot-page")).toBeVisible();
  66  |     await expect(page.getByTestId("depot-ingest")).toBeVisible();
  67  |     await expect(page.getByTestId("depot-filters-toggle")).toBeVisible();
  68  |     await expect(page.getByTestId("depot-panels")).toBeVisible();
  69  |     await expect(page.getByTestId("depot-reader")).toBeVisible();
  70  |   });
  71  |
  72  |   test("API docs page loads", async ({ page }) => {
  73  |     await page.goto("/swagger");
  74  |     await expect(page.getByRole("heading", { name: "API docs" })).toBeVisible();
  75  |   });
  76  |
  77  |   test("Skills page loads", async ({ page }) => {
  78  |     await page.goto("/skills");
  79  |     await expect(page.getByText("Bundled skills")).toBeVisible();
  80  |   });
  81  |
  82  |   test("Logs page loads", async ({ page }) => {
  83  |     await page.goto("/logs");
  84  |     await expect(page.getByText("Session logs")).toBeVisible();
  85  |   });
  86  |
  87  |   test("Settings page loads", async ({ page }) => {
  88  |     await page.goto("/settings");
  89  |     await expect(page.getByText("Configuration")).toBeVisible();
  90  |   });
  91  |
  92  |   test("Help page loads", async ({ page }) => {
  93  |     await page.goto("/help");
  94  |     await expect(page.getByText("How this web UI is laid out")).toBeVisible();
  95  |   });
  96  |
  97  |   test("Framer Motion page transitions work", async ({ page }) => {
  98  |     await page.goto("/dashboard");
  99  |     await page.getByRole("link", { name: "Chat", exact: true }).click();
  100 |     await expect(page).toHaveURL(/\/chat/);
  101 |     await expect(page.getByTestId("chat-page")).toBeVisible();
  102 |     await page.getByRole("link", { name: "Search arXiv", exact: true }).click();
  103 |     await expect(page).toHaveURL(/\/search/);
  104 |     await expect(page.getByTestId("search-page")).toBeVisible();
  105 |   });
  106 | });
  107 |
  108 | test.describe("REST API", () => {
```

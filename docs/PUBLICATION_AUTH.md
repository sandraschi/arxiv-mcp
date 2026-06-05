# Publication subscriptions (NYT, WSJ, …)

Licensed subscriber access for paywalled outlets during media traction enrichment.

## Why

You may have a valid **NYT** (or WSJ, FT) subscription, but bots are blocked or shown a login wall. Generic Jina/Bright Hand fetches do not use your subscriber session.

## Configure in `.env` (never commit)

Per publication (example NYT):

```env
ARXIV_MCP_PUB_NYT_USER=your@email.example
ARXIV_MCP_PUB_NYT_PASSWORD=your_password
ARXIV_MCP_PUB_NYT_VALID_TILL=2026-12-31
ARXIV_MCP_PUB_NYT_COOKIE=NYT-S=...; nyt-auth=...; ...
```

| Field | Required | Purpose |
|-------|----------|---------|
| `USER` | Recommended | Audit trail; future login automation |
| `PASSWORD` | Recommended | Same |
| `VALID_TILL` | **Required** if any credential set | `YYYY-MM-DD` — **must not silently fail** when sub lapses |
| `COOKIE` | Required for fetch | Subscriber session exported from browser after login |

Manifest (domains, env key names): `config/publication_subscriptions.json`

## Expiry behaviour (loud, not silent)

| Status | Behaviour |
|--------|-----------|
| `expired` | Fetch **blocked**; `subscription_error: expired`; pipeline liveness **critical** alert |
| `credentials_incomplete` | Any credential without `VALID_TILL` → error alert |
| `cookie_missing` | Valid dates but no cookie → error (won't pretend paywall read worked) |
| `expiring_soon` | Warning within 7 days (configurable) |
| `valid` | Cookie fetch attempted first for matching domains |

## Fetch order for paywalled domains

1. **Publication auth** (subscriber cookie) — if configured for that domain
2. Jina Reader — if ignore bot blocks on
3. Bright Hand — if enabled and Jina failed

Expired subscriptions **do not** fall through to anonymous fetch.

## API & UI

- `GET /api/settings/publications` — status per outlet (no secrets)
- Settings page — subscription status table
- `pipeline_liveness_tool` — includes `PUBLICATION_SUBSCRIPTION_EXPIRED` alerts
- `arxiv_help(topic="publication_auth")`

## Refreshing NYT cookie

1. Log in at nytimes.com in your browser (subscriber).
2. DevTools → Application → Cookies → copy session cookies into `ARXIV_MCP_PUB_NYT_COOKIE`.
3. Update `VALID_TILL` to your renewal date when you renew.

Password alone cannot unlock NYT HTML without a session cookie (no silent password-only scrape).

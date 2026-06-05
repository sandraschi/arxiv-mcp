# Ignore bot blocks — legal context & antipattern

## The antipattern we push back on

A growing share of the public web ships with **anti-robot guards by default**, not by choice:

- CDN “bot fight” modes (Cloudflare, etc.) enabled in one click during setup
- WordPress / Joomla security plugins that block “suspicious” User-Agents
- Hosting panels that turn on “AI scraper protection” because the checkbox was pre-ticked
- Static-site scaffolds that copy `robots.txt` templates saying `Disallow: /` for everything

The **site proprietor often does not know**. They paid for a website, not a bunker. Meanwhile:

- Google may still index them (different crawler identity)
- Humans can read the page in a browser
- **Research agents, news aggregators, and local-discovery tools get 403** — so the site is invisible in citations, fleet digests, and “what’s near Hollabrunn” answers

Classic symptom: a perfectly normal **Hollabrunn minigolf** (or bakery, vet, community club) site exists, looks fine in Chrome, but **no bot, map, or assistant ever mentions it** because every automated reader hits a challenge page. The owner wonders why “nobody finds us online” while the cause is invisible scaffolding.

We are not advocating harassment or DDoS. We advocate **not treating every public HTML page as a secret** when the publisher clearly intended it to be found.

## What arxiv-mcp does instead

| Default (off) | Ignore bot blocks (on) | + Bright Hand (if justified) |
|---------------|------------------------|------------------------------|
| HN + Google News RSS + **tech magazine RSS metadata only** | **Jina Reader** on RSS hit URLs | **Bright Data Web Unlocker** after Jina fails |
| Never fetches publisher article HTML directly | Free/cheap reader proxy | Billed unlocker — CAPTCHA / hard gates |
| Hits tagged `snippet_only: true` | `enriched_via: jina` | `enriched_via: brighthand` |

Toggles: **Settings → Ignore bot blocks** (+ optional **Bright Hand**), or env:

- `ARXIV_MCP_CODEHUNT_MEDIA_IGNORE_BOTBLOCKS=1`
- `ARXIV_MCP_CODEHUNT_MEDIA_USE_BRIGHTHAND=1`
- `BRIGHTDATA_API_TOKEN` (or `ARXIV_MCP_BRIGHTDATA_API_TOKEN`) + `ARXIV_MCP_BRIGHTDATA_ZONE`

Runtime override is stored in `data/arxiv_mcp/runtime_settings.json` (survives restarts; does not edit `.env`).

## Legal & ethical framing (not legal advice)

This section explains **why we offer the toggle**, not a jurisdiction-specific opinion. Verify with counsel for commercial redistribution.

### Public web pages

If a URL is linked from RSS, search, or social without login, the publisher has usually **published it for discovery**. Reading that page at human scale—with a declared bot identity and conservative rate limits—is different from breaking into private systems.

### robots.txt

`robots.txt` is a **voluntary convention**, not DRM. Courts and regulators have treated it as a signal to well-behaved crawlers, not a universal ban on access to public facts. Malicious ignoring of `robots.txt` plus ToS breach is a different story than **reading a linked news headline** for research traction.

### EU / Austria (operator context)

- **GDPR**: Applies to personal data. A public business address on a minigolf homepage is not the same as harvesting a private inbox.
- **Database rights / copyright**: Facts and short excerpts for indexing/citation may be fair use / quotation depending on purpose; we store **short excerpts** for match verification, not full republication.
- **eCommerce / unfair competition**: Do not misrepresent affiliation or scrape competitors’ extranets.

### When **not** to enable ignore

- Paywalls, login walls, or session-gated content
- Terms that explicitly forbid automated access **and** you lack permission
- High-volume re-scraping of the same domain
- Personal data (private social posts, leaked dumps)

### What we still do

- Honest `User-Agent` strings
- Cached RSS indexes (hours, not seconds)
- Jina Reader when you opt in
- **Bright Hand** (Bright Data) only when explicitly enabled **and** credentials exist — for hard gates Jina cannot pass; usage is billed
- No credential stuffing, no CAPTCHA farms operated by us (Bright Data handles unlocker CAPTCHA per their ToS)

## Licensed publications (NYT, WSJ, …)

Subscriber credentials live in `.env` with a mandatory **`VALID_TILL`** date. Expired subs raise **critical** alerts and block fetch — no silent anonymous fallback. See `docs/PUBLICATION_AUTH.md`.

## Related config

- `config/codehunt_media_feeds.json` — official RSS feeds (preferred path)
- `ARXIV_MCP_CODEHUNT_MEDIA_FEED_CACHE_HOURS` — RSS poll interval
- `ARXIV_MCP_JINA_READER_BASE_URL` — Jina base (default `https://r.jina.ai`)

Help: `arxiv_help(topic="botblocks")` · REST: `GET /api/help/botblocks`

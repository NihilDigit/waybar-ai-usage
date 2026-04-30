# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Waybar widgets that show usage/balance for **Claude Code, OpenAI Codex CLI, GitHub Copilot, OpenCode Zen, and Z.ai**. Each provider is one Python script that prints either a human-readable line (CLI) or a Waybar JSON blob (`--waybar`). Cron-style behavior comes from Waybar itself, not the scripts.

## Mental model

This is a **fan-in** layout, not a framework:

- N small, mostly-independent provider scripts at the repo root (`claude.py`, `codex.py`, `copilot.py`, `zen.py`, `zai.py`)
- One shared utility module (`common.py`) holding the cookie loader, file cache, output formatter, and reset-time formatter
- One fat orchestrator (`waybar_ai_usage.py`, ~900 lines) that knows about all providers and writes/restores the user's Waybar config + CSS

A provider script never imports another provider — it only depends on `common.py`. The orchestrator depends on **knowledge** of every provider (in five places — see "Adding a provider"), but not on imports of them.

## Code shape

| File | Lines | Role |
|------|-------|------|
| `common.py` | ~340 | Contract layer: `load_cookies`, `get_cached_or_fetch`, `format_eta`, `format_output`, `parse_window_*`, `open_login_url` |
| `waybar_ai_usage.py` | ~920 | Setup/cleanup/restore CLI. Reads/writes Waybar's JSON5 config and CSS, handles backups, drives the TUI module picker |
| `claude.py` / `codex.py` | ~290 each | Cookie-auth providers (claude.ai, chatgpt.com) — most code is API request + `parse_window_*` glue |
| `zen.py` | ~230 | Cookie-auth provider (opencode.ai), parses balance from rendered HTML/JS state |
| `copilot.py` | ~280 | PAT-auth via `urllib` (no `curl_cffi`); PR #13 adds Chrome-cookie HTML-scrape fallback for org-managed accounts |
| `zai.py` | ~320 | API-token-auth via `urllib`; JWT must be copied from DevTools (no browser auto-detect possible) |

`waybar_ai_usage.py` is the most complex file. It does JSON5 round-tripping, region-marker-based CSS edits, dry-run previews, and config restoration from `.bak` files. Most maintenance work touches the providers and `common.py`; `waybar_ai_usage.py` only changes when adding/removing a provider or tweaking the setup UX.

## The provider contract

Every provider script must:

1. Define a config object (cookies dict or `~/.config/waybar-ai-usage/<name>.conf`)
2. Have an `argparse` `main()` that supports `--waybar` and `--config <path>` (and `--browser` for cookie-auth ones)
3. Wrap its fetch in `get_cached_or_fetch("<name>", fetch_fn, ttl=...)` from `common.py`
4. Format output with `common.format_output(format_string, data)` so the user's `--format` flag works
5. Classify errors as **Auth Err** (HTTP 401/403/404, cookie load failures) or **Net Err** (timeouts, DNS, anything else)
6. In `--waybar` mode, **always `sys.exit(0)`** even on error — non-zero exit hides the widget entirely
7. On HTTP auth errors, call `open_login_url()` from `common.py` (no-op outside `--waybar`, has 10-min cooldown via marker file)

Reuse from `common.py` rather than rolling your own — `format_eta` accepts `str | int | None` (ISO 8601 string, Unix timestamp seconds, or null), so you should not pre-convert timestamps.

## Three auth strategies

The choice depends on what the upstream service exposes. In rough order of preference:

| Strategy | Used by | Picked when |
|---|---|---|
| **Browser cookie auto-detect** | `claude.py`, `codex.py`, `zen.py` | Cookies persist on disk and the API accepts them. Multi-browser fallback via `DEFAULT_BROWSERS` order in `common.py` |
| **Static API token in config file** | `copilot.py` (PAT), `zai.py` (JWT) | When auth is short-lived/JS-generated and not in cookies, OR when the user must explicitly grant a scoped token |
| **HTML scrape with cookies** | `copilot.py` org-managed fallback (PR #13) | Last resort when the API doesn't expose the data but the settings page does |

`curl_cffi` with `impersonate="chrome"` is required for any cookie-authenticated call to providers behind Cloudflare (claude.ai, chatgpt.com, opencode.ai, github.com settings page). Stdlib `urllib` is fine for plain API calls (Copilot billing, Z.ai).

## Cross-cutting concerns

**Caching** (`common.get_cached_or_fetch`)
- File-based: `~/.cache/waybar-ai-usage/<name>.json` with TTL (default 60s, Z.ai uses 120s)
- Multi-Waybar coordination via `.updating` marker files. Multiple monitors → multiple Waybar instances → concurrent fetches; the marker makes one win and the others wait up to 3s for the cache to land
- Fragile state to be aware of: corrupted cache files are silently treated as miss

**Error UX**
- Two buckets: `Auth Err` and `Net Err`. Auth errors trigger `xdg-open` to the provider's login page (cooldown marker at `~/.cache/waybar-ai-usage/<name>.login_opened`)
- Tooltip carries the full error message; the bar text is short (`Auth Err` / `Net Err` / icon + percentage)

**Retry**
- Cookie-auth providers (`claude.py`, `codex.py`, `zen.py`) retry once on failure (2 attempts, 10s timeout each)
- Token-auth providers (`copilot.py`, `zai.py`) do not retry. Single 10s timeout
- If you add retry to a token provider, keep total wall time < Waybar's poll interval

**Output modes**
- CLI: human-readable, exit code reflects success
- `--waybar`: JSON `{"text", "tooltip", "class", "percentage"}`, **always exit 0**
- The format DSL is `{placeholder}` with optional `{?var}...{/var}` conditionals, processed by `common.format_output`. Full reference: [docs/formatting.md](docs/formatting.md)
- **Quirk**: the conditional `{?var}...{/var}` only treats values as "not set" when they're empty or the literal string `"Not started"` (Claude/Codex sentinel). Other providers' missing-data sentinels (e.g. Z.ai's `"??"`) won't trigger conditionals — work around by emitting an empty string when missing

## Fragility map

When this project breaks, it's almost always one of these:

| Trigger | Affected | Symptom | Fix pattern |
|---|---|---|---|
| Cloudflare anti-bot tightens | claude/codex/zen | All requests 403 | Bump `curl_cffi` |
| Provider renames an API field | any | Widget shows weird number or `Net Err` | Update field path in provider |
| GitHub redesigns settings page | copilot org-fallback | Regex misses, "no copilot usage section" | Update HTML regex in `copilot.py` |
| User has multiple browsers, wrong one picked first | cookie-auth | `Missing 'lastActiveOrg'` etc. | User passes `--browser <name>` (see issue #12) |
| Firefox uses `~/.config/mozilla/firefox` (XDG) | cookie-auth on newer distros | Firefox cookies not found | `_firefox_xdg_fallback` in `common.py` (issue #9) |
| Z.ai JWT expires | `zai.py` | `Auth Err` after working for a while | User re-grabs token from DevTools (no auto-refresh possible) |

## Adding a provider

A new `<name>.py` requires touch-ups in **five places** in `waybar_ai_usage.py` (and one in `pyproject.toml`). Missing any of them silently breaks setup or cleanup. The list as of v0.7.0:

1. `pyproject.toml`: add to `[project.scripts]` and `[tool.hatch.build.targets.wheel].packages`
2. `waybar_ai_usage.py:MODULES` list — drives the setup TUI (key, name, desc, default config filename)
3. `TEMPLATE_CONFIG` and `TEMPLATE_STYLE` blocks in the same file — written to the user's Waybar config/CSS during setup
4. `_remove_style_blocks` selector tuple — for `untoggle` / cleanup to strip CSS
5. `_remove_config` — both the `modules-left` filter tuple and the per-key `pop` block
6. `_resolve_exec_base.binaries` tuple — used to detect whether the user installed via AUR or `uv tool install`

Also update `waybar-config-example.jsonc` and `waybar-style-example.css` for users who copy templates manually.

## Development

```bash
uv run python claude.py              # CLI mode
uv run python claude.py --waybar     # Waybar JSON mode
uv run python waybar_ai_usage.py setup --dry-run  # Preview setup changes
```

Python 3.11+ (uses `X | Y` union syntax). Zero global installs — always use `uv run`. No tests, no linter configured; correctness is verified by hand-running each provider against a real account.

## Release & distribution

- `uv build` produces a wheel, but distribution is via **AUR**, not PyPI
- `./release.sh <X.Y.Z>` automates: bump `pyproject.toml` + `PKGBUILD` → commit → tag → push to `origin main` + `--tags` → wait 5s for GitHub → recompute SHA256 from the GitHub tarball → regenerate `.SRCINFO` → push to AUR over SSH
- Has interactive `read -p` prompts; in non-interactive contexts pipe `y` to stdin
- The script does **not** create a GitHub Release — that's a separate `gh release create vX.Y.Z` step done only for minor/major bumps. Patch releases get the AUR push but no GH release page
- Common footgun: if AUR SSH fails mid-script, the GitHub side is already published; re-run only the AUR portion manually rather than re-running the whole script

External contributors land most new providers (PR #5 Zen, PR #11 Z.ai, PR #13 Copilot fallback). The code review pattern that recurs: collapsing redundant null-checks, removing manual `datetime` arithmetic in favor of `format_eta`, wiring up unused helpers.

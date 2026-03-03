# waybar-ai-usage

Waybar widgets showing usage/balance for Claude Code, OpenAI Codex CLI, GitHub Copilot, and OpenCode Zen.

## Architecture

Flat single-module layout — no `src/` directory. Each service is one Python file:

| File | Entry point | Service | Auth method |
|------|-------------|---------|-------------|
| `claude.py` | `claude-usage` | Claude Code (claude.ai) | Browser cookies via `browser_cookie3` + `curl_cffi` |
| `codex.py` | `codex-usage` | Codex CLI (chatgpt.com) | Browser cookies via `browser_cookie3` + `curl_cffi` |
| `copilot.py` | `copilot-usage` | GitHub Copilot billing | Fine-grained PAT in `~/.config/waybar-ai-usage/copilot.conf` |
| `zen.py` | `zen-balance` | OpenCode Zen (opencode.ai) | Browser cookies via `browser_cookie3` + `curl_cffi` |
| `common.py` | — | Shared utilities | — |
| `waybar_ai_usage.py` | `waybar-ai-usage` | Setup/cleanup CLI | — |

## Key patterns

- **Dual output**: Every module supports `--waybar` (JSON for Waybar) and plain CLI (human-readable).
- **File-based caching**: `~/.cache/waybar-ai-usage/<name>.json` with TTL (default 60s). Prevents duplicate requests when multiple Waybar instances exist (multi-monitor).
- **Error classification**: Errors are bucketed as `Auth Err` (HTTP 401/403/404, cookie failures) or `Net Err` (timeouts, DNS). Only HTTP auth errors trigger `xdg-open` to the login page, with a 10-minute cooldown marker.
- **No external deps beyond `pyproject.toml`**: Only `browser_cookie3`, `curl_cffi`, and `json-five`. Copilot module uses only stdlib (`urllib`).

## Development

```bash
uv run python claude.py              # CLI mode
uv run python claude.py --waybar     # Waybar JSON mode
uv run python waybar_ai_usage.py setup --dry-run  # Preview setup changes
```

## Build & release

- `uv build` to create wheel
- `./release.sh <version>` automates: version bump → commit → tag → push → AUR update
- AUR package at `aur/waybar-ai-usage/PKGBUILD`; system install goes to `/usr/bin/` and `/usr/lib/python3.*/site-packages/`

## Conventions

- Python 3.11+ (uses `X | Y` union syntax, `match` not used yet)
- Zero global installs — use `uv run` for development
- `curl_cffi` with `impersonate="chrome"` for cookie-authenticated modules (bypasses Cloudflare)
- Waybar JSON output: `{"text": "...", "tooltip": "...", "class": "...", "percentage": N}`
- Error output in `--waybar` mode always `sys.exit(0)` (non-zero hides the widget)
- Format strings use `{placeholder}` with optional conditionals `{?var}...{/var}`

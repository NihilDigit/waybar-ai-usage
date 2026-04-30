# Waybar AI Usage

[![Mentioned in Awesome Codex CLI](https://awesome.re/mentioned-badge.svg)](https://github.com/RoggeOhta/awesome-codex-cli)

Monitor **Claude Code**, **OpenAI Codex CLI**, **GitHub Copilot**, **OpenCode Zen**, and **Z.ai** usage directly in your Waybar status bar.

![showcase](https://github.com/user-attachments/assets/13e8a4a1-6778-484f-8a37-cba238aefea5)

This tool displays your AI coding assistant usage limits in real-time by reading browser cookies or API tokens. No API key needed for Claude, Codex, or OpenCode Zen — they use the browser session you're already signed into.

## Contents

- [What This Monitors](#what-this-monitors)
- [Requirements](#requirements)
- [Installation](#installation)
- [Setup](#setup) — Claude, Codex, Copilot, Zen, Z.ai
- [Usage](#usage)
- [Formatting Configuration](#formatting-configuration) — see also [docs/formatting.md](docs/formatting.md)
- [Display States](#display-states)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing) — see also [CLAUDE.md](CLAUDE.md)

## What This Monitors

- **Claude Code**: Claude's AI-powered code editor
  - 5-hour usage window
  - 7-day usage window
- **OpenAI Codex CLI**: OpenAI's command-line coding assistant
  - Primary (5-hour) window
  - Secondary (7-day) window
- **GitHub Copilot**: Monthly premium request quota (Pro/Pro+)
  - Requests consumed vs. included quota (default: 300)
  - Countdown to monthly reset (1st of month, 00:00 UTC)
- **OpenCode Zen**: Pay-as-you-go balance for curated coding models
  - Current account balance in USD
  - Color-coded warnings when balance is low
  - No API key needed - uses browser cookies
- **Z.ai**: Usage quota monitoring (GLM models)
  - 5-hour token usage window (percentage + reset timer)
  - Monthly tool quota (web search, web reader, ZRead)
  - Uses API token from config file

## Requirements

- **Linux** with **Waybar** running
- A signed-in browser session for whichever cookie-based providers you monitor — [Claude.ai](https://claude.ai), [ChatGPT](https://chatgpt.com), [OpenCode](https://opencode.ai). See [Setup](#setup) for the supported browser list.
- **GitHub fine-grained PAT** — required for Copilot (see [Setup](#setup))
- **Z.ai API token** — required for Z.ai (see [Setup](#setup))
- **Python 3.11+** and **uv** ([install uv](https://docs.astral.sh/uv/getting-started/installation/))

## Installation

### Method 0: AUR (Recommended on Arch)

```bash
yay -S waybar-ai-usage
```

### Method 1: Using uv tool

```bash
# Install from GitHub
uv tool install git+https://github.com/NihilDigit/waybar-ai-usage

# Or install locally for development
git clone https://github.com/NihilDigit/waybar-ai-usage
cd waybar-ai-usage
uv build
uv tool install --force dist/waybar_ai_usage-*-py3-none-any.whl
```

### Method 2: Development Mode

```bash
git clone https://github.com/NihilDigit/waybar-ai-usage
cd waybar-ai-usage
uv sync
```

## Setup

Each provider authenticates differently. Expand the ones you need.

<details>
<summary><b>Claude &amp; Codex</b> — browser cookies, automatic if you're already signed in</summary>

Claude and Codex pick up your existing browser session — no config file needed. As long as you're signed into [claude.ai](https://claude.ai) and [chatgpt.com](https://chatgpt.com) in a supported browser, just run:

```bash
claude-usage
codex-usage
```

Default browser probe order: `chrome` → `chromium` → `brave` → `edge` → `firefox` → `helium`. Override with `--browser <name>` (repeatable) if you need a specific browser. See [Troubleshooting](#troubleshooting) if cookies aren't picked up.

</details>

<details>
<summary><b>GitHub Copilot</b> — fine-grained PAT in a config file</summary>

Copilot uses a **GitHub Personal Access Token** instead of browser cookies.

**1. Create a fine-grained PAT**

1. Go to **GitHub → Settings → Developer Settings → Personal access tokens → Fine-grained tokens**
2. Click **"Generate new token"**
3. Set a name (e.g. `waybar-copilot`) and expiration
4. Under **User permissions** → find **Plan** → set to **Read-only**
5. Click **"Generate token"** and copy the value

> **Note**: The **"Copilot"** permission scope is *not* the right one — you need **"Plan"**.
>
> This endpoint only works if your Copilot license is billed directly to your personal account (Copilot Pro/Pro+). If your license is managed by an organization, the data won't appear here.

**2. Create the config file**

```bash
mkdir -p ~/.config/waybar-ai-usage
```

Create `~/.config/waybar-ai-usage/copilot.conf`:

```ini
# GitHub Personal Access Token
# Required permission: User permissions → Plan → Read-only
# Create at: https://github.com/settings/personal-access-tokens
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Monthly included premium request quota
# Copilot Pro = 300, Copilot Pro+ = 1500
COPILOT_QUOTA=300
```

**3. Test it**

```bash
copilot-usage          # Shows used/quota in terminal
copilot-usage --waybar # Shows Waybar JSON
```

</details>

<details>
<summary><b>OpenCode Zen</b> — browser cookies, automatic if you're already signed in</summary>

Zen shows your pay-as-you-go balance and uses browser cookies just like Claude and Codex. Make sure you're logged into [opencode.ai](https://opencode.ai) in a supported browser, then:

```bash
zen-balance          # Shows balance in terminal
zen-balance --waybar # Shows Waybar JSON
```

No config file needed.

</details>

<details>
<summary><b>Z.ai</b> — API token in a config file</summary>

Z.ai uses an API token captured from your browser session.

**1. Get your API token**

1. Go to [z.ai](https://z.ai) and log in
2. Open DevTools (**F12**) > **Network** tab
3. Find any request to `api.z.ai` and copy the `Authorization` header value (e.g. `Bearer eyJ...`)
4. You only need the token part after `Bearer `

**2. Create the config file**

```bash
mkdir -p ~/.config/waybar-ai-usage
```

Create `~/.config/waybar-ai-usage/zai.conf`:

```ini
# Z.ai API token from browser DevTools
ZAI_TOKEN=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...
```

**3. Test it**

```bash
zai-usage          # Shows usage in terminal
zai-usage --waybar # Shows Waybar JSON
```

> **Note**: The Z.ai JWT can expire after a while. If you start seeing `Auth Err` later, repeat step 1 to grab a fresh token.

</details>

## Usage

### Command Line

After `uv tool install`:
```bash
# Setup helper (adds modules/styles with backups + confirmation)
waybar-ai-usage setup

# Cleanup helper (removes modules/styles with backups + confirmation)
waybar-ai-usage cleanup

# Restore latest backups (or pass specific backup paths)
waybar-ai-usage restore

# Preview changes without writing
waybar-ai-usage setup --dry-run
waybar-ai-usage cleanup --dry-run
waybar-ai-usage restore --dry-run

# Skip confirmation
waybar-ai-usage setup --yes
waybar-ai-usage cleanup --yes

# Claude usage
claude-usage

# ChatGPT usage
codex-usage

# GitHub Copilot usage
copilot-usage
copilot-usage --config ~/.config/waybar-ai-usage/copilot.conf  # custom config path

# OpenCode Zen balance
zen-balance

# Z.ai usage quota
zai-usage
zai-usage --config ~/.config/waybar-ai-usage/zai.conf  # custom config path

# Waybar JSON output
claude-usage --waybar
codex-usage --waybar
copilot-usage --waybar
zen-balance --waybar
zai-usage --waybar

# Use a specific browser (repeatable, tried in order)
claude-usage --browser chromium --browser brave
codex-usage --browser chromium
```

> Note: `setup`/`cleanup` will rewrite your Waybar config JSONC and may change formatting or remove comments. Backups are created before any write.

In development mode:
```bash
uv run python claude.py
uv run python codex.py
```

### Waybar Integration

#### Step 1: Install the tool

```bash
uv tool install waybar-ai-usage
```

After installation, the commands `claude-usage`, `codex-usage`, `copilot-usage`, `zen-balance`, and `zai-usage` will be available in your PATH (along with `waybar-ai-usage` for setup/cleanup).

#### Step 2: Run setup

```bash
waybar-ai-usage setup
```

This will add the required Waybar modules and styles (with backup + confirmation).
Copilot module is only added if `~/.config/waybar-ai-usage/copilot.conf` exists (see [Setup](#setup)).
If you want to force a specific browser order in Waybar, pass it here:
```bash
waybar-ai-usage setup --browser chromium --browser brave
```

#### Step 3: Restart Waybar

```bash
pkill waybar && waybar &
```

**Important Notes**:

- **Use full path `~/.local/bin/`** to ensure modules work when Waybar is
  launched by systemd (auto-start on login). Without the full path, modules will
  only work when Waybar is manually started from a terminal.

## Formatting Configuration

The default output works without any configuration. To customize what each widget shows — variables, conditional blocks, custom layouts — see [docs/formatting.md](docs/formatting.md).

## Display States

Color thresholds are defined in `waybar-style-example.css` and applied via Waybar CSS classes — edit the stylesheet to taste. The shipped defaults:

- **Green** — low usage (`<50%` for Claude/Codex/Copilot/Z.ai; healthy balance for Zen)
- **Yellow** — moderate usage (`50–79%`; low balance for Zen)
- **Red** — high usage (`≥80%`; near-empty balance for Zen)
- **Critical** (red, with bg tint) — fetch failed (auth or network error)

Special bar text states (Claude, Codex, Z.ai only):

- **Ready** — window hasn't been activated yet (0% used, full reset window remaining)
- **Pause** — quota exhausted (100% used). For Claude/Codex this means the long window (7-day / Secondary) is fully consumed

## Troubleshooting

### "Cookie read failed" Error

Make sure you're logged into Claude/ChatGPT in your chosen browser:

```bash
# Test Claude cookies
python -c "import browser_cookie3; print(list(browser_cookie3.chromium(domain_name='claude.ai')))"

# Test ChatGPT cookies
python -c "import browser_cookie3; print(list(browser_cookie3.chromium(domain_name='chatgpt.com')))"
```

### "403 Forbidden" or "Net Err"

1. Refresh the Claude/ChatGPT/OpenCode page in your browser
2. Check if your IP is blocked by Cloudflare
3. Update dependencies: `uv sync --upgrade`
4. Cookie-based providers (Claude, Codex, Zen) retry once on failure (10s timeout each); Copilot and Z.ai do not retry

### Wrong browser picked / `Missing 'lastActiveOrg'`

If you have multiple browsers installed, the tool may pick one you're not actually signed into and then return errors like `Missing 'lastActiveOrg' in cookies` or `Auth Err`. Force a specific browser with `--browser` (repeatable, tried in order):

```bash
claude-usage --browser chromium --browser brave
codex-usage --browser helium
```

For Waybar, append `--browser <name>` to the `exec` line in your config, or pass it to `waybar-ai-usage setup` so it's baked in:

```bash
waybar-ai-usage setup --browser chromium
```

Default probe order if `--browser` is not given: `chrome`, `chromium`, `brave`, `edge`, `firefox`, `helium`.

## Contributing

Contributions welcome — especially new providers. See [CLAUDE.md](CLAUDE.md) for the architecture overview, the provider contract, and the touch-points required when adding a provider.

## License

MIT - See [LICENSE](LICENSE) file for details.

## Acknowledgments

- Uses [browser_cookie3](https://github.com/borisbabic/browser_cookie3) for
  cookie extraction
- Uses [curl_cffi](https://github.com/yifeikong/curl_cffi) for making
  authenticated requests

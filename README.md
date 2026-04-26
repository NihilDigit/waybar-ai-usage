# Waybar AI Usage

[![Mentioned in Awesome Codex CLI](https://awesome.re/mentioned-badge.svg)](https://github.com/RoggeOhta/awesome-codex-cli)

Monitor **Claude Code**, **OpenAI Codex CLI**, **GitHub Copilot**, **OpenCode Zen**, and **Z.ai** usage directly in your Waybar status bar.

![showcase](https://github.com/user-attachments/assets/13e8a4a1-6778-484f-8a37-cba238aefea5)

This tool displays your AI coding assistant usage limits in real-time by reading browser cookies (Chrome by default) or API tokens. No API keys needed for Claude and Codex!

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

## Features

- 🎨 Real-time usage percentage display
- ⏰ Countdown timer until quota reset
- 🚦 Color-coded warnings (green → yellow → red)
- 🔄 Click to refresh instantly
- 🍪 Uses browser cookies (Chrome by default, configurable) - no API key needed
- 🎯 Special states: "Ready" (unused) and "Pause" (quota exhausted)
- 🔁 Auto-retry on network errors

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

## GitHub Copilot Setup

Unlike Claude and Codex, Copilot uses a **GitHub Personal Access Token** instead of browser cookies.

### 1. Create a Fine-Grained PAT

1. Go to **GitHub → Settings → Developer Settings → Personal access tokens → Fine-grained tokens**
2. Click **"Generate new token"**
3. Set a name (e.g. `waybar-copilot`) and expiration
4. Under **User permissions** → find **Plan** → set to **Read-only**
5. Click **"Generate token"** and copy the value

> **Note**: The **"Copilot"** permission scope is *not* the right one — you need **"Plan"**.
>
> This endpoint only works if your Copilot license is billed directly to your personal account (Copilot Pro/Pro+). If your license is managed by an organization, the data won't appear here.

### 2. Create the Config File

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

### 3. Test It

```bash
copilot-usage          # Shows used/quota in terminal
copilot-usage --waybar # Shows Waybar JSON
```

## OpenCode Zen Setup

Unlike Claude and Codex which have usage windows, **Zen** shows your current pay-as-you-go balance.

### 1. Login to OpenCode

Make sure you're logged into [opencode.ai](https://opencode.ai) in your Chrome/Chromium browser.

### 2. Test It

```bash
zen-balance          # Shows balance in terminal
zen-balance --waybar # Shows Waybar JSON
```

No configuration needed - it uses browser cookies just like Claude and Codex!

## Z.ai Setup

Unlike Claude and Codex which use browser cookies, **Z.ai** uses an API token for authentication.

### 1. Get Your API Token

1. Go to [z.ai](https://z.ai) and log in
2. Open DevTools (**F12**) > **Network** tab
3. Find any request to `api.z.ai` and copy the `Authorization` header value (e.g. `Bearer eyJ...`)
4. You only need the token part after `Bearer `

### 2. Create the Config File

```bash
mkdir -p ~/.config/waybar-ai-usage
```

Create `~/.config/waybar-ai-usage/zai.conf`:

```ini
# Z.ai API token from browser DevTools
ZAI_TOKEN=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Test It

```bash
zai-usage          # Shows usage in terminal
zai-usage --waybar # Shows Waybar JSON
```

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

After installation, the commands `claude-usage`, `codex-usage`, and `copilot-usage` will be available in your PATH.

#### Step 2: Run setup

```bash
waybar-ai-usage setup
```

This will add the required Waybar modules and styles (with backup + confirmation).
Copilot module is only added if `~/.config/waybar-ai-usage/copilot.conf` exists (see [GitHub Copilot Setup](#github-copilot-setup)).
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

You can customize the output format using the `--format` and `--tooltip-format`
options. This allows you to:

- Show specific data points (5-hour or 7-day)
- Remove or customize icons
- Create your own layout

### Available Variables

All variables are available for both `--format` and `--tooltip-format`:

| Variable            | Description                     | Example                               |
| ------------------- | ------------------------------- | ------------------------------------- |
| `{icon}`            | Service icon with color styling | `<span foreground='#DE7356'>󰜡</span>` |
| `{icon_plain}`      | Service icon without styling    | `󰜡` (Claude) or `󰬫` (Codex)           |
| `{time_icon}`       | Time icon with color styling    | `<span foreground='#DE7356'>󰔚</span>` |
| `{time_icon_plain}` | Time icon without styling       | `󰔚`                                   |
| `{5h_pct}`          | 5-hour window percentage        | `45`                                  |
| `{7d_pct}`          | 7-day window percentage         | `67`                                  |
| `{5h_reset}`        | 5-hour reset time               | `4h23m`                               |
| `{7d_reset}`        | 7-day reset time                | `2d15h`                               |
| `{pct}`             | Active window percentage        | Varies based on active window         |
| `{reset}`           | Active window reset time        | Varies based on active window         |
| `{status}`          | Status text                     | `Ready`, `Pause`, or empty            |
| `{win}`             | Active window name              | `5h` or `7d`                          |

### Format Examples

```bash
# Show only 5-hour data without styled icons
claude-usage --waybar --format "{icon_plain} {5h_pct}% {time_icon_plain} {5h_reset}"

# Show both 5-hour and 7-day percentages
claude-usage --waybar --format "{icon} 5h:{5h_pct}% 7d:{7d_pct}%"

# Minimal format with just percentage
codex-usage --waybar --format "{5h_pct}%"

# Custom tooltip showing both windows
claude-usage --waybar --tooltip-format "5-Hour: {5h_pct}%  Reset: {5h_reset}\n7-Day: {7d_pct}%  Reset: {7d_reset}"

# Always show 5-hour window (disable auto-switch to 7-day)
claude-usage --waybar --show-5h
```

### Waybar Configuration Example

Pass formatting directly to the script using `--format` (useful for styled icons with colors):

```jsonc
"custom/claude-usage": {
    "exec": "~/.local/bin/claude-usage --waybar --format '{icon} {5h_pct}% {time_icon} {5h_reset}'",
    "return-type": "json",
    "interval": 120,
    "on-click": "~/.local/bin/claude-usage --waybar --format '{icon} {5h_pct}% {time_icon} {5h_reset}'"
}
```

When using `--format`, `{icon}` includes HTML color styling.

Without `--format`, the script provides a default formatted text:

```jsonc
"custom/claude-usage": {
    "exec": "~/.local/bin/claude-usage --waybar",
    "return-type": "json",
    "interval": 120
}
```

This displays: `󰜡 98% 󰔚 2d21h` (with colored icons)

**Note**: When using `%` in shell commands, you may need to escape it as `%%`
depending on your shell.

### Conditional Formatting

You can use conditional blocks to show or hide sections based on whether a time
window has started:

**Single variable conditions:**

- `{?5h_reset}...{/5h_reset}` - Show content only if 5h window has started
- `{?7d_reset}...{/7d_reset}` - Show content only if 7d window has started

**Multiple variable conditions:**

- `{?5h_reset&7d_reset}...{/}` - Show content only if both windows have started

#### Conditional Examples

```bash
# Show both windows only if they've started, with separator only when both present
claude-usage --waybar --format '{?5h_reset}{5h_pct}/{5h_reset}{/5h_reset}{?5h_reset&7d_reset} - {/}{?7d_reset}{7d_pct}/{7d_reset}{/7d_reset}'

# Show 5h data only when active, otherwise show nothing
codex-usage --waybar --format '{?5h_reset}{icon} {5h_pct}% {time_icon} {5h_reset}{/5h_reset}'
```

The first example will display:

- Nothing when both windows are "Not started"
- `45/4h23m` when only 5h window is active
- `67/2d15h` when only 7d window is active
- `45/4h23m - 67/2d15h` when both windows are active

## Display States

### Normal States

- **Green** (0-49%): Low usage, plenty of quota remaining
- **Yellow** (50-79%): Moderate usage, consider managing requests
- **Red** (80-99%): High usage, approaching limit

### Special States

- **Ready** (󰬫/󰜡): Window hasn't been activated yet (0% usage, ~5h remaining)
- **Pause** (󰬫/󰜡): Weekly quota exhausted (100% usage)

## Requirements

- **Chrome browser** (default) or another supported browser with active login
  to:
  - [Claude.ai](https://claude.ai) for Claude Code monitoring
  - [ChatGPT](https://chatgpt.com) for Codex CLI monitoring
  - [OpenCode](https://opencode.ai) for Zen balance monitoring
- **Z.ai account** with API token for Z.ai usage monitoring (see [Z.ai Setup](#zai-setup))
- **Python 3.11+**
- **uv** package manager
  ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

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

1. Refresh the Claude/ChatGPT page in your Chrome browser
2. Check if your IP is blocked by Cloudflare
3. Update dependencies: `uv sync --upgrade`
4. The tool has built-in retry (1 retry with 10s timeout)

### Using Other Browsers

You can select browsers in order using `--browser` (repeatable). Without it, the default order is: `chrome`, `chromium`, `brave`, `edge`, `firefox`, `helium`.

```bash
claude-usage --browser chromium --browser brave
codex-usage --browser helium
```

## Project Structure

```
waybar-ai-usage/
├── assets/
│   ├── claude.svg                # Claude logo (unused in current version)
│   └── codex.svg                 # ChatGPT/OpenAI logo (unused in current version)
├── common.py                     # Shared utilities (time formatting, window parsing)
├── claude.py                     # Claude Code usage monitor
├── codex.py                      # OpenAI Codex CLI usage monitor
├── copilot.py                    # GitHub Copilot premium request monitor
├── zen.py                        # OpenCode Zen balance monitor
├── zai.py                        # Z.ai usage quota monitor
├── pyproject.toml                # Project metadata and dependencies
├── waybar-config-example.jsonc   # Template used by setup
├── waybar-style-example.css      # Template used by setup
├── LICENSE                       # MIT License
└── README.md                     # This file
```

## How It Works

1. **Cookie Extraction**: Uses `browser_cookie3` to read authentication cookies from your chosen browser (Claude/Codex)
2. **Token Auth**: GitHub Copilot uses a Personal Access Token stored in a local config file
3. **API Requests**: Makes authenticated requests to Claude.ai, ChatGPT, and GitHub APIs
4. **Usage Parsing**: Extracts usage percentages and reset times from API responses
4. **Waybar Output**: Formats data as JSON for Waybar's custom module
5. **Auto-refresh**: Waybar polls every 2 minutes (configurable via `interval`)

### Network Configuration

- **Timeout**: 10 seconds per request
- **Retry**: 1 automatic retry on failure (total 2 attempts)
- **Refresh interval**: 120 seconds (2 minutes) recommended

## Contributing

Contributions are welcome! Areas for improvement:

- [x] Support for Firefox, Brave, Chromium browsers
- [x] Better UX for setup/cleanup (preview changes, restore helper)
- [x] Caching mechanism to reduce API calls (v0.4.0+)
- [x] GitHub Copilot premium request monitoring (v0.5.0+)
- [x] OpenCode Zen balance monitoring
- [ ] Better error messages
- [ ] More examples and screenshots

### For Maintainers

See [RELEASING.md](RELEASING.md) for release process documentation.

Quick release:
```bash
./release.sh 0.5.0
```

## License

MIT - See [LICENSE](LICENSE) file for details.

## Acknowledgments

- Uses [browser_cookie3](https://github.com/borisbabic/browser_cookie3) for
  cookie extraction
- Uses [curl_cffi](https://github.com/yifeikong/curl_cffi) for making
  authenticated requests

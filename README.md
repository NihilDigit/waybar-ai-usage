# Waybar AI Usage

Monitor **Claude Code** and **OpenAI Codex CLI** usage directly in your Waybar status bar.

This tool displays your AI coding assistant usage limits in real-time by reading browser cookies (Chrome by default). No API keys needed!

## What This Monitors

- **Claude Code**: Claude's AI-powered code editor
  - 5-hour usage window
  - 7-day usage window
- **OpenAI Codex CLI**: OpenAI's command-line coding assistant
  - Primary (5-hour) window
  - Secondary (7-day) window

## Features

- 🎨 Real-time usage percentage display
- ⏰ Countdown timer until quota reset
- 🚦 Color-coded warnings (green → yellow → red)
- 🔄 Click to refresh instantly
- 🍪 Uses browser cookies (Chrome by default, configurable) - no API key needed
- 🎯 Special states: "Ready" (unused) and "Pause" (quota exhausted)
- 🔁 Auto-retry on network errors

## Installation

### Method 1: Using uv tool (Recommended)

```bash
# Install from GitHub
uv tool install git+https://github.com/NihilDigit/waybar-ai-usage

# Or install locally for development
git clone https://github.com/NihilDigit/waybar-ai-usage
cd waybar-ai-usage
uv build
uv tool install --force dist/waybar_ai_usage-0.1.5-py3-none-any.whl
```

### Method 2: Development Mode

```bash
git clone https://github.com/NihilDigit/waybar-ai-usage
cd waybar-ai-usage
uv sync
```

## Usage

### Command Line

After `uv tool install`:
```bash
# Setup helper (adds modules/styles with backups + confirmation)
waybar-ai-usage setup

# Cleanup helper (removes modules/styles with backups + confirmation)
waybar-ai-usage cleanup

# Preview changes without writing
waybar-ai-usage setup --dry-run
waybar-ai-usage cleanup --dry-run

# Skip confirmation
waybar-ai-usage setup --yes
waybar-ai-usage cleanup --yes

> Note: `setup`/`cleanup` will rewrite your Waybar config JSONC and may change formatting or remove comments. Backups are created before any write.

# Claude usage
claude-usage

# ChatGPT usage
codex-usage

# Waybar JSON output
claude-usage --waybar
codex-usage --waybar

# Use a specific browser (repeatable, tried in order)
claude-usage --browser chromium --browser brave
codex-usage --browser chromium
```

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

After installation, the commands `claude-usage` and `codex-usage` will be available in your PATH.

#### Step 2: Run setup

```bash
waybar-ai-usage setup
```

This will add the required Waybar modules and styles (with backup + confirmation).

#### Step 3: Restart Waybar

```bash
pkill waybar && waybar &
```

**Important Notes**:
- **Use full path `~/.local/bin/`** to ensure modules work when Waybar is launched by systemd (auto-start on login). Without the full path, modules will only work when Waybar is manually started from a terminal.

## Display States

### Normal States
- **Green** (0-49%): Low usage, plenty of quota remaining
- **Yellow** (50-79%): Moderate usage, consider managing requests
- **Red** (80-99%): High usage, approaching limit

### Special States
- **Ready** (󰬫/󰜡): Window hasn't been activated yet (0% usage, ~5h remaining)
- **Pause** (󰬫/󰜡): Weekly quota exhausted (100% usage)

## Requirements

- **Chrome browser** (default) or another supported browser with active login to:
  - [Claude.ai](https://claude.ai) for Claude Code monitoring
  - [ChatGPT](https://chatgpt.com) for Codex CLI monitoring
- **Python 3.11+**
- **uv** package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

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

You can select browsers in order using `--browser` (repeatable). Without it, the default order is: `chrome`, `chromium`, `brave`, `edge`, `firefox`.

```bash
claude-usage --browser chromium --browser brave
codex-usage --browser chromium
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
├── pyproject.toml                # Project metadata and dependencies
├── waybar-config-example.jsonc   # Template used by setup
├── waybar-style-example.css      # Template used by setup
├── LICENSE                       # MIT License
└── README.md                     # This file
```

## How It Works

1. **Cookie Extraction**: Uses `browser_cookie3` to read authentication cookies from your chosen browser
2. **API Requests**: Makes authenticated requests to Claude.ai and ChatGPT APIs using `curl_cffi`
3. **Usage Parsing**: Extracts usage percentages and reset times from API responses
4. **Waybar Output**: Formats data as JSON for Waybar's custom module
5. **Auto-refresh**: Waybar polls every 2 minutes (configurable via `interval`)

### Network Configuration

- **Timeout**: 10 seconds per request
- **Retry**: 1 automatic retry on failure (total 2 attempts)
- **Refresh interval**: 120 seconds (2 minutes) recommended

## Contributing

Contributions are welcome! Areas for improvement:

- [ ] Support for Firefox, Brave, Chromium browsers
- [ ] Caching mechanism to reduce API calls
- [ ] Additional AI service monitors
- [ ] Better error messages
- [ ] Screenshot examples

## License

MIT - See [LICENSE](LICENSE) file for details.

## Acknowledgments

- Uses [browser_cookie3](https://github.com/borisbabic/browser_cookie3) for cookie extraction
- Uses [curl_cffi](https://github.com/yifeikong/curl_cffi) for making authenticated requests

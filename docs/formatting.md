# Formatting Configuration

You can customize the bar text and tooltip via `--format` and `--tooltip-format`. Both flags accept the same variables and the same `{?var}...{/var}` conditional syntax.

**Provider support**:

| Provider | `--format` / `--tooltip-format` |
|---|---|
| `claude-usage` | ✓ |
| `codex-usage` | ✓ |
| `copilot-usage` | ✓ |
| `zai-usage` | ✓ |
| `zen-balance` | ✗ — fixed format |

Each provider exposes a different set of variables. Pick the table for your provider below.

## Claude & Codex variables

Both `claude-usage` and `codex-usage` show two usage windows. Variables are identical between them, with one difference noted in the table.

| Variable            | Description                              | Example                               |
| ------------------- | ---------------------------------------- | ------------------------------------- |
| `{icon}`            | Service icon with color styling          | `<span foreground='#DE7356'>󰜡</span>` |
| `{icon_plain}`      | Service icon without styling             | `󰜡` (Claude) or `󰬫` (Codex)           |
| `{time_icon}`       | Clock icon with color styling            | `<span foreground='#DE7356'>󰔚</span>` |
| `{time_icon_plain}` | Clock icon without styling               | `󰔚`                                   |
| `{5h_pct}`          | Short-window percentage (5-hour)         | `45`                                  |
| `{7d_pct}`          | Long-window percentage (7-day)           | `67`                                  |
| `{5h_reset}`        | Short-window reset time                  | `4h23m` or `Not started`              |
| `{7d_reset}`        | Long-window reset time                   | `2d15h` or `Not started`              |
| `{pct}`             | Active window percentage                 | Varies by active window               |
| `{reset}`           | Active window reset time                 | Varies by active window               |
| `{status}`          | Status text                              | `Ready`, `Pause`, or empty            |
| `{win}`             | Active window name                       | Claude: `5h` / `7d` — Codex: `Primary` / `Secondary` |

## Copilot variables (`copilot-usage`)

| Variable            | Description                          | Example                          |
| ------------------- | ------------------------------------ | -------------------------------- |
| `{icon}`            | Copilot icon with color styling      | styled span                      |
| `{icon_plain}`      | Copilot icon without styling         | ``                              |
| `{time_icon}`       | Clock icon with color styling        | styled span                      |
| `{time_icon_plain}` | Clock icon without styling           | `󰔚`                              |
| `{pct}`             | Used percentage of monthly quota     | `27`                             |
| `{used}`            | Used premium requests (number)       | `81.0`                           |
| `{used_str}`        | Used premium requests (formatted)    | `81` (omits `.0` for whole numbers) |
| `{quota}`           | Configured `COPILOT_QUOTA`           | `300`                            |
| `{reset}`           | Time until next month, 1st 00:00 UTC | `12d4h`                          |

## Z.ai variables (`zai-usage`)

The first group is always present. The `tools_*` group is only present when the API returns a monthly tool quota (`time_limit`).

| Variable            | Description                                  | Example         |
| ------------------- | -------------------------------------------- | --------------- |
| `{icon}`            | Z.ai icon with color styling                 | styled span     |
| `{icon_plain}`      | Z.ai icon without styling                    | `Z`             |
| `{time_icon}`       | Clock icon with color styling                | styled span     |
| `{time_icon_plain}` | Clock icon without styling                   | `󰔚`             |
| `{pct}`             | 5-hour token-window percentage               | `45`            |
| `{reset}`           | 5-hour token-window reset                    | `2h17m` or `??` |
| `{status}`          | Status text                                  | `Ready`, `Pause`, or empty |
| `{tools_pct}`       | Monthly tool-quota percentage                | `12`            |
| `{tools_remaining}` | Monthly tool-quota remaining                 | `88`            |
| `{tools_reset}`     | Monthly tool-quota reset                     | `18d2h`         |

## Format examples

```bash
# Claude — show only 5-hour data without styled icons
claude-usage --waybar --format "{icon_plain} {5h_pct}% {time_icon_plain} {5h_reset}"

# Codex — show both windows
codex-usage --waybar --format "{icon} P:{5h_pct}% S:{7d_pct}%"

# Copilot — explicit count instead of percentage
copilot-usage --waybar --format "{icon} {used_str}/{quota}"

# Z.ai — show monthly tool quota in the bar (when available)
zai-usage --waybar --format "{icon} {pct}% — tools {tools_pct}%"

# Custom tooltip showing both Claude windows
claude-usage --waybar --tooltip-format "5-Hour: {5h_pct}%  Reset: {5h_reset}\n7-Day: {7d_pct}%  Reset: {7d_reset}"

# Always show 5-hour window (Claude/Codex only — disable auto-switch to long window)
claude-usage --waybar --show-5h
```

## Waybar configuration example

Pass formatting through the script's `--format` argument (rather than Waybar's own `format` field), so styled icons with embedded HTML colors render correctly:

```jsonc
"custom/claude-usage": {
    "exec": "~/.local/bin/claude-usage --waybar --format '{icon} {5h_pct}% {time_icon} {5h_reset}'",
    "return-type": "json",
    "interval": 120,
    "on-click": "~/.local/bin/claude-usage --waybar --format '{icon} {5h_pct}% {time_icon} {5h_reset}'"
}
```

Without `--format`, the script provides a default that works as-is:

```jsonc
"custom/claude-usage": {
    "exec": "~/.local/bin/claude-usage --waybar",
    "return-type": "json",
    "interval": 120
}
```

This displays: `󰜡 98% 󰔚 2d21h` (with colored icons).

**Note**: Some shells require escaping `%` as `%%` inside `exec` strings.

## Conditional formatting

Show or hide sections of a format string based on whether a variable resolved to a non-empty value (e.g., a window hasn't started yet). The conditional syntax works in both `--format` and `--tooltip-format`.

**Single-variable conditions**:

- `{?5h_reset}...{/5h_reset}` — show content only if `{5h_reset}` is set
- `{?7d_reset}...{/7d_reset}` — show content only if `{7d_reset}` is set

**Multi-variable conditions**:

- `{?5h_reset&7d_reset}...{/}` — show content only if **both** variables are set

A variable is treated as "not set" only when its value is empty or the literal string `Not started`. In practice this means conditionals are useful for Claude/Codex's `{5h_reset}` / `{7d_reset}` (which render `Not started` before a window starts). Other providers' "missing data" sentinels (e.g. Z.ai's `??`) are not recognized by the conditional.

### Conditional examples

```bash
# Show both windows only if active, with separator only when both are present
claude-usage --waybar --format '{?5h_reset}{5h_pct}/{5h_reset}{/5h_reset}{?5h_reset&7d_reset} - {/}{?7d_reset}{7d_pct}/{7d_reset}{/7d_reset}'

# Show 5h data only when active, otherwise show nothing
codex-usage --waybar --format '{?5h_reset}{icon} {5h_pct}% {time_icon} {5h_reset}{/5h_reset}'
```

The first example will display:

- Nothing when both windows are "Not started"
- `45/4h23m` when only the 5h window is active
- `67/2d15h` when only the 7d window is active
- `45/4h23m - 67/2d15h` when both windows are active

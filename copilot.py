from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from common import format_eta, format_output, get_cached_or_fetch


# ==================== Configuration ====================

CONFIG_PATH = Path("~/.config/waybar-ai-usage/copilot.conf").expanduser()
COPILOT_ICON = "\uf4b8"   # nf-seti-copilot — same as LazyVim/Neovim Copilot ()
COPILOT_COLOR = "#8b5cf6"
DEFAULT_QUOTA = 300
GITHUB_API_BASE = "https://api.github.com"


def load_copilot_config(config_path: Path | None = None) -> dict:
    """Load Copilot config from file. Returns dict with GITHUB_TOKEN and COPILOT_QUOTA."""
    path = config_path or CONFIG_PATH
    config: dict = {"GITHUB_TOKEN": None, "COPILOT_QUOTA": DEFAULT_QUOTA}

    if not path.exists():
        return config

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key == "GITHUB_TOKEN":
                config["GITHUB_TOKEN"] = value
            elif key == "COPILOT_QUOTA":
                try:
                    config["COPILOT_QUOTA"] = int(value)
                except ValueError:
                    pass

    return config


# ==================== Core Logic: Get Usage ====================

def _github_get(url: str, token: str) -> dict | list:
    """Make authenticated GET request to GitHub API."""
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "waybar-ai-usage/copilot",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e


def _get_github_username(token: str) -> str:
    """Fetch and cache the authenticated GitHub username (TTL: 1 hour)."""
    data = get_cached_or_fetch(
        "copilot_user",
        lambda: _github_get(f"{GITHUB_API_BASE}/user", token),
        ttl=3600,
    )
    username = data.get("login") if isinstance(data, dict) else None
    if not username:
        raise RuntimeError("Could not determine GitHub username from /user endpoint")
    return username


def _fetch_copilot_usage_uncached(token: str) -> dict:
    """Fetch Copilot premium request usage from GitHub API (not cached)."""
    username = _get_github_username(token)
    url = f"{GITHUB_API_BASE}/users/{username}/settings/billing/premium_request/usage"
    usage_data = _github_get(url, token)

    # Response may be a list directly or a dict with usageItems
    if isinstance(usage_data, list):
        usage_items = usage_data
    else:
        usage_items = usage_data.get("usageItems", [])

    used = sum(item.get("grossQuantity", 0) for item in usage_items)
    return {"used": round(used, 1), "raw": usage_data}


def get_copilot_usage(token: str) -> dict:
    """Fetch Copilot usage with file-based caching (TTL: 60 seconds)."""
    return get_cached_or_fetch("copilot", lambda: _fetch_copilot_usage_uncached(token))


# ==================== Output: CLI / Waybar ====================

def _next_month_reset_iso() -> str:
    """Return ISO timestamp for 00:00 UTC on the 1st of next month."""
    now = datetime.now(timezone.utc)
    if now.month == 12:
        reset = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        reset = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return reset.isoformat()


def print_cli(used: float, quota: int) -> None:
    """Print usage to terminal (for debugging)."""
    pct = round(used / quota * 100) if quota > 0 else 0
    reset_str = format_eta(_next_month_reset_iso())
    print(f"GitHub Copilot Premium Requests")
    print("-" * 40)
    print(f"Used : {used} / {quota} ({pct}%)")
    print(f"Reset: {reset_str} (next month, 1st at 00:00 UTC)")


def print_waybar(
    used: float,
    quota: int,
    format_str: str | None = None,
    tooltip_format: str | None = None,
) -> None:
    """Print Waybar JSON output."""
    pct = min(round(used / quota * 100) if quota > 0 else 0, 100)
    reset_iso = _next_month_reset_iso()
    reset_str = format_eta(reset_iso)

    icon_styled = f"<span foreground='{COPILOT_COLOR}' size='large'>{COPILOT_ICON} </span>"
    time_icon_styled = f"<span foreground='{COPILOT_COLOR}' size='large'>\U000f051a</span>"  # 󰔚

    used_str = str(int(used)) if used == int(used) else str(used)

    data = {
        "icon": icon_styled,
        "icon_plain": COPILOT_ICON,
        "time_icon": time_icon_styled,
        "time_icon_plain": "\U000f051a",
        "used": used,
        "used_str": used_str,
        "quota": quota,
        "pct": pct,
        "reset": reset_str,
    }

    if format_str:
        text = format_output(format_str, data)
    else:
        text = f"{icon_styled}{pct}% {time_icon_styled} {reset_str}"

    if tooltip_format:
        tooltip = format_output(tooltip_format, data)
    else:
        tooltip = (
            f"GitHub Copilot Premium Requests\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Used:   {used_str} / {quota} ({pct}%)\n"
            f"Reset:  {reset_str} (next month)\n"
            f"\nClick to Refresh"
        )

    if pct < 50:
        cls = "copilot-low"
    elif pct < 80:
        cls = "copilot-mid"
    else:
        cls = "copilot-high"

    output = {
        "text": text,
        "tooltip": tooltip,
        "class": cls,
        "percentage": pct,
    }
    print(json.dumps(output))


# ==================== CLI Entry Point ====================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show GitHub Copilot premium request usage in Waybar",
    )
    parser.add_argument(
        "--waybar",
        action="store_true",
        help="Output in JSON format for Waybar custom module",
    )
    parser.add_argument(
        "--format",
        type=str,
        help=(
            "Custom format string for waybar text. Available: {icon}, {icon_plain}, "
            "{used}, {quota}, {pct}, {reset}. Example: '{icon_plain} {pct}%%'"
        ),
    )
    parser.add_argument(
        "--tooltip-format",
        type=str,
        help="Custom format string for tooltip. Uses same variables as --format.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help=f"Path to copilot config file (default: {CONFIG_PATH})",
    )
    args = parser.parse_args()

    config = load_copilot_config(args.config)
    token = config["GITHUB_TOKEN"]
    quota = config["COPILOT_QUOTA"]

    if not token:
        if args.waybar:
            print(json.dumps({
                "text": f"<span foreground='#ff5555'>{COPILOT_ICON} No Token</span>",
                "tooltip": (
                    f"No GITHUB_TOKEN found in {args.config}\n"
                    f"Create the file with:\n"
                    f"GITHUB_TOKEN=ghp_xxxxx\n"
                    f"COPILOT_QUOTA=300"
                ),
                "class": "critical",
            }))
            sys.exit(0)
        else:
            print(f"[!] Error: No GITHUB_TOKEN in {args.config}", file=sys.stderr)
            sys.exit(1)

    try:
        usage = get_copilot_usage(token)
        used = usage.get("used", 0)
    except Exception as e:
        if args.waybar:
            err_msg = str(e)
            short_err = "Auth Err" if "401" in err_msg or "403" in err_msg else "Net Err"
            print(json.dumps({
                "text": f"<span foreground='#ff5555'>{COPILOT_ICON} {short_err}</span>",
                "tooltip": f"Error fetching Copilot usage:\n{err_msg}",
                "class": "critical",
            }))
            sys.exit(0)
        else:
            print(f"[!] Critical Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.waybar:
        print_waybar(used, quota, args.format, args.tooltip_format)
    else:
        print_cli(used, quota)


if __name__ == "__main__":
    main()

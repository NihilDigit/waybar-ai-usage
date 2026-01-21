from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

from curl_cffi import requests

from common import format_eta, load_cookies, parse_window_percent, format_output


# ==================== Configuration ====================

CLAUDE_DOMAIN = "claude.ai"

BASE_HEADERS = {
    "Referer": "https://claude.ai/chats",
    "Origin": "https://claude.ai",
    "Accept": "application/json, text/plain, */*",
}

# SVG icon path (unused in current version)
SCRIPT_DIR = Path(__file__).parent
ICON_PATH = SCRIPT_DIR / "assets" / "claude.svg"


# ==================== Core Logic: Get Usage ====================

def get_claude_usage(browsers: list[str] | None = None) -> dict:
    """Fetch Claude usage data using curl_cffi to impersonate Chrome"""
    try:
        cookies, _browser = load_cookies(CLAUDE_DOMAIN, browsers)
    except Exception as e:
        raise RuntimeError(f"Failed to read cookies: {e}")

    org_id = cookies.get("lastActiveOrg")
    if not org_id:
        raise RuntimeError(
            "Missing 'lastActiveOrg' in cookies.\n"
            "Please refresh Claude page in browser or switch Organization."
        )

    url = f"https://{CLAUDE_DOMAIN}/api/organizations/{org_id}/usage"

    # Retry once (2 attempts total)
    last_error = None
    for attempt in range(2):
        try:
            resp = requests.get(
                url,
                cookies=cookies,
                headers=BASE_HEADERS,
                impersonate="chrome",
                timeout=10
            )

            if resp.status_code == 403:
                raise RuntimeError("403 Forbidden: Try updating browser_cookie3 or refresh the page in browser.")

            resp.raise_for_status()
            return resp.json()

        except Exception as e:
            last_error = e
            if attempt == 0:  # First failure, retry
                continue

    # Both attempts failed
    raise RuntimeError(f"Request failed: {last_error}")


# ==================== Output: CLI / Waybar ====================

def print_cli(usage: dict) -> None:
    """Print usage to terminal (for debugging)."""
    print(json.dumps(usage, indent=2))

    fh = parse_window_percent(usage.get("five_hour"))
    sd = parse_window_percent(usage.get("seven_day"))

    def _fmt_reset(win):
        if win.utilization == 0 and win.resets_at is None:
            return "Not started"
        return format_eta(win.resets_at)

    print("-" * 40)
    print(f"5-hour : {fh.utilization:.1f}%  (Reset in {_fmt_reset(fh)})")
    print(f"7-day  : {sd.utilization:.1f}%  (Reset in {_fmt_reset(sd)})")


def print_waybar(usage: dict, format_str: str | None = None, tooltip_format: str | None = None, show_5h: bool = False) -> None:
    fh = parse_window_percent(usage.get("five_hour"))
    sd = parse_window_percent(usage.get("seven_day"))

    # Get raw window data to check for unused state
    fh_raw = usage.get("five_hour") or {}
    sd_raw = usage.get("seven_day") or {}

    # Prepare all data points without icons
    fh_reset_str = format_eta(fh.resets_at) if fh.resets_at else "Not started"
    sd_reset_str = format_eta(sd.resets_at) if sd.resets_at else "Not started"

    # Icons with colors (users can customize)
    icon_styled = "<span foreground='#DE7356' size='large'>󰜡</span>"
    time_icon_styled = "<span foreground='#DE7356' size='large'>󰔚</span>"

    # Determine active window based on show_5h flag or default logic
    if show_5h:
        # Always show 5-hour window
        target = fh
        target_raw = fh_raw
        win_name = "5h"
        window_length = 18000  # 5 hours in seconds
    elif sd.utilization >= 100:
        # 7-day window exhausted
        target = sd
        target_raw = sd_raw
        win_name = "7d"
        window_length = 604800
    elif sd.utilization > 80:
        # 7-day window high usage
        target = sd
        target_raw = sd_raw
        win_name = "7d"
        window_length = 604800  # 7 days in seconds
    else:
        # Default to 5h window
        target = fh
        target_raw = fh_raw
        win_name = "5h"
        window_length = 18000  # 5 hours in seconds

    pct = int(round(target.utilization))

    window_not_started = (target.utilization == 0 and target.resets_at is None)

    # Check if window is unused (utilization == 0 and reset time near window length)
    is_unused = False
    if target.utilization == 0 and target.resets_at:
        from datetime import datetime, timezone
        try:
            if isinstance(target.resets_at, str):
                reset_at_str = target.resets_at
                if reset_at_str.endswith('Z'):
                    reset_at_str = reset_at_str[:-1] + '+00:00'
                reset_dt = datetime.fromisoformat(reset_at_str)
            else:
                reset_dt = datetime.fromtimestamp(target.resets_at, tz=timezone.utc)

            now = datetime.now(timezone.utc)
            reset_after = int((reset_dt - now).total_seconds())

            # If reset time is close to window length (allow 1s error), consider it unused
            is_unused = (reset_after >= window_length - 1)
        except Exception:
            pass

    # Determine status
    if sd.utilization >= 100:
        status = "Pause"
    elif is_unused or window_not_started:
        status = "Ready"
    else:
        status = ""

    # Prepare data dictionary for formatting
    data = {
        "5h_pct": int(round(fh.utilization)),
        "7d_pct": int(round(sd.utilization)),
        "5h_reset": fh_reset_str,
        "7d_reset": sd_reset_str,
        "icon": icon_styled,
        "icon_plain": "󰜡",
        "time_icon": time_icon_styled,
        "time_icon_plain": "󰔚",
        "status": status,
        "pct": pct,
        "reset": format_eta(target.resets_at) if target.resets_at else "Not started",
        "win": win_name,
    }

    # Use custom format or default
    if format_str:
        text = format_output(format_str, data)
    else:
        # Default format (backward compatible)
        if status == "Pause":
            text = f"{icon_styled} Pause"
        elif status == "Ready":
            text = f"{icon_styled} Ready"
        else:
            text = f"{icon_styled} {pct}% {time_icon_styled} {data['reset']}"

    # Use custom tooltip format or default
    if tooltip_format:
        tooltip = format_output(tooltip_format, data)
    else:
        # Default tooltip
        tooltip = (
            "Window     Used    Reset\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"5-Hour     {fh.utilization:>3.0f}%    {fh_reset_str}\n"
            f"7-Day      {sd.utilization:>3.0f}%    {sd_reset_str}\n"
            "\n"
            "Click to Refresh"
        )

    if pct < 50:
        cls = "claude-low"
    elif pct < 80:
        cls = "claude-mid"
    else:
        cls = "claude-high"

    output = {
        "text": text,
        "tooltip": tooltip,
        "class": cls,
        "alt": win_name,
        "percentage": data["5h_pct"] if show_5h else data["pct"],
    }

    print(json.dumps(output))


# ==================== CLI Entry Point ====================

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--waybar",
        action="store_true",
        help="Output in JSON format for Waybar custom module",
    )
    parser.add_argument(
        "--browser",
        action="append",
        help="Browser cookie source to try (repeatable). Example: --browser chromium",
    )
    parser.add_argument(
        "--format",
        type=str,
        help=(
            "Custom format string for waybar text. Available: {icon}, {icon_plain}, "
            "{time_icon}, {time_icon_plain}, {5h_pct}, {7d_pct}, {5h_reset}, {7d_reset}, "
            "{status}, {pct}, {reset}, {win}. Example: '{icon_plain} {5h_pct}%%'"
        ),
    )
    parser.add_argument(
        "--tooltip-format",
        type=str,
        help="Custom format string for tooltip. Uses same variables as --format.",
    )
    parser.add_argument(
        "--show-5h",
        action="store_true",
        help="Always show 5-hour window data (instead of auto-switching to 7-day at 80%%)",
    )
    args = parser.parse_args()

    try:
        usage = get_claude_usage(args.browser)
    except Exception as e:
        if args.waybar:
            err_msg = str(e)
            short_err = "Auth Err" if "403" in err_msg else "Net Err"
            print(json.dumps({
                "text": f"<span foreground='#ff5555'>󰜡 {short_err}</span>",
                "tooltip": f"Error fetching Claude usage:\n{err_msg}",
                "class": "critical"
            }))
            sys.exit(0)
        else:
            print(f"[!] Critical Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.waybar:
        print_waybar(usage, args.format, args.tooltip_format, args.show_5h)
    else:
        print_cli(usage)


if __name__ == "__main__":
    main()

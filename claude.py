from __future__ import annotations

import argparse
import json
import sys
from typing import Dict

import os
from pathlib import Path

from curl_cffi import requests
import browser_cookie3

from common import parse_window_percent, format_eta


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

# Supported browsers
SUPPORTED_BROWSERS = [
    ("chrome", browser_cookie3.chrome),
    ("firefox", browser_cookie3.firefox),
    ("brave", browser_cookie3. brave),
    ("edge", browser_cookie3.edge),
    ("opera", browser_cookie3.opera),
    ("chromium", browser_cookie3. chromium),
    ("vivaldi", browser_cookie3. vivaldi),
]


# ==================== Core Logic: Get Usage ====================

def get_claude_usage() -> dict:
    """Fetch Claude usage data using curl_cffi to impersonate Chrome"""
    try:
        cookies = None
        for browser_name, browser_func in SUPPORTED_BROWSERS:
            try:
                cj = browser_func(domain_name=CLAUDE_DOMAIN)
                cookies = {c.name: c.value for c in cj}
                if cookies. get("lastActiveOrg"):
                    break
            except Exception:
                continue
        if not cookies or not cookies.get("lastActiveOrg"):
            raise RuntimeError(
                f"No valid cookies found.  Please log in to Claude in one of: "
                f"{', '.join(b[0] for b in SUPPORTED_BROWSERS)}"
            )
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


def print_waybar(usage: dict) -> None:
    fh = parse_window_percent(usage.get("five_hour"))
    sd = parse_window_percent(usage.get("seven_day"))

    # Get raw window data to check for unused state
    fh_raw = usage.get("five_hour") or {}
    sd_raw = usage.get("seven_day") or {}

    # Default to 5h window, unless 7d window exceeds 80%
    if sd.utilization >= 100:
        # 7-day window exhausted
        target = sd
        win_name = "7d"
        pct = 100
        icon = "<span foreground='#DE7356' size='large'>󰜡</span>"
        text = f"{icon} Pause"
    else:
        if sd.utilization > 80:
            target = sd
            target_raw = sd_raw
            win_name = "7d"
            window_length = 604800  # 7 days in seconds
        else:
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

        icon = "<span foreground='#DE7356' size='large'>󰜡</span>"

        if is_unused or window_not_started:
            text = f"{icon} Ready"
        else:
            eta = format_eta(target.resets_at)
            time_icon = "<span foreground='#DE7356' size='large'>󰔚</span>"
            text = f"{icon} {pct}% {time_icon} {eta}"

    fh_reset = format_eta(fh.resets_at) if fh.resets_at else "Not started"
    sd_reset = format_eta(sd.resets_at) if sd.resets_at else "Not started"

    tooltip = (
        "Window     Used    Reset\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"5-Hour     {fh.utilization:>3.0f}%    {fh_reset}\n"
        f"7-Day      {sd.utilization:>3.0f}%    {sd_reset}\n"
        "\n"
        "Click to Refresh"
    )

    if pct < 50:
        cls = "claude-low"
    elif pct < 80:
        cls = "claude-mid"
    else:
        cls = "claude-high"

    print(json.dumps({
        "text": text,
        "tooltip": tooltip,
        "class": cls,
        "alt": win_name
    }))


# ==================== CLI Entry Point ====================

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--waybar",
        action="store_true",
        help="Output in JSON format for Waybar custom module",
    )
    args = parser.parse_args()

    try:
        usage = get_claude_usage()
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
        print_waybar(usage)
    else:
        print_cli(usage)


if __name__ == "__main__":
    main()

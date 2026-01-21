from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from curl_cffi import requests

from common import format_eta, load_cookies, parse_window_direct, format_output


# ================= Configuration =================

BASE_HEADERS = {
    "Referer": "https://chatgpt.com/",
    "Origin": "https://chatgpt.com",
    "Accept": "*/*"
}

SESSION_URL = "https://chatgpt.com/api/auth/session"
CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"

# SVG icon path (unused in current version)
SCRIPT_DIR = Path(__file__).parent
ICON_PATH = SCRIPT_DIR / "assets" / "codex.svg"

# ================= Network Logic =================

def get_codex_usage(browsers: list[str] | None = None) -> dict:
    try:
        cookies_dict, _browser = load_cookies("chatgpt.com", browsers)
    except Exception as e:
        raise RuntimeError(f"Failed to read browser cookies: {e}")

    # Retry once (2 attempts total)
    last_error = None
    for attempt in range(2):
        try:
            # Get Access Token
            session_resp = requests.get(
                SESSION_URL,
                cookies=cookies_dict,
                headers=BASE_HEADERS,
                impersonate="chrome",
                timeout=10
            )

            if session_resp.status_code == 403:
                raise RuntimeError("403 Forbidden: Cloudflare blocked, check IP or update browser_cookie3")

            session_resp.raise_for_status()
            session_data = session_resp.json()

            access_token = session_data.get("accessToken")
            if not access_token:
                raise RuntimeError("accessToken not found in session response.")

            # Get Usage Data
            usage_headers = BASE_HEADERS.copy()
            usage_headers["Authorization"] = f"Bearer {access_token}"

            usage_resp = requests.get(
                CODEX_USAGE_URL,
                cookies=cookies_dict,
                headers=usage_headers,
                impersonate="chrome",
                timeout=10
            )

            usage_resp.raise_for_status()
            return usage_resp.json()

        except Exception as e:
            last_error = e
            if attempt == 0:  # First failure, retry
                continue

    # Both attempts failed
    raise RuntimeError(f"Request failed: {last_error}")


# ================= Output Logic =================


def print_waybar(
    usage: dict,
    format_str: str | None = None,
    tooltip_format: str | None = None,
    show_5h: bool = False,
) -> None:
    rate = usage.get("rate_limit") or {}
    p_win = parse_window_direct(rate.get("primary_window"))
    s_win = parse_window_direct(rate.get("secondary_window"))

    # Get raw window data to check for unused state
    p_raw = rate.get("primary_window") or {}
    s_raw = rate.get("secondary_window") or {}

    # Prepare all data points without icons
    p_reset_str = format_eta(p_win.resets_at) if p_win.resets_at else "Not started"
    s_reset_str = format_eta(s_win.resets_at) if s_win.resets_at else "Not started"

    # Icons with colors (users can customize)
    icon_styled = "<span foreground='#74AA9C' size='large'>󰬫</span>"
    time_icon_styled = "<span foreground='#74AA9C' size='large'>󰔚</span>"

    # Determine active window based on show_5h flag or default logic
    if show_5h:
        # Always show primary (5-hour) window
        target_win = p_win
        target_raw = p_raw
        win_type = "Primary"
    elif s_win.utilization >= 100:
        # Secondary window exhausted
        target_win = s_win
        target_raw = s_raw
        win_type = "Secondary"
    elif s_win.utilization > 80:
        # Secondary window high usage
        target_win = s_win
        target_raw = s_raw
        win_type = "Secondary"
    else:
        # Default to Primary window
        target_win = p_win
        target_raw = p_raw
        win_type = "Primary"

    pct = int(round(target_win.utilization))

    # Check if window is unused (used_percent == 0 and reset_after near window length)
    used_pct = target_raw.get("used_percent", 0)
    reset_after = target_raw.get("reset_after_seconds", 0)
    window_length = target_raw.get("limit_window_seconds", 0)

    is_unused = (used_pct == 0 and reset_after >= window_length - 1)

    window_not_started = (target_win.utilization == 0 and target_win.resets_at is None)

    # Determine status
    if s_win.utilization >= 100:
        status = "Pause"
    elif is_unused or window_not_started:
        status = "Ready"
    else:
        status = ""

    # Prepare data dictionary for formatting
    data = {
        "5h_pct": int(round(p_win.utilization)),
        "7d_pct": int(round(s_win.utilization)),
        "5h_reset": p_reset_str,
        "7d_reset": s_reset_str,
        "icon": icon_styled,
        "icon_plain": "󰬫",
        "time_icon": time_icon_styled,
        "time_icon_plain": "󰔚",
        "status": status,
        "pct": pct,
        "reset": format_eta(target_win.resets_at) if target_win.resets_at else "Not started",
        "win": win_type,
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
            f"5-Hour     {p_win.utilization:>3.0f}%    {p_reset_str}\n"
            f"7-Day      {s_win.utilization:>3.0f}%    {s_reset_str}\n"
            "\n"
            "Click to Refresh"
        )

    if pct < 50:
        cls = "codex-low"
    elif pct < 80:
        cls = "codex-mid"
    else:
        cls = "codex-high"

    output = {
        "text": text,
        "tooltip": tooltip,
        "class": cls,
        "alt": win_type,
        "percentage": data["pct"],
    }

    print(json.dumps(output))


def print_cli(usage: dict) -> None:
    print(json.dumps(usage, indent=2))
    rate = usage.get("rate_limit") or {}
    p = parse_window_direct(rate.get("primary_window"))
    s = parse_window_direct(rate.get("secondary_window"))

    print("-" * 40)
    print(f"Primary   (Short): {p.utilization:>5.1f}% | Reset in {format_eta(p.resets_at)}")
    print(f"Secondary (Long) : {s.utilization:>5.1f}% | Reset in {format_eta(s.resets_at)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--waybar", action="store_true")
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
        usage = get_codex_usage(args.browser)
    except Exception as e:
        if args.waybar:
            err_msg = str(e)
            short_err = "Auth Err" if "403" in err_msg or "401" in err_msg else "Net Err"
            print(json.dumps({
                "text": f"<span foreground='#ff5555'>󰬫 {short_err}</span>",
                "tooltip": f"Error:\n{err_msg}",
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

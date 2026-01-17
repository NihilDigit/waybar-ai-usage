from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from curl_cffi import requests
import browser_cookie3

from common import parse_window_direct, format_eta


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

# Supported browsers
SUPPORTED_BROWSERS = [
    ("chrome", browser_cookie3.chrome),
    ("firefox", browser_cookie3.firefox),
    ("brave", browser_cookie3.brave),
    ("edge", browser_cookie3. edge),
    ("opera", browser_cookie3.opera),
    ("chromium", browser_cookie3. chromium),
    ("vivaldi", browser_cookie3.vivaldi),
]

# ================= Network Logic =================

def get_codex_usage() -> dict:
    try:
        cookies_dict = None
        for browser_name, browser_func in SUPPORTED_BROWSERS:
            try:
                cj = browser_func(domain_name="chatgpt.com")
                cookies_dict = {c.name: c.value for c in cj}
                if cookies_dict:
                    break
            except Exception:
                continue
    
        if not cookies_dict:
            raise RuntimeError(
                f"No valid cookies found.  Please log in to ChatGPT in one of: "
                f"{', '.join(b[0] for b in SUPPORTED_BROWSERS)}"
            )
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

def print_waybar(usage: dict) -> None:
    rate = usage.get("rate_limit") or {}
    p_win = parse_window_direct(rate.get("primary_window"))
    s_win = parse_window_direct(rate.get("secondary_window"))

    # Get raw window data to check for unused state
    p_raw = rate.get("primary_window") or {}
    s_raw = rate.get("secondary_window") or {}

    # Default to Primary window, unless Secondary window exceeds 80%
    if s_win.utilization >= 100:
        # Secondary window exhausted
        target_win = s_win
        win_type = "Secondary"
        pct = 100
        codex_icon = "<span foreground='#74AA9C' size='large'>󰬫</span>"
        text = f"{codex_icon} Pause"
    else:
        if s_win.utilization > 80:
            target_win = s_win
            target_raw = s_raw
            win_type = "Secondary"
        else:
            target_win = p_win
            target_raw = p_raw
            win_type = "Primary"

        pct = int(round(target_win.utilization))

        # Check if window is unused (used_percent == 0 and reset_after near window length)
        used_pct = target_raw.get("used_percent", 0)
        reset_after = target_raw.get("reset_after_seconds", 0)
        window_length = target_raw.get("limit_window_seconds", 0)

        is_unused = (used_pct == 0 and reset_after >= window_length - 1)

        codex_icon = "<span foreground='#74AA9C' size='large'>󰬫</span>"

        if is_unused:
            text = f"{codex_icon} Ready"
        else:
            # Check if window hasn't been started
            if target_win.utilization == 0 and target_win.resets_at is None:
                eta_text = "Not started"
            else:
                eta_text = format_eta(target_win.resets_at)

            time_icon = "<span foreground='#74AA9C' size='large'>󰔚</span>"
            text = f"{codex_icon} {pct}% {time_icon} {eta_text}"


    # Check if window hasn't been started
    if p_win.utilization == 0 and p_win.resets_at is None:
        p_reset = "Not started"
    else:
        p_reset = format_eta(p_win.resets_at)

    if s_win.utilization == 0 and s_win.resets_at is None:
        s_reset = "Not started"
    else:
        s_reset = format_eta(s_win.resets_at)

    tooltip = (
        "Window     Used    Reset\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"5-Hour     {p_win.utilization:>3.0f}%    {p_reset}\n"
        f"7-Day      {s_win.utilization:>3.0f}%    {s_reset}\n"
        "\n"
        "Click to Refresh"
    )

    if pct < 50:
        cls = "codex-low"
    elif pct < 80:
        cls = "codex-mid"
    else:
        cls = "codex-high"

    print(json.dumps({
        "text": text,
        "tooltip": tooltip,
        "class": cls,
        "alt": win_type
    }))


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
    args = parser.parse_args()

    try:
        usage = get_codex_usage()
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
        print_waybar(usage)
    else:
        print_cli(usage)

if __name__ == "__main__":
    main()

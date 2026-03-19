#!/usr/bin/env python3
"""OpenCode Zen balance fetcher for Waybar

Fetches current Zen balance from the OpenCode dashboard using browser cookies.
Similar to the claude-usage and codex-usage widgets.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from curl_cffi import requests

from common import get_cached_or_fetch, load_cookies, open_login_url, LOGIN_URLS


# ==================== Configuration ====================

ZEN_DOMAIN = "opencode.ai"
ZEN_URL = "https://opencode.ai/auth"

BASE_HEADERS = {
    "Referer": "https://opencode.ai/auth",
    "Origin": "https://opencode.ai",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CACHE_TTL = 120  # Cache for 120 seconds


# ==================== Core Logic: Get Balance ====================


def _parse_balance_from_html(html_content: str) -> float | None:
    """Parse balance from HTML content using various patterns"""

    # Pattern 1: JS state object — balance:<number> (integer or decimal)
    # e.g. balance:0  or  balance:19.43
    balance_match = re.search(
        r"balance:([0-9]+(?:\.[0-9]+)?)",
        html_content,
    )
    if balance_match:
        return float(balance_match.group(1))

    # Pattern 2: data-slot="balance" structure with HTML comments (legacy)
    balance_match = re.search(
        r'data-slot="balance"[^>]*>.*?Current balance.*?<b>\$\s*<!--\$-->([0-9]+\.[0-9]{2})<!--/-->',
        html_content,
        re.DOTALL,
    )
    if balance_match:
        return float(balance_match.group(1))

    # Pattern 3: Simple "Current balance $XX.XX" pattern (legacy)
    balance_match = re.search(
        r"Current balance\s*\$\s*([0-9]+\.[0-9]{2})",
        html_content,
    )
    if balance_match:
        return float(balance_match.group(1))

    return None


def _fetch_zen_balance_uncached(browsers: list[str] | None = None) -> dict:
    """Internal function to fetch Zen balance without caching"""
    try:
        cookies, _browser = load_cookies(ZEN_DOMAIN, browsers)
    except Exception as e:
        raise RuntimeError(f"Failed to read cookies: {e}")

    # Try zen URL first - it redirects to the specific workspace
    last_error = None
    for attempt in range(2):
        try:
            resp = requests.get(
                ZEN_URL,
                cookies=cookies,
                headers=BASE_HEADERS,
                impersonate="chrome",
                timeout=10,
                allow_redirects=True,  # Follow redirects to specific workspace
            )

            if resp.status_code == 403:
                raise RuntimeError(
                    "403 Forbidden: Try updating browser_cookie3 or refresh the page in browser."
                )

            resp.raise_for_status()

            # Parse the HTML to find the balance
            html_content = resp.text

            balance = _parse_balance_from_html(html_content)

            if balance is not None:
                return {"balance": balance, "currency": "USD"}
            else:
                raise RuntimeError(
                    "Could not find balance. Please ensure you're logged into opencode.ai/zen in your browser."
                )

        except Exception as e:
            last_error = e
            if attempt == 0:  # First failure, retry
                continue

    # All attempts failed
    raise RuntimeError(f"Request failed: {last_error}")


def get_zen_balance(browsers: list[str] | None = None) -> dict:
    """
    Fetch Zen balance using curl_cffi to impersonate Chrome.
    Uses file-based caching to prevent multiple Waybar instances from making
    concurrent API requests.
    """
    return get_cached_or_fetch(
        "zen-balance", lambda: _fetch_zen_balance_uncached(browsers), ttl=CACHE_TTL
    )


# ==================== Output: CLI / Waybar ====================


def print_cli(balance_data: dict) -> None:
    """Print balance to terminal (for debugging)."""
    print(f"Zen Balance: ${balance_data['balance']:.2f} {balance_data['currency']}")


def print_waybar(balance_data: dict) -> None:
    """Print balance in JSON format for Waybar"""
    balance = balance_data.get("balance", 0.0)

    # Format the balance text
    text = f"<span foreground='#DE7356'>ZEN</span> ${balance:.2f}"

    # Determine status class based on balance
    if balance < 5:
        cls = "zen-low"  # Red: critically low
    elif balance < 10:
        cls = "zen-medium"  # Yellow: getting low
    else:
        cls = "zen-high"  # Green: good balance

    # Build tooltip
    tooltip = (
        f"OpenCode Zen Balance\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Balance: ${balance:.2f} USD\n"
        f"\n"
        f"Click to refresh"
    )

    output = {
        "text": text,
        "tooltip": tooltip,
        "class": cls,
        "alt": f"${balance:.2f}",
    }

    print(json.dumps(output))


# ==================== CLI Entry Point ====================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch OpenCode Zen balance for Waybar or CLI"
    )
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
    args = parser.parse_args()

    try:
        balance_data = get_zen_balance(args.browser)
    except Exception as e:
        if args.waybar:
            err_msg = str(e)
            err_lower = err_msg.lower()
            is_http_auth = "403" in err_msg or "401" in err_msg
            is_cookie = "cookie" in err_lower
            short_err = (
                "Auth Err"
                if (is_http_auth or is_cookie)
                else "Net Err"
                if "failed" in err_lower or "timed out" in err_lower
                else "Err"
            )
            tooltip = f"Error fetching Zen balance:\n{err_msg}"
            if is_http_auth:
                if open_login_url(LOGIN_URLS["opencode.ai"]):
                    tooltip += "\n\nOpened login page — log in then click to refresh"
            else:
                tooltip += "\n\nMake sure you're logged into opencode.ai/zen"
            print(
                json.dumps(
                    {
                        "text": f"<span foreground='#ff5555'>ZEN {short_err}</span>",
                        "tooltip": tooltip,
                        "class": "critical",
                    }
                )
            )
            sys.exit(0)
        else:
            print(f"[!] Critical Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.waybar:
        print_waybar(balance_data)
    else:
        print_cli(balance_data)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

from common import format_eta, format_output, get_cached_or_fetch


# ==================== Configuration ====================

CONFIG_PATH = Path("~/.config/waybar-ai-usage/zai.conf").expanduser()
ZAI_ICON = "Z"
ZAI_COLOR = "#126EF4"
API_BASE = "https://api.z.ai"
QUOTA_URL = f"{API_BASE}/api/monitor/usage/quota/limit"


def load_zai_config(config_path: Path | None = None) -> dict:
    path = config_path or CONFIG_PATH
    config: dict = {"ZAI_TOKEN": None}

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
            if key == "ZAI_TOKEN":
                config["ZAI_TOKEN"] = value

    return config


# ==================== Core Logic: Get Quota ====================


def _api_get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "waybar-ai-usage/zai",
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


def _fetch_zai_quota_uncached(token: str) -> dict:
    data = _api_get(QUOTA_URL, token)

    if not data.get("success"):
        msg = data.get("msg", "Unknown error")
        raise RuntimeError(f"API error: {msg}")

    limits = data.get("data", {}).get("limits", [])

    token_limit = None
    time_limit = None

    for item in limits:
        if item.get("type") == "TOKENS_LIMIT":
            token_limit = item
        elif item.get("type") == "TIME_LIMIT":
            time_limit = item

    return {
        "token_limit": token_limit,
        "time_limit": time_limit,
        "level": data.get("data", {}).get("level"),
    }


def get_zai_quota(token: str) -> dict:
    return get_cached_or_fetch(
        "zai",
        lambda: _fetch_zai_quota_uncached(token),
        ttl=120,
    )


# ==================== Helpers ====================


def _format_tokens(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def _format_ms_reset(ms: int | None) -> str:
    if not ms:
        return "??"
    return format_eta(ms // 1000)


# ==================== Output: CLI / Waybar ====================


def print_cli(quota: dict) -> None:
    tl = quota.get("token_limit")
    ml = quota.get("time_limit")

    print(f"Z.ai Usage (level: {quota.get('level', '?')})")
    print("-" * 50)

    if tl:
        pct = tl.get("percentage", 0)
        reset = _format_ms_reset(tl.get("nextResetTime"))
        print(f"5h Tokens : {pct}%  (Reset in {reset})")

    if ml:
        pct = ml.get("percentage", 0)
        remaining = ml.get("remaining", 0)
        reset = _format_ms_reset(ml.get("nextResetTime"))
        print(f"Monthly Tools: {pct}% ({remaining} remaining)")
        for d in ml.get("usageDetails", []):
            code = d.get("modelCode", "?")
            usage = d.get("usage", 0)
            print(f"  - {code}: {usage}")


def print_waybar(
    quota: dict,
    format_str: str | None = None,
    tooltip_format: str | None = None,
) -> None:
    tl = quota.get("token_limit")
    ml = quota.get("time_limit")

    pct = tl.get("percentage", 0) if tl else 0
    reset_str = _format_ms_reset(tl.get("nextResetTime")) if tl else "??"

    is_ready = pct == 0 and tl is not None
    is_exhausted = pct >= 100

    if is_exhausted:
        status = "Pause"
    elif is_ready:
        status = "Ready"
    else:
        status = ""

    icon_styled = f"<span foreground='{ZAI_COLOR}' size='large'>{ZAI_ICON}</span>"
    time_icon_styled = f"<span foreground='{ZAI_COLOR}' size='large'>\U000f051a</span>"

    data = {
        "icon": icon_styled,
        "icon_plain": ZAI_ICON,
        "time_icon": time_icon_styled,
        "time_icon_plain": "\U000f051a",
        "pct": pct,
        "reset": reset_str,
        "status": status,
    }

    if ml:
        ml_pct = ml.get("percentage", 0)
        ml_remaining = ml.get("remaining", 0)
        ml_reset = _format_ms_reset(ml.get("nextResetTime"))
        data["tools_pct"] = ml_pct
        data["tools_remaining"] = ml_remaining
        data["tools_reset"] = ml_reset

    if format_str:
        text = format_output(format_str, data)
    else:
        if status == "Pause":
            text = f"{icon_styled} Pause"
        elif status == "Ready":
            text = f"{icon_styled} Ready"
        else:
            text = f"{icon_styled} {pct}% {time_icon_styled} {reset_str}"

    if tooltip_format:
        tooltip = format_output(tooltip_format, data)
    else:
        lines = [
            "Window     Used    Reset",
            "\u2501" * 24,
        ]
        if tl:
            lines.append(f"Tokens     {pct:>3}%    {reset_str}")
        if ml:
            ml_pct = ml.get("percentage", 0)
            ml_reset = _format_ms_reset(ml.get("nextResetTime"))
            lines.append(f"Tools      {ml_pct:>3}%    {ml_reset}")
            for d in ml.get("usageDetails", []):
                code = d.get("modelCode", "?")
                usage = d.get("usage", 0)
                lines.append(f"  \u2022 {code:<12} {_format_tokens(usage)}")
        lines.append("")
        lines.append("Click to Refresh")
        tooltip = "\n".join(lines)

    if pct < 50:
        cls = "zai-low"
    elif pct < 80:
        cls = "zai-mid"
    else:
        cls = "zai-high"

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
        description="Show Z.ai usage in Waybar",
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
            "{pct}, {reset}, {status}, {tools_pct}, {tools_remaining}, {tools_reset}. "
            "Example: '{icon_plain} {pct}%%'"
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
        help=f"Path to Z.ai config file (default: {CONFIG_PATH})",
    )
    args = parser.parse_args()

    config = load_zai_config(args.config)
    token = config["ZAI_TOKEN"]

    if not token:
        if args.waybar:
            print(json.dumps({
                "text": f"<span foreground='#ff5555'>{ZAI_ICON} No Token</span>",
                "tooltip": (
                    f"No ZAI_TOKEN found in {args.config}\n"
                    f"1. Go to https://z.ai and log in\n"
                    f"2. Open DevTools (F12) > Network tab\n"
                    f"3. Find a request to api.z.ai and copy the Authorization header\n"
                    f"4. Save as ZAI_TOKEN=eyJ... in {args.config}"
                ),
                "class": "critical",
            }))
            sys.exit(0)
        else:
            print(
                f"[!] Error: No ZAI_TOKEN in {args.config}",
                file=sys.stderr,
            )
            print(
                f"    Create config: mkdir -p ~/.config/waybar-ai-usage",
                file=sys.stderr,
            )
            print(
                f"    Then add: ZAI_TOKEN=your_token_here",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        quota = get_zai_quota(token)
    except Exception as e:
        if args.waybar:
            err_msg = str(e)
            is_auth = "401" in err_msg or "403" in err_msg
            short_err = "Auth Err" if is_auth else "Net Err"
            tooltip = f"Error fetching Z.ai quota:\n{err_msg}"
            print(json.dumps({
                "text": f"<span foreground='#ff5555'>{ZAI_ICON} {short_err}</span>",
                "tooltip": tooltip,
                "class": "critical",
            }))
            sys.exit(0)
        else:
            print(f"[!] Critical Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.waybar:
        print_waybar(quota, args.format, args.tooltip_format)
    else:
        print_cli(quota)


if __name__ == "__main__":
    main()

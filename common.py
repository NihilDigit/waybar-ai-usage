"""Common utilities shared between claude.py and codex.py"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Optional

import browser_cookie3


DEFAULT_BROWSERS = ("chrome", "chromium", "brave", "edge", "firefox")


def load_cookies(domain: str, browsers: Iterable[str] | None = None) -> tuple[dict, str]:
    """Load cookies for a domain from the first available browser in order."""
    browsers = list(browsers or DEFAULT_BROWSERS)
    errors: list[str] = []

    for name in browsers:
        loader = getattr(browser_cookie3, name, None)
        if loader is None:
            errors.append(f"{name}: unsupported by browser_cookie3")
            continue

        try:
            cj = loader(domain_name=domain)
            cookies = {c.name: c.value for c in cj}
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            continue

        if cookies:
            return cookies, name

        errors.append(f"{name}: no cookies found")

    detail = "; ".join(errors) if errors else "no browsers provided"
    raise RuntimeError(f"Failed to read cookies for {domain}: {detail}")


@dataclass
class WindowUsage:
    """Usage information for a time window."""
    utilization: float
    resets_at: Optional[str | int]


def parse_window_percent(raw: Mapping[str, object] | None, key: str = "utilization") -> WindowUsage:
    """Parse window where Claude returns utilization as 0–100% (may be float)."""
    raw = raw or {}
    util = raw.get(key) or 0
    resets = raw.get("resets_at")

    try:
        util_f = float(util)
    except Exception:
        util_f = 0.0

    return WindowUsage(utilization=util_f, resets_at=resets)  # type: ignore[arg-type]


def parse_window_direct(raw: Mapping[str, object] | None) -> WindowUsage:
    """Parse window where used_percent is already 0-100 - used by ChatGPT."""
    raw = raw or {}
    used = raw.get("used_percent") or 0
    reset_at = raw.get("reset_at")

    try:
        used_f = float(used)
    except Exception:
        used_f = 0.0

    return WindowUsage(utilization=used_f, resets_at=reset_at)  # type: ignore[arg-type]


def format_eta(reset_at: str | int | None) -> str:
    """Format ETA from ISO string or Unix timestamp -> '4h19′' or '19′30″'."""
    if not reset_at:
        return "0′00″"

    try:
        # Handle both ISO string and Unix timestamp
        if isinstance(reset_at, str):
            if reset_at.endswith('Z'):
                reset_at = reset_at[:-1] + '+00:00'
            reset_dt = datetime.fromisoformat(reset_at)
        else:
            reset_dt = datetime.fromtimestamp(reset_at, tz=timezone.utc)

        now = datetime.now(timezone.utc)
        delta = reset_dt - now
    except Exception:
        return "??′??″"

    secs = int(delta.total_seconds())
    if secs <= 0:
        return "0m00s"

    # Show days+hours if > 24 hours
    if secs >= 86400:  # 24 * 3600
        days = secs // 86400
        hours = (secs % 86400) // 3600
        return f"{days}d{hours:02}h"

    # Show hours+minutes if > 1 hour
    if secs >= 3600:
        hours = secs // 3600
        mins = (secs % 3600) // 60
        return f"{hours}h{mins:02}m"

    # Show minutes+seconds
    mins = secs // 60
    secs_rem = secs % 60
    return f"{mins}m{secs_rem:02}s"


def format_output(format_string: str, data: dict) -> str:
    """
    Format output using a template string with placeholders.

    Available placeholders:
    - {5h_pct} - 5-hour utilization percentage (no decimals)
    - {7d_pct} - 7-day utilization percentage (no decimals)
    - {5h_reset} - 5-hour reset time (formatted)
    - {7d_reset} - 7-day reset time (formatted)
    - {icon} - service icon
    - {time_icon} - time icon
    - {status} - status text (Ready, Pause, or empty)
    - {pct} - active window percentage
    - {reset} - active window reset time

    Conditional sections:
    - {?5h_reset}...{/5h_reset} - show content only if 5h_reset is not "Not started"
    - {?7d_reset}...{/7d_reset} - show content only if 7d_reset is not "Not started"
    - {?5h_reset&7d_reset}...{/} - show content only if both are not "Not started"

    Example:
        format_output("{icon} {5h_pct}% {time_icon} {5h_reset}", data)
        format_output("{?5h_reset}{5h_pct}/{5h_reset}{/5h_reset}{?5h_reset&7d_reset} - {/}{?7d_reset}{7d_pct}/{7d_reset}{/7d_reset}", data)
    """
    import re
    
    # Process conditional blocks with multiple variables: {?var1&var2&...}content{/}
    def replace_multi_conditional(match):
        var_names = match.group(1).split('&')
        content = match.group(2)
        # Check if all variables exist and are not "Not started"
        all_valid = all(data.get(v.strip(), "") and data.get(v.strip(), "") != "Not started" for v in var_names)
        if all_valid:
            return content.format(**data)
        return ""
    
    # Replace multi-variable conditional blocks first: {?var1&var2}content{/}
    result = re.sub(r'\{\?([^}]+&[^}]+)\}(.*?)\{/\}', replace_multi_conditional, format_string)
    
    # Process single variable conditional blocks: {?var}content{/var}
    def replace_conditional(match):
        var_name = match.group(1)
        content = match.group(2)
        value = data.get(var_name, "")
        # Show content only if value exists and is not "Not started"
        if value and value != "Not started":
            return content.format(**data)
        return ""
    
    # Replace single-variable conditional blocks: {?var}content{/var}
    result = re.sub(r'\{\?(\w+)\}(.*?)\{/\1\}', replace_conditional, result)
    
    # Replace remaining placeholders
    return result.format(**data)

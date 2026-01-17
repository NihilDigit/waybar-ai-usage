from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import json5

DEFAULT_CONFIG = Path("~/.config/waybar/config.jsonc").expanduser()
DEFAULT_STYLE = Path("~/.config/waybar/style.css").expanduser()

TEMPLATE_CONFIG = """// Waybar Configuration Example
// Add this configuration to the modules section of ~/.config/waybar/config.jsonc
//
// After installing with: uv tool install waybar-ai-usage
// Or for development mode, use the full path with uv run

{
  // Claude Code Usage Monitor
  "custom/claude-usage": {
    // After 'uv tool install waybar-ai-usage':
    // IMPORTANT: Use full path to work with systemd-launched Waybar
    "exec": "~/.local/bin/claude-usage --waybar",
    // Example for Chromium:
    // "exec": "~/.local/bin/claude-usage --waybar --browser chromium",

    // Or for development mode:
    // "exec": "uv run --directory /home/YOUR_USER/Codes/waybar-ai-usage python claude.py --waybar",

    "return-type": "json",
    "interval": 120,  // Refresh every 2 minutes
    "format": "{}",
    "tooltip": true,
    "on-click": "pkill -RTMIN+8 waybar",  // Click to refresh immediately
    "signal": 8  // Refresh when receiving signal 8
  },

  // OpenAI Codex CLI Usage Monitor
  "custom/codex-usage": {
    // After 'uv tool install waybar-ai-usage':
    // IMPORTANT: Use full path to work with systemd-launched Waybar
    "exec": "~/.local/bin/codex-usage --waybar",
    // Example for Chromium:
    // "exec": "~/.local/bin/codex-usage --waybar --browser chromium",

    // Or for development mode:
    // "exec": "uv run --directory /home/YOUR_USER/Codes/waybar-ai-usage python codex.py --waybar",

    "return-type": "json",
    "interval": 120,  // Refresh every 2 minutes
    "format": "{}",
    "tooltip": true,
    "on-click": "pkill -RTMIN+9 waybar",  // Click to refresh immediately
    "signal": 9  // Refresh when receiving signal 9
  }
}
"""

TEMPLATE_STYLE = """/* Claude Code Usage Monitor Styling */
#custom-claude-usage {
  padding: 0 8px;
  margin: 0 4px;
  border-radius: 4px;
  background: transparent;
  font-family: 'Adwaita Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  transition: all 0.3s ease;
}

/* Hover effect: show clickable */
#custom-claude-usage:hover {
  background: rgba(222, 115, 86, 0.15);
}

/* Color-coded by usage level */
#custom-claude-usage.claude-low {
  color: #a6e3a1;  /* Green: low usage (0-49%) */
}

#custom-claude-usage.claude-mid {
  color: #f9e2af;  /* Yellow: medium usage (50-79%) */
}

#custom-claude-usage.claude-high {
  color: #f38ba8;  /* Red: high usage (80-99%) */
}

/* OpenAI Codex CLI Usage Monitor Styling */
#custom-codex-usage {
  padding: 0 8px;
  margin: 0 4px;
  border-radius: 4px;
  background: transparent;
  font-family: 'Adwaita Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  transition: all 0.3s ease;
}

#custom-codex-usage:hover {
  background: rgba(116, 170, 156, 0.15);
}

#custom-codex-usage.codex-low {
  color: #a6e3a1;  /* Green: low usage */
}

#custom-codex-usage.codex-mid {
  color: #f9e2af;  /* Yellow: medium usage */
}

#custom-codex-usage.codex-high {
  color: #f38ba8;  /* Red: high usage */
}

/* Error state (network failures, auth errors, etc.) */
#custom-claude-usage.critical,
#custom-codex-usage.critical {
  color: #ff5555;
  background: rgba(255, 85, 85, 0.1);
}
"""


def _confirm_changes(paths: Iterable[Path]) -> bool:
    print("Note: this will rewrite your Waybar config; formatting/comments may change.")
    print("This will modify the following files:")
    for path in paths:
        print(f"- {path}")
    answer = input("Proceed? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def _find_style_region(lines: list[str]) -> tuple[int, int] | None:
    start_marker = "/* Claude Code Usage Monitor Styling */"
    end_marker = "/* Error state (network failures, auth errors, etc.) */"
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if start_idx is None and start_marker in line:
            start_idx = i
        if end_marker in line:
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        return None

    depth = 0
    for j in range(end_idx, len(lines)):
        depth += lines[j].count("{") - lines[j].count("}")
        if depth <= 0 and "}" in lines[j]:
            end_idx = j + 1
            break
    else:
        end_idx = end_idx + 1

    return start_idx, end_idx


def _extract_style_region(lines: list[str]) -> list[str]:
    region = _find_style_region(lines)
    if region is None:
        return []
    start_idx, end_idx = region
    return lines[start_idx:end_idx]


def _apply_style_region(lines: list[str], region_lines: list[str]) -> list[str]:
    if not region_lines:
        return lines[:]
    region = _find_style_region(lines)
    out = list(lines)
    if region is None:
        if out and out[-1].strip():
            out.append("")
        out.extend(region_lines)
        return out
    start_idx, end_idx = region
    return out[:start_idx] + region_lines + out[end_idx:]


def _remove_style_blocks(lines: list[str]) -> list[str]:
    region = _find_style_region(lines)
    if region is not None:
        start_idx, end_idx = region
        return lines[:start_idx] + lines[end_idx:]

    targets = ("#custom-claude-usage", "#custom-codex-usage")
    out: list[str] = []
    skipping = False
    depth = 0

    for line in lines:
        if not skipping and any(t in line for t in targets):
            skipping = True
            depth = line.count("{") - line.count("}")
            if depth == 0 and "{" not in line:
                depth = 0
            continue

        if skipping:
            depth += line.count("{") - line.count("}")
            if depth <= 0 and "}" in line:
                skipping = False
            continue

        out.append(line)

    return out


def _backup_file(path: Path) -> Path:
    ts = __import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak.{ts}")
    backup.write_text(path.read_text())
    return backup


def _load_json5(path: Path) -> dict:
    try:
        return json5.loads(path.read_text())
    except Exception as exc:
        raise RuntimeError(f"Failed to parse JSONC: {path} ({exc})") from exc


def _dump_json5(data: dict) -> str:
    return json5.dumps(data, indent=2)


def _read_template(path: Path, fallback: str) -> str:
    if path.exists():
        return path.read_text()
    return fallback


def _remove_config(config_path: Path, style_path: Path, dry_run: bool) -> None:
    if not config_path.exists():
        print(f"Config not found: {config_path}")
    else:
        config_data = _load_json5(config_path)
        changed = False
        modules_left = config_data.get("modules-left")
        if isinstance(modules_left, list):
            new_modules = [m for m in modules_left if m not in ("custom/claude-usage", "custom/codex-usage")]
            if new_modules != modules_left:
                config_data["modules-left"] = new_modules
                changed = True
        if "custom/claude-usage" in config_data:
            config_data.pop("custom/claude-usage", None)
            changed = True
        if "custom/codex-usage" in config_data:
            config_data.pop("custom/codex-usage", None)
            changed = True

        if changed:
            if dry_run:
                print(f"[dry-run] Would update: {config_path}")
            else:
                backup = _backup_file(config_path)
                print(f"Backup created: {backup}")
                config_path.write_text(_dump_json5(config_data) + "\n")
                print(f"Updated: {config_path}")
        else:
            print(f"No changes needed in: {config_path}")

    if not style_path.exists():
        print(f"Style not found: {style_path}")
    else:
        style_lines = style_path.read_text().splitlines()
        updated_style = _remove_style_blocks(style_lines)
        if updated_style != style_lines:
            if dry_run:
                print(f"[dry-run] Would update: {style_path}")
            else:
                backup = _backup_file(style_path)
                print(f"Backup created: {backup}")
                style_path.write_text("\n".join(updated_style) + "\n")
                print(f"Updated: {style_path}")
        else:
            print(f"No changes needed in: {style_path}")
    if not dry_run:
        print("Please restart Waybar to apply changes (e.g. `pkill waybar && waybar &`).")


def _apply_setup(config_path: Path, style_path: Path, browsers: list[str] | None, dry_run: bool) -> None:
    example_config = Path(__file__).with_name("waybar-config-example.jsonc")
    example_style = Path(__file__).with_name("waybar-style-example.css")
    style_lines = style_path.read_text().splitlines() if style_path.exists() else []

    example_config_text = _read_template(example_config, TEMPLATE_CONFIG)
    example_style_text = _read_template(example_style, TEMPLATE_STYLE)
    example_config_data = json5.loads(example_config_text)
    example_style_lines = example_style_text.splitlines()
    css_region = _extract_style_region(example_style_lines)

    if config_path.exists():
        config_data = _load_json5(config_path)
    else:
        config_data = {}

    changed_config = False
    modules_left = config_data.get("modules-left")
    if not isinstance(modules_left, list):
        modules_left = []
        config_data["modules-left"] = modules_left
        changed_config = True

    for name in ("custom/claude-usage", "custom/codex-usage"):
        if name not in modules_left:
            modules_left.append(name)
            changed_config = True

    for key in ("custom/claude-usage", "custom/codex-usage"):
        if key not in config_data and key in example_config_data:
            config_data[key] = example_config_data[key]
            changed_config = True

    if browsers:
        flags = " ".join(f"--browser {b}" for b in browsers)
        for key in ("custom/claude-usage", "custom/codex-usage"):
            entry = config_data.get(key)
            if isinstance(entry, dict):
                exec_cmd = entry.get("exec")
                if isinstance(exec_cmd, str) and "--waybar" in exec_cmd and "--browser" not in exec_cmd:
                    entry["exec"] = exec_cmd.replace("--waybar", f"--waybar {flags}")
                    changed_config = True

    updated_style = _apply_style_region(style_lines, css_region)

    changed_style = updated_style != style_lines

    if not changed_config and not changed_style:
        print("No changes needed.")
        return

    if dry_run:
        if changed_config:
            print(f"[dry-run] Would update: {config_path}")
        if changed_style:
            print(f"[dry-run] Would update: {style_path}")
        return

    backups: list[Path] = []
    if changed_config and config_path.exists():
        backups.append(_backup_file(config_path))
    if changed_style and style_path.exists():
        backups.append(_backup_file(style_path))

    if backups:
        print("Backups created:")
        for backup in backups:
            print(f"- {backup}")

    if changed_config:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(_dump_json5(config_data) + "\n")
        print(f"Updated: {config_path}")
    if changed_style:
        style_path.parent.mkdir(parents=True, exist_ok=True)
        style_path.write_text("\n".join(updated_style) + "\n")
        print(f"Updated: {style_path}")
    print("Please restart Waybar to apply changes (e.g. `pkill waybar && waybar &`).")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="waybar-ai-usage",
        description="Waybar AI Usage helper and setup tool",
    )
    subparsers = parser.add_subparsers(dest="command")

    setup = subparsers.add_parser(
        "setup",
        help="Add Waybar config entries and styles (with backups)",
    )
    setup.add_argument(
        "--browser",
        action="append",
        help="Browser cookie source to try (repeatable). Example: --browser chromium",
    )
    setup.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Waybar config path (default: ~/.config/waybar/config.jsonc)",
    )
    setup.add_argument(
        "--style",
        type=Path,
        default=DEFAULT_STYLE,
        help="Waybar style path (default: ~/.config/waybar/style.css)",
    )
    setup.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files",
    )
    setup.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    cleanup = subparsers.add_parser(
        "cleanup",
        help="Remove Waybar config entries and styles added for AI usage modules",
    )
    cleanup.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Waybar config path (default: ~/.config/waybar/config.jsonc)",
    )
    cleanup.add_argument(
        "--style",
        type=Path,
        default=DEFAULT_STYLE,
        help="Waybar style path (default: ~/.config/waybar/style.css)",
    )
    cleanup.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files",
    )
    cleanup.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    if args.command == "setup":
        if not args.yes and not args.dry_run:
            if not _confirm_changes([args.config.expanduser(), args.style.expanduser()]):
                print("Aborted.")
                return
        _apply_setup(args.config.expanduser(), args.style.expanduser(), args.browser, args.dry_run)
        return
    if args.command == "cleanup":
        if not args.yes and not args.dry_run:
            if not _confirm_changes([args.config.expanduser(), args.style.expanduser()]):
                print("Aborted.")
                return
        _remove_config(args.config.expanduser(), args.style.expanduser(), args.dry_run)
        return

    parser.print_help()


if __name__ == "__main__":
    main()

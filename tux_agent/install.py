"""Add or remove the tux-agent hooks in Claude Code's user settings (~/.claude/settings.json)."""

import json
import os
import shlex
import shutil
import sys
import time
from pathlib import Path

EVENTS = [
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PermissionRequest",
    "Notification", "SubagentStart", "Stop", "SessionEnd",
]
HOOK = Path(__file__).resolve().parent / "hook.py"
MARKER = "tux_agent/hook.py"


def settings_path() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"
    return Path(base) / "settings.json"


def _command() -> str:
    # -I -S: isolated, no site packages — the hook only needs the stdlib and starts faster.
    return f"{shlex.quote(sys.executable)} -I -S {shlex.quote(str(HOOK))}"


def _ours(hook: dict) -> bool:
    cmd = hook.get("command", "")
    return MARKER in cmd or "tux-hook.py" in cmd


def _strip(settings: dict) -> int:
    """Remove our hooks (current and older layouts); returns how many were removed."""
    removed = 0
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        kept_groups = []
        for group in hooks[event]:
            inner = [h for h in group.get("hooks", []) if not _ours(h)]
            removed += len(group.get("hooks", [])) - len(inner)
            if inner:
                kept_groups.append({**group, "hooks": inner})
        if kept_groups:
            hooks[event] = kept_groups
        else:
            del hooks[event]
    if "hooks" in settings and not settings["hooks"]:
        del settings["hooks"]
    return removed


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def _save(path: Path, settings: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(f"settings.json.tux-agent-{time.strftime('%Y%m%d-%H%M%S')}.bak")
        shutil.copy2(path, backup)
        print(f"backup: {backup}")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def install():
    path = settings_path()
    settings = _load(path)
    _strip(settings)
    hooks = settings.setdefault("hooks", {})
    entry = {"type": "command", "command": _command(), "async": True, "timeout": 5}
    for event in EVENTS:
        hooks.setdefault(event, []).append({"hooks": [dict(entry)]})
    _save(path, settings)
    print(f"tux-agent hooks installed in {path} ({len(EVENTS)} events)")
    print("New Claude Code sessions will show up in the office. / Yeni Claude Code oturumları ofiste görünecek.")


def uninstall():
    path = settings_path()
    settings = _load(path)
    removed = _strip(settings)
    if removed:
        _save(path, settings)
    print(f"removed {removed} tux-agent hook(s) from {path}")

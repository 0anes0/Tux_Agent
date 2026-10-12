"""Render docs/demo.gif: three scripted Claude Code sessions sharing the office.

    python3 tools/demo_gif.py [out.gif]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tux_agent.app import Scene, export_gif  # noqa: E402


def ev(session, event, tool=None, **extra):
    return {"session": session, "event": event, "tool": tool, "cwd": f"/home/me/{session}", "ts": 0, **extra}


SCRIPT = [
    (0.0, ev("api", "SessionStart")),
    (1.0, ev("api", "PreToolUse", "Read")),
    (1.5, ev("web-app", "SessionStart")),
    (3.0, ev("web-app", "PreToolUse", "WebSearch")),
    (6.0, ev("api", "PreToolUse", "Edit")),
    (6.5, ev("docs", "SessionStart")),
    (8.0, ev("docs", "PreToolUse", "Write")),
    (9.0, ev("web-app", "PreToolUse", "Bash")),
    (13.0, ev("web-app", "PermissionRequest", "Bash")),
    (14.0, ev("api", "PreToolUse", "Bash")),
    (17.0, ev("web-app", "PreToolUse", "Edit")),
    (18.0, ev("docs", "Stop")),
    (19.0, ev("api", "PreToolUse", "Edit")),
    (23.0, ev("api", "Stop")),
]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/demo.gif"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    # timestamps only need to increase per session
    script = [(t, {**e, "ts": t}) for t, e in SCRIPT]
    export_gif(out, seconds=26, scale=2, scene=Scene(demo=False), script=script)


if __name__ == "__main__":
    main()

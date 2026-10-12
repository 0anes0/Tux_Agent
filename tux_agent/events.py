"""Receive Claude Code hook events (see hooks/tux-hook.py) and map them to Tux activities."""

import json
import os
import socket


def socket_path() -> str:
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/tux-agent-{os.getuid()}"
    return os.path.join(base, "tux-agent.sock")


TOOL_ACTIVITY = {
    "Edit": "type", "Write": "type", "MultiEdit": "type", "NotebookEdit": "type",
    "Read": "read", "Grep": "read", "Glob": "read", "LS": "read",
    "Bash": "bash", "BashOutput": "bash", "KillShell": "bash", "PowerShell": "bash",
    "WebSearch": "web", "WebFetch": "web",
}


def activity_for(ev: dict) -> str | None:
    """The activity an event asks for, or None if the event shouldn't move Tux."""
    name = ev.get("event")
    if name in ("PreToolUse",):
        if ev.get("agent_id"):
            return None  # a subagent's tool call; subagents get their own Tux later (Faz 3)
        tool = ev.get("tool") or ""
        return TOOL_ACTIVITY.get(tool, "think")
    if name in ("SessionStart", "UserPromptSubmit", "SubagentStart"):
        return "think"
    if name == "PermissionRequest":
        return "wait"
    if name == "Notification":
        return "wait" if ev.get("notification") in ("permission_prompt", "elicitation_dialog", "agent_needs_input") else None
    if name == "Stop":
        return "rest"
    if name == "SessionEnd":
        return "leave"
    return None


class Listener:
    """Non-blocking Unix datagram socket; fileno() can go straight into select()."""

    def __init__(self, path: str | None = None):
        self.path = path or socket_path()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if os.path.exists(self.path):
            os.unlink(self.path)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(self.path)
        os.chmod(self.path, 0o600)
        self.sock.setblocking(False)

    def fileno(self) -> int:
        return self.sock.fileno()

    def drain(self) -> list[dict]:
        out = []
        while True:
            try:
                data = self.sock.recv(65536)
            except BlockingIOError:
                return out
            try:
                ev = json.loads(data)
            except ValueError:
                continue
            if isinstance(ev, dict) and ev.get("session"):
                out.append(ev)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self.sock.close()
        try:
            os.unlink(self.path)
        except OSError:
            pass

"""Receive Claude Code hook events (see hooks/tux-hook.py) and map them to Tux activities."""

import json
import os
import socket
import stat


def socket_path() -> str:
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/tux-agent-{os.getuid()}"
    return os.path.join(base, "tux-agent.sock")


def own_folder(path: str):
    """The /tmp fallback is shared with every user: another one could create the folder first
    and read the events (session ids, folder paths). Only use it if it is ours and private."""
    st = os.lstat(path)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        raise SystemExit(f"tux-agent: {path} is not a folder owned by you, not using it")
    if st.st_mode & 0o077:
        os.chmod(path, 0o700)  # made by an older version with the default umask


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
        folder = os.path.dirname(self.path)
        os.makedirs(folder, mode=0o700, exist_ok=True)
        if not os.environ.get("XDG_RUNTIME_DIR"):
            own_folder(folder)
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

#!/usr/bin/env python3
"""Claude Code hook: forward a trimmed copy of the event to a running tux-agent.

Never prints and always exits 0, so it can't affect Claude Code. If tux-agent
isn't running the datagram simply has nowhere to go.
"""

import json
import os
import socket
import sys
import time


def socket_path() -> str:
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/tux-agent-{os.getuid()}"
    return os.path.join(base, "tux-agent.sock")


def main():
    ts = time.time()
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    # Only what the office needs; tool_input can be huge (file contents) and private.
    event = {
        "ts": ts,
        "event": data.get("hook_event_name"),
        "session": data.get("session_id"),
        "cwd": data.get("cwd"),
        "tool": data.get("tool_name"),
        "agent_id": data.get("agent_id"),
        "agent_type": data.get("agent_type"),
        "notification": data.get("notification_type"),
    }
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.sendto(json.dumps(event).encode(), socket_path())
    except OSError:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)

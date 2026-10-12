"""Raw terminal I/O: alternate screen, size in cells and pixels, non-blocking key reads."""

import fcntl
import os
import select
import struct
import sys
import termios
import tty

KEYS = {
    b"\x1b[A": "up", b"\x1b[B": "down", b"\x1b[C": "right", b"\x1b[D": "left",
    b"\x1bOA": "up", b"\x1bOB": "down", b"\x1bOC": "right", b"\x1bOD": "left",
}


class Terminal:
    def __init__(self):
        self.fd_in = sys.stdin.fileno()
        self.fd_out = sys.stdout.fileno()
        self.rows = self.cols = self.xpx = self.ypx = 0
        self.refresh_size()

    def __enter__(self):
        self._saved = termios.tcgetattr(self.fd_in)
        tty.setcbreak(self.fd_in)
        self.write(b"\x1b[?1049h\x1b[?25l\x1b[2J")
        return self

    def __exit__(self, *exc):
        self.write(b"\x1b_Ga=d,d=A,q=2\x1b\\\x1b[0m\x1b[2J\x1b[?25h\x1b[?1049l")
        termios.tcsetattr(self.fd_in, termios.TCSADRAIN, self._saved)

    def write(self, data: bytes):
        view = memoryview(data)
        while view:
            n = os.write(self.fd_out, view)
            view = view[n:]

    def refresh_size(self):
        packed = fcntl.ioctl(self.fd_out, termios.TIOCGWINSZ, b"\0" * 8)
        self.rows, self.cols, self.xpx, self.ypx = struct.unpack("HHHH", packed)

    def cell_px(self) -> tuple[int, int]:
        if self.xpx and self.ypx:
            return self.xpx // self.cols, self.ypx // self.rows
        return 10, 20  # terminal didn't report pixels; a typical guess

    def supports_kitty(self) -> bool:
        env = os.environ
        return (
            env.get("TERM") == "xterm-kitty"
            or "KITTY_WINDOW_ID" in env
            or env.get("TERM_PROGRAM") in ("WezTerm", "ghostty")
        ) and "TMUX" not in env

    def keys(self, timeout: float, wake=()) -> list[str]:
        """Keys pressed within timeout; returns early when any `wake` fd becomes readable."""
        ready, _, _ = select.select([self.fd_in, *wake], [], [], max(0.0, timeout))
        if self.fd_in not in ready:
            return []
        data = os.read(self.fd_in, 1024)
        out = []
        i = 0
        while i < len(data):
            for seq, name in KEYS.items():
                if data.startswith(seq, i):
                    out.append(name)
                    i += len(seq)
                    break
            else:
                ch = data[i : i + 1]
                out.append("esc" if ch == b"\x1b" else ch.decode(errors="ignore"))
                i += 1
        return out

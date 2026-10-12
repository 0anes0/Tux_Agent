"""Turn an RGBA frame into terminal output.

kitty     — Kitty graphics protocol: real pixels, integer-scaled, zlib-compressed.
halfblock — '▀' with truecolor fg/bg (2 pixels per cell); shows a viewport that follows a point.
"""

import base64
import zlib

from PIL import Image

ESC = b"\x1b"


class Kitty:
    name = "kitty"
    CHUNK = 4096

    def __init__(self):
        self.ids = (1, 2)
        self.flip = 0
        self.last: bytes | None = None
        self.size = None

    def frame(self, img: Image.Image, term, focus) -> tuple[bytes, int]:
        """Returns (escape bytes, first free terminal row below the image)."""
        cell_w, cell_h = term.cell_px()
        avail_w = term.cols * cell_w
        avail_h = (term.rows - 1) * cell_h  # keep one line for the status bar
        # Fill the space: fractional nearest-neighbour scaling (pixels become 2-3 px wide
        # instead of dropping from 5x to 2x when the window is halved).
        scale = max(1.0, min(avail_w / img.width, avail_h / img.height))
        w, h = int(img.width * scale), int(img.height * scale)
        img_rows = -(-h // cell_h)
        col = max(0, (term.cols - (-(-w // cell_w))) // 2) + 1

        rgb = img.convert("RGB")
        raw = rgb.tobytes()
        if raw == self.last and self.size == (w, h, col):
            return b"", img_rows + 1
        self.last, self.size = raw, (w, h, col)
        if scale > 1:
            rgb = rgb.resize((w, h), Image.NEAREST)

        payload = base64.standard_b64encode(zlib.compress(rgb.tobytes(), 1))
        new_id = self.ids[self.flip]
        old_id = self.ids[1 - self.flip]
        self.flip = 1 - self.flip

        out = [b"\x1b[1;%dH" % col]
        for i in range(0, len(payload), self.CHUNK):
            more = int(i + self.CHUNK < len(payload))
            if i == 0:
                ctrl = b"a=T,f=24,o=z,s=%d,v=%d,i=%d,q=2,C=1,m=%d" % (w, h, new_id, more)
            else:
                ctrl = b"m=%d" % more
            out.append(ESC + b"_G" + ctrl + b";" + payload[i : i + self.CHUNK] + ESC + b"\\")
        # place the new image first, then drop the old one: no flicker
        out.append(ESC + b"_Ga=d,d=I,i=%d,q=2" % old_id + ESC + b"\\")
        return b"".join(out), img_rows + 1

    def reset(self) -> bytes:
        self.last = None
        return ESC + b"_Ga=d,d=A,q=2" + ESC + b"\\"


class HalfBlock:
    name = "halfblock"

    def __init__(self):
        self.lines: list[bytes] = []

    def frame(self, img: Image.Image, term, focus) -> tuple[bytes, int]:
        vw = min(img.width, term.cols)
        vh = min(img.height, (term.rows - 1) * 2) // 2 * 2
        fx, fy = focus
        x0 = int(min(max(fx - vw / 2, 0), img.width - vw))
        y0 = int(min(max(fy - vh / 2, 0), img.height - vh))
        px = img.convert("RGB").crop((x0, y0, x0 + vw, y0 + vh)).load()

        col0 = (term.cols - vw) // 2 + 1
        out = []
        lines = []
        for row in range(vh // 2):
            parts = []
            prev = None
            for x in range(vw):
                top, bot = px[x, row * 2], px[x, row * 2 + 1]
                if (top, bot) != prev:
                    parts.append(b"\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm" % (*top, *bot))
                    prev = (top, bot)
                parts.append("▀".encode())
            line = b"".join(parts)
            lines.append(line)
            if row >= len(self.lines) or self.lines[row] != line:
                out.append(b"\x1b[%d;%dH" % (row + 1, col0) + line + b"\x1b[0m")
        self.lines = lines
        return b"".join(out), vh // 2 + 1

    def reset(self) -> bytes:
        self.lines = []
        return b""


def pick(name: str | None, term) -> "Kitty | HalfBlock":
    if name == "kitty":
        return Kitty()
    if name == "halfblock":
        return HalfBlock()
    return Kitty() if term.supports_kitty() else HalfBlock()

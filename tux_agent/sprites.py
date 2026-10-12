"""Tux sprite sheet (Kyrodian Legends style, CC-BY-SA 4.0) and the animations cut from it."""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SHEET = ASSETS / "sprites" / "tux.png"
CELL = 32
# Feet touch the bottom edge of every cell, horizontally centred.
ANCHOR = (16, 32)

# name: (cells as (row, col), frames per second). Side views face right;
# the matching *_left animations are mirrored automatically.
ANIMS = {
    "idle_down": ([(5, 0)] * 14 + [(5, 1)], 6),
    "idle_up": ([(5, 3)], 1),
    "idle_right": ([(0, 0)], 1),
    "walk_right": ([(2, c) for c in range(8)], 12),
    "walk_up": ([(5, c) for c in range(4, 8)], 8),
    "walk_down": ("derived", 8),
    "type": ([(5, 3), (5, 5)], 5),
    "read_right": ([(9, 5), (9, 6), (9, 7), (9, 6)], 3),
    "sit": ([(6, 3)] * 10 + [(6, 2)] * 3, 4),
    "wave": ([(5, 0), (5, 2)], 3),
    "tinker": ([(5, 3), (5, 4), (5, 3), (5, 7)], 4),
}


@dataclass
class Anim:
    frames: list[Image.Image]
    fps: float

    def at(self, t: float) -> Image.Image:
        return self.frames[int(t * self.fps) % len(self.frames)]


class Sprites:
    def __init__(self, path: Path = SHEET):
        self.sheet = Image.open(path).convert("RGBA")
        self.anims: dict[str, Anim] = {}
        for name, (cells, fps) in ANIMS.items():
            if cells == "derived":
                frames = self._walk_down()
            else:
                frames = [self.cell(r, c) for r, c in cells]
            self.anims[name] = Anim(frames, fps)
            if name.endswith("_right"):
                left = name.removesuffix("_right") + "_left"
                self.anims[left] = Anim([ImageOps.mirror(f) for f in frames], fps)

    def cell(self, row: int, col: int) -> Image.Image:
        x, y = col * CELL, row * CELL
        return self.sheet.crop((x, y, x + CELL, y + CELL))

    def _walk_down(self) -> list[Image.Image]:
        # The sheet has no front-facing walk, so lift one foot at a time from the front idle frame.
        base = self.cell(5, 0)
        foot_top = _foot_top(base)

        def lift(left: bool) -> Image.Image:
            box = (0, foot_top, CELL // 2, CELL) if left else (CELL // 2, foot_top, CELL, CELL)
            out = base.copy()
            foot = base.crop(box)
            out.paste((0, 0, 0, 0), box)
            out.alpha_composite(foot, (box[0], box[1] - 2))
            return out

        return [base, lift(True), base, lift(False)]

    def get(self, name: str) -> Anim:
        return self.anims[name]


def _foot_top(img: Image.Image) -> int:
    """Row of the outline just above the yellow feet."""
    px = img.load()
    rows = [y for y in range(CELL // 2, CELL) if any(_is_foot(px[x, y]) for x in range(CELL))]
    return min(rows) - 1 if rows else CELL - 4


def _is_foot(p) -> bool:
    r, g, b, a = p
    return a > 0 and r > 180 and g > 120 and b < 90

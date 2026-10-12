"""The office: hand-drawn (in code) pixel background, y-sorted props, walk grid and spots."""

import random
from collections import deque
from dataclasses import dataclass
from typing import Callable

from PIL import Image, ImageDraw

TILE = 16
COLS, ROWS = 20, 12
WIDTH, HEIGHT = COLS * TILE, ROWS * TILE
WALL_ROWS = 2
WALL_H = WALL_ROWS * TILE

Tile = tuple[int, int]
# (sort_y, draw) — props and characters are painted back to front by sort_y.
Drawable = tuple[float, Callable[[Image.Image], None]]

C = {
    "wall": (58, 66, 94), "wall_hi": (70, 80, 112), "wall_trim": (40, 44, 64),
    "wainscot": (84, 72, 64), "wainscot_hi": (100, 86, 76), "base": (36, 30, 30),
    "floor_a": (154, 108, 70), "floor_b": (142, 98, 62), "floor_seam": (112, 76, 48),
    "shadow": (0, 0, 0, 60),
    "wood": (120, 78, 44), "wood_hi": (150, 100, 58), "wood_dk": (84, 52, 30),
    "metal": (46, 50, 62), "metal_hi": (70, 76, 92), "metal_dk": (28, 30, 38),
    "glass": (126, 186, 232), "glass_hi": (196, 228, 248), "frame": (222, 222, 232),
    "white": (236, 238, 242), "screen_off": (24, 30, 40), "screen_on": (20, 34, 46),
    "chair": (52, 74, 120), "chair_hi": (72, 98, 150), "chair_dk": (34, 48, 82),
    "leaf": (64, 150, 80), "leaf_hi": (98, 190, 104), "leaf_dk": (40, 104, 58),
    "pot": (186, 96, 64), "pot_dk": (140, 66, 44),
    "rug": (150, 58, 66), "rug_hi": (196, 92, 88), "rug_dk": (112, 40, 50),
    "led_g": (90, 240, 120), "led_a": (250, 190, 60), "led_r": (240, 80, 80),
}
CODE_COLORS = [(122, 200, 255), (250, 200, 90), (150, 230, 140), (230, 140, 220), (220, 220, 230)]


@dataclass(frozen=True)
class Spot:
    tile: Tile
    facing: str  # up | down | left | right
    dx: int = 0  # pixel nudge after arriving (desks span two tiles)


@dataclass(frozen=True)
class Desk:
    col: int  # left tile of a 2-tile desk
    row: int

    @property
    def seat(self) -> Spot:
        return Spot((self.col, self.row + 1), "up", dx=TILE // 2)


def feet(tile: Tile) -> tuple[float, float]:
    """Pixel position of a character's feet standing on a tile."""
    c, r = tile
    return c * TILE + TILE / 2, r * TILE + 12


def tile_at(x: float, y: float) -> Tile:
    return int(x // TILE), int(y // TILE)


class Office:
    def __init__(self):
        self.desks = [Desk(c, r) for r in (4, 8) for c in (7, 11, 15)]
        self.spots = {
            "door": Spot((3, 2), "down"),
            "shelf": Spot((1, 3), "right"),
            "window": Spot((5, 3), "up"),
            "coffee": Spot((13, 3), "up"),
            "rack": Spot((17, 3), "up"),
            "rug": Spot((3, 9), "down"),
        }
        self.blocked: set[Tile] = {(c, r) for r in range(WALL_ROWS) for c in range(COLS)}
        self.blocked |= {(0, 2), (1, 2), (2, 2), (13, 2), (17, 2), (18, 2), (19, 2), (0, 11)}
        for d in self.desks:
            self.blocked |= {(d.col, d.row), (d.col + 1, d.row)}
        self.background = self._draw_background()

    # --- navigation -------------------------------------------------------

    def walkable(self, t: Tile) -> bool:
        c, r = t
        return 0 <= c < COLS and 0 <= r < ROWS and t not in self.blocked

    def path(self, start: Tile, goal: Tile) -> list[Tile]:
        """BFS over the tile grid; returns tiles from start to goal inclusive, or [] if unreachable."""
        prev: dict[Tile, Tile | None] = {start: None}
        queue = deque([start])
        while queue:
            cur = queue.popleft()
            if cur == goal:
                out = []
                while cur is not None:
                    out.append(cur)
                    cur = prev[cur]
                return out[::-1]
            c, r = cur
            for nxt in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                if nxt not in prev and (self.walkable(nxt) or nxt == goal):
                    prev[nxt] = cur
                    queue.append(nxt)
        return []

    # --- dynamic props ----------------------------------------------------

    def props(self, t: float, typing: set[Desk]) -> list[Drawable]:
        out: list[Drawable] = []
        for d in self.desks:
            x0, y0 = d.col * TILE, d.row * TILE
            out.append((y0 + TILE, lambda img, x0=x0, y0=y0, on=d in typing: _desk(img, x0, y0, on, t)))
            sx, sy = feet(d.seat.tile)
            sx += d.seat.dx
            out.append((sy + 0.5, lambda img, sx=sx, sy=sy: _chair(img, sx, sy)))
        out.append((0, lambda img: _rack_leds(img, 17 * TILE, t)))
        return out

    # --- static background ------------------------------------------------

    def _draw_background(self) -> Image.Image:
        img = Image.new("RGBA", (WIDTH, HEIGHT), C["floor_a"] + (255,))
        d = ImageDraw.Draw(img)
        rng = random.Random(7)

        # floor planks: 8px tall rows, staggered seams
        for y in range(WALL_H, HEIGHT, 8):
            row = (y - WALL_H) // 8
            d.rectangle([0, y, WIDTH, y + 7], fill=C["floor_a"] if row % 2 else C["floor_b"])
            d.line([0, y + 7, WIDTH, y + 7], fill=C["floor_seam"])
            for x in range((row * 13) % 40 - 40, WIDTH, 40):
                d.line([x, y, x, y + 6], fill=C["floor_seam"])
            for _ in range(6):
                gx = rng.randrange(WIDTH)
                d.line([gx, y + 3, gx + rng.randrange(3, 9), y + 3], fill=C["floor_b"] if row % 2 else C["floor_a"])

        # back wall
        d.rectangle([0, 0, WIDTH, WALL_H - 1], fill=C["wall"])
        for x in range(0, WIDTH, 8):
            d.line([x, 3, x, WALL_H - 12], fill=C["wall_hi"])
        d.rectangle([0, 0, WIDTH, 2], fill=C["wall_trim"])
        d.rectangle([0, WALL_H - 11, WIDTH, WALL_H - 3], fill=C["wainscot"])
        d.line([0, WALL_H - 11, WIDTH, WALL_H - 11], fill=C["wainscot_hi"])
        d.rectangle([0, WALL_H - 2, WIDTH, WALL_H - 1], fill=C["base"])
        # soft shadow where wall meets floor
        shadow = Image.new("RGBA", (WIDTH, 3), C["shadow"])
        img.alpha_composite(shadow, (0, WALL_H))

        _window(d, 5 * TILE + 2, 4)
        _window(d, 15 * TILE + 2, 4)
        _whiteboard(d, 8 * TILE + 2, 3, rng)
        _clock(d, 12 * TILE + 8, 9)
        _door(d, 3 * TILE + 1, 2)
        _rug(d, 1 * TILE + 4, 7 * TILE + 6, 5 * TILE - 8, 4 * TILE - 10)
        _beanbag(d, 2 * TILE + 2, 9 * TILE + 2)

        # wall-standing furniture (row 2, reaching up into the wall)
        _bookshelf(d, 1 * TILE, 2 * TILE + TILE - 1, rng)
        _counter(d, 13 * TILE, 2 * TILE + TILE - 1)
        _rack(d, 17 * TILE + 2, 2 * TILE + TILE - 1)
        _plant(img, 0 * TILE + 8, 2 * TILE + 14)
        _plant(img, 19 * TILE + 8, 2 * TILE + 14)
        _plant(img, 0 * TILE + 8, 11 * TILE + 14)
        return img


# --- drawing helpers (x, y are top-left unless noted; "bottom" means feet line) ---

def _window(d, x, y):
    w, h = 24, 18
    d.rectangle([x - 1, y - 1, x + w, y + h], fill=C["frame"])
    d.rectangle([x + 1, y + 1, x + w - 2, y + h - 2], fill=C["glass"])
    d.line([x + w // 2, y, x + w // 2, y + h - 1], fill=C["frame"])
    d.line([x, y + h // 2, x + w - 1, y + h // 2], fill=C["frame"])
    d.line([x + 2, y + 6, x + 6, y + 2], fill=C["glass_hi"])
    d.line([x + 15, y + 15, x + 20, y + 10], fill=C["glass_hi"])
    d.rectangle([x - 2, y + h, x + w + 1, y + h + 1], fill=C["frame"])


def _whiteboard(d, x, y, rng):
    w, h = 60, 22
    d.rectangle([x - 1, y - 1, x + w, y + h], fill=C["metal_hi"])
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=C["white"])
    for i, col in enumerate([(60, 110, 200), (200, 70, 70), (60, 150, 90)]):
        yy = y + 4 + i * 6
        xx = x + 4
        while xx < x + w - 8:
            seg = rng.randrange(3, 10)
            d.line([xx, yy, xx + seg, yy + rng.choice((0, 0, 1))], fill=col)
            xx += seg + 3
    d.rectangle([x + 4, y + h, x + w - 5, y + h + 1], fill=C["metal"])


def _clock(d, cx, cy):
    d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=C["metal_dk"])
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=C["white"])
    d.line([cx, cy, cx, cy - 4], fill=C["metal_dk"])
    d.line([cx, cy, cx + 3, cy], fill=C["metal_dk"])


def _door(d, x, y):
    d.rectangle([x - 1, y - 1, x + 14, WALL_H - 1], fill=C["wood_dk"])
    d.rectangle([x + 1, y + 1, x + 12, WALL_H - 1], fill=C["wood"])
    d.rectangle([x + 3, y + 4, x + 10, y + 12], fill=C["wood_hi"])
    d.rectangle([x + 3, y + 16, x + 10, y + 24], fill=C["wood_hi"])
    d.point([x + 10, y + 15], fill=(230, 200, 90))


def _rug(d, x, y, w, h):
    d.rounded_rectangle([x, y, x + w, y + h], radius=4, fill=C["rug_dk"])
    d.rounded_rectangle([x + 2, y + 2, x + w - 2, y + h - 2], radius=3, fill=C["rug"])
    d.rounded_rectangle([x + 5, y + 5, x + w - 5, y + h - 5], radius=2, outline=C["rug_hi"])
    for xx in range(x + 9, x + w - 8, 6):
        d.point([xx, y + h // 2], fill=C["rug_hi"])


def _beanbag(d, x, y):
    d.ellipse([x, y + 2, x + 20, y + 14], fill=(54, 120, 120))
    d.ellipse([x + 3, y, x + 15, y + 8], fill=(70, 150, 148))
    d.arc([x + 5, y + 2, x + 13, y + 7], 200, 340, fill=(110, 190, 186))


def _bookshelf(d, x, bottom, rng):
    w, h = 32, 40
    top = bottom - h
    d.rectangle([x, top, x + w - 1, bottom], fill=C["wood_dk"])
    d.rectangle([x + 2, top + 2, x + w - 3, bottom - 2], fill=C["wood"])
    for sy in range(top + 3, bottom - 4, 12):
        bx = x + 3
        while bx < x + w - 5:
            bw = rng.choice((2, 2, 3))
            bh = rng.randrange(7, 10)
            col = rng.choice([(200, 70, 70), (70, 120, 200), (230, 190, 80), (90, 170, 110), (180, 110, 200), (230, 230, 220)])
            d.rectangle([bx, sy + 10 - bh, bx + bw - 1, sy + 9], fill=col)
            bx += bw + rng.choice((0, 0, 1))
        d.rectangle([x + 2, sy + 10, x + w - 3, sy + 11], fill=C["wood_hi"])


def _counter(d, x, bottom):
    d.rectangle([x, bottom - 14, x + 15, bottom], fill=C["wood_dk"])
    d.rectangle([x, bottom - 15, x + 15, bottom - 13], fill=C["wood_hi"])
    d.rectangle([x + 1, bottom - 11, x + 14, bottom - 1], fill=C["wood"])
    # coffee machine
    d.rectangle([x + 3, bottom - 31, x + 12, bottom - 15], fill=C["metal_dk"])
    d.rectangle([x + 4, bottom - 30, x + 11, bottom - 26], fill=C["metal_hi"])
    d.point([x + 10, bottom - 28], fill=C["led_r"])
    d.rectangle([x + 6, bottom - 20, x + 9, bottom - 16], fill=C["white"])


def _rack(d, x, bottom):
    w, h = 28, 44
    top = bottom - h
    d.rectangle([x, top, x + w - 1, bottom], fill=C["metal_dk"])
    d.rectangle([x + 2, top + 2, x + w - 3, bottom - 2], fill=C["metal"])
    for sy in range(top + 4, bottom - 4, 6):
        d.rectangle([x + 3, sy, x + w - 4, sy + 4], fill=C["metal_hi"])
        d.line([x + 4, sy + 2, x + 14, sy + 2], fill=C["metal_dk"])


def _rack_leds(img, x, t):
    d = ImageDraw.Draw(img)
    bottom = 3 * TILE - 1
    top = bottom - 44
    for i, sy in enumerate(range(top + 4, bottom - 4, 6)):
        for j, col in enumerate((C["led_g"], C["led_a"], C["led_g"])):
            on = (int(t * (3 + i % 3) + i * 1.7 + j * 2.3) % 4) != 0
            d.point([x + 2 + 18 + j * 2, sy + 2], fill=col if on else C["metal_dk"])


def _plant(img, cx, bottom):
    d = ImageDraw.Draw(img)
    d.polygon([(cx - 5, bottom - 8), (cx + 5, bottom - 8), (cx + 4, bottom), (cx - 4, bottom)], fill=C["pot"])
    d.line([cx - 5, bottom - 8, cx + 5, bottom - 8], fill=C["pot_dk"])
    for dx, dy, col in [(-5, -16, "leaf_dk"), (3, -18, "leaf_dk"), (-2, -21, "leaf"), (4, -13, "leaf"),
                        (-6, -11, "leaf"), (0, -15, "leaf_hi"), (-3, -24, "leaf_hi")]:
        d.ellipse([cx + dx - 3, bottom + dy - 2, cx + dx + 3, bottom + dy + 3], fill=C[col])


def _desk(img, x, y, on, t):
    """2-tile desk standing on tile row y; monitor faces the viewer (chair is south)."""
    d = ImageDraw.Draw(img)
    w = 2 * TILE
    # legs + front panel
    d.rectangle([x + 1, y + 6, x + w - 2, y + 14], fill=C["wood_dk"])
    d.rectangle([x + 2, y + 7, x + w - 3, y + 13], fill=C["wood"])
    d.line([x + 2, y + 15, x + 2, y + 15], fill=C["wood_dk"])
    d.line([x + w - 3, y + 15, x + w - 3, y + 15], fill=C["wood_dk"])
    # top surface
    d.rectangle([x, y + 1, x + w - 1, y + 6], fill=C["wood_hi"])
    d.line([x, y + 6, x + w - 1, y + 6], fill=C["wood_dk"])
    # monitor
    mx, my = x + 7, y - 12
    d.rectangle([mx, my, mx + 17, my + 12], fill=C["metal_dk"])
    d.rectangle([mx + 1, my + 1, mx + 16, my + 11], fill=C["screen_on"] if on else C["screen_off"])
    if on:
        scroll = int(t * 6)
        rng = random.Random()
        for i in range(5):
            line = scroll + i
            rng.seed(line * 7919 + x)
            indent = rng.choice((0, 0, 2, 4))
            length = rng.randrange(3, 12 - indent)
            col = CODE_COLORS[line % len(CODE_COLORS)]
            d.line([mx + 2 + indent, my + 2 + i * 2, mx + 2 + indent + length, my + 2 + i * 2], fill=col)
        if int(t * 3) % 2:
            d.point([mx + 3, my + 10], fill=C["white"])
    else:
        d.line([mx + 2, my + 2, mx + 5, my + 2], fill=(40, 52, 68))
    d.rectangle([mx + 7, my + 13, mx + 10, my + 14], fill=C["metal"])
    d.rectangle([mx + 5, my + 15, mx + 12, my + 15], fill=C["metal_dk"])
    # mug
    d.rectangle([x + 27, y + 1, x + 29, y + 4], fill=C["white"])
    d.point([x + 30, y + 2], fill=C["white"])


def _chair(img, cx, feet_y):
    """Office chair seen from behind; drawn in front of a seated Tux."""
    d = ImageDraw.Draw(img)
    cx = int(cx)
    y = int(feet_y)
    d.rounded_rectangle([cx - 7, y - 8, cx + 6, y - 2], radius=2, fill=C["chair_dk"])
    d.rounded_rectangle([cx - 6, y - 7, cx + 5, y - 3], radius=1, fill=C["chair"])
    d.line([cx - 4, y - 6, cx + 3, y - 6], fill=C["chair_hi"])
    d.rectangle([cx - 1, y - 2, cx, y + 1], fill=C["metal_dk"])
    d.line([cx - 5, y + 2, cx + 4, y + 2], fill=C["metal_dk"])

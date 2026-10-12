"""A Tux character: walks the office grid and plays an animation for its current activity."""

import math
from collections import deque

from PIL import Image, ImageDraw

from .office import TILE, Desk, Drawable, Office, Spot, feet, tile_at
from .sprites import ANCHOR, Sprites

# activity -> (where to go, pose animation once there). None = stay put.
ACTIVITIES = {
    "idle": (None, None),
    "think": ("desk", None),
    "type": ("desk", "type"),
    "read": ("shelf", "read"),
    "bash": ("rack", "tinker"),
    "web": ("window", None),
    "coffee": ("coffee", None),
    "rest": ("rug", "sit"),
    "wait": (None, "wave"),
    "leave": ("door", None),
}
LABELS = {
    "idle": "boşta", "think": "düşünüyor", "type": "kod yazıyor", "read": "dosya okuyor", "bash": "komut çalıştırıyor",
    "web": "internette arıyor", "coffee": "kahve alıyor", "rest": "dinleniyor",
    "wait": "onay bekliyor!", "leave": "çıkıyor",
}


class Tux:
    SPEED = 52.0  # px/s
    MIN_DWELL = 1.5  # s to stay at a spot before a queued activity takes over

    def __init__(self, office: Office, sprites: Sprites, desk: Desk, start: str = "door"):
        self.office = office
        self.sprites = sprites
        self.desk = desk
        spot = office.spots[start]
        self.x, self.y = feet(spot.tile)
        self.facing = spot.facing
        self.waypoints: list[tuple[float, float]] = []
        self.activity = "idle"
        self.pose: str | None = None
        self.arrived = True
        self._spot: Spot | None = None
        self.t = 0.0
        self.pending: deque[str] = deque()  # live activities, played in order
        self.gone = False  # walked out of the door after "leave"

    @property
    def tile(self):
        return tile_at(self.x, self.y)

    @property
    def typing(self) -> bool:
        return self.arrived and self.activity == "type"

    def want(self, activity: str):
        """Queue an activity from a live event; each plays once Tux has arrived and dwelt MIN_DWELL.

        "wait" and "leave" are urgent: they drop the backlog and take over at once.
        """
        if activity in ("wait", "leave"):
            self.pending.clear()
        last = self.pending[-1] if self.pending else self.activity
        if activity != last:
            self.pending.append(activity)

    def do(self, activity: str):
        where, _ = ACTIVITIES[activity]
        self.activity = activity
        self.pose = None
        if where is None:
            self.arrived = True
            self._settle(None)
            return
        spot = self.desk.seat if where == "desk" else self.office.spots[where]
        self._go(spot)

    def step(self, dc: int, dr: int):
        """Manual control: move one tile."""
        c, r = self.tile
        nxt = (c + dc, r + dr)
        self.activity = "idle"
        self.pose = None
        self.facing = {(1, 0): "right", (-1, 0): "left", (0, -1): "up", (0, 1): "down"}[(dc, dr)]
        if self.office.walkable(nxt):
            self.waypoints = [feet(nxt)]
            self.arrived = False
            self._spot = None

    def _go(self, spot: Spot):
        tiles = self.office.path(self.tile, spot.tile)
        fx, fy = feet(spot.tile)
        self.waypoints = [feet(t) for t in tiles] + [(fx + spot.dx, fy)]
        self.arrived = False
        self._spot = spot

    def _settle(self, spot: Spot | None):
        _, pose = ACTIVITIES[self.activity]
        if spot is not None:
            self.facing = spot.facing
        self.pose = pose
        self.t = 0.0

    def update(self, dt: float):
        self.t += dt
        if self.pending and ((self.arrived and self.t >= self.MIN_DWELL) or self.pending[0] in ("wait", "leave")):
            self.do(self.pending.popleft())
        if self.arrived:
            return
        budget = self.SPEED * dt
        while budget > 0 and self.waypoints:
            tx, ty = self.waypoints[0]
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            if dist <= budget:
                self.x, self.y = tx, ty
                self.waypoints.pop(0)
                budget -= dist
            else:
                self.x += dx / dist * budget
                self.y += dy / dist * budget
                budget = 0
            if abs(dx) > abs(dy):
                self.facing = "right" if dx > 0 else "left"
            elif dist > 0.01:
                self.facing = "down" if dy > 0 else "up"
        if not self.waypoints:
            self.arrived = True
            self._settle(self._spot)
            if self.activity == "leave":
                self.gone = True

    def _frame(self) -> Image.Image:
        if not self.arrived:
            return self.sprites.get("walk_" + self.facing).at(self.t)
        if self.pose == "read":
            name = "read_" + ("left" if self.facing == "left" else "right")
        elif self.pose:
            name = self.pose
        else:
            name = "idle_" + self.facing
        return self.sprites.get(name).at(self.t)

    def drawables(self) -> list[Drawable]:
        frame = self._frame()
        ox = round(self.x) - ANCHOR[0]
        oy = round(self.y) - ANCHOR[1]

        def draw(img: Image.Image):
            shadow = Image.new("RGBA", (12, 3), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).ellipse([0, 0, 11, 2], fill=(0, 0, 0, 70))
            img.alpha_composite(shadow, (round(self.x) - 6, round(self.y) - 2))
            img.alpha_composite(frame, (ox, oy))
            if self.activity == "wait":
                _bubble(img, round(self.x), oy + 4, self.t)

        return [(self.y, draw)]


def _bubble(img: Image.Image, cx: int, top: int, t: float):
    """Bobbing "!" speech bubble above the head."""
    d = ImageDraw.Draw(img)
    y = top - 12 - (1 if int(t * 4) % 2 else 0)
    d.rounded_rectangle([cx - 4, y, cx + 4, y + 9], radius=2, fill=(250, 250, 250), outline=(30, 30, 40))
    d.polygon([(cx - 1, y + 9), (cx + 2, y + 9), (cx, y + 12)], fill=(250, 250, 250))
    d.line([cx - 1, y + 10, cx, y + 12], fill=(30, 30, 40))
    d.line([cx, y + 2, cx, y + 5], fill=(220, 50, 50))
    d.point([cx, y + 7], fill=(220, 50, 50))

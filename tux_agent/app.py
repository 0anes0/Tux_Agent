"""Scene composition and the main loop."""

import argparse
import os
import signal
import time

from PIL import Image

from . import backends
from . import i18n
from .agent import Tux
from .events import Listener, activity_for
from .office import Office
from .sprites import Sprites

FPS = 15
# Demo routine until real Claude Code events are wired in: (activity, seconds after arriving).
DEMO = [("type", 6), ("read", 4), ("type", 5), ("bash", 4), ("web", 3), ("wait", 3), ("coffee", 2), ("rest", 5)]
HOTKEYS = {"t": "type", "r": "read", "b": "bash", "w": "web", "c": "coffee", "s": "rest", "a": "wait", "l": "leave"}
STEPS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


class Scene:
    """One Tux per live Claude Code session; a demo Tux walks around while there are none."""

    def __init__(self, demo: bool = True, lang: str = "en"):
        self.text = i18n.TEXT[lang]
        self.office = Office()
        self.sprites = Sprites()
        self.agents: dict[str, Tux] = {}
        self.names: dict[str, str] = {}
        self.last_ts: dict[str, float] = {}
        self.demo_tux: Tux | None = None
        self.t = 0.0
        self.demo = demo
        self._demo_i = -1
        self._demo_left = 0.0
        if demo:
            self._spawn_demo()

    def _spawn_demo(self):
        self.demo_tux = Tux(self.office, self.sprites, self.office.desks[0])
        self._demo_i, self._demo_left = -1, 0.0

    def _free_desk(self):
        used = {a.desk for a in self.agents.values()}
        return next((d for d in self.office.desks if d not in used), self.office.desks[len(self.agents) % len(self.office.desks)])

    @property
    def tuxes(self) -> list[Tux]:
        return list(self.agents.values()) + ([self.demo_tux] if self.demo_tux else [])

    @property
    def focus(self) -> Tux | None:
        return self.demo_tux or next(iter(self.agents.values()), None)

    def handle(self, ev: dict):
        sid = ev["session"]
        ts = ev.get("ts") or 0.0
        # async hooks can arrive slightly out of order; keep the newest state
        if ts < self.last_ts.get(sid, 0.0):
            return
        self.last_ts[sid] = ts
        activity = activity_for(ev)
        tux = self.agents.get(sid)
        if tux is None:
            if activity in (None, "leave"):
                return
            tux = self.agents[sid] = Tux(self.office, self.sprites, self._free_desk())
            self.names[sid] = os.path.basename((ev.get("cwd") or "").rstrip("/")) or sid[:6]
            self.demo_tux = None  # real work arrived; the demo Tux clocks out
        if activity:
            tux.want(activity)

    def update(self, dt: float):
        self.t += dt
        tux = self.demo_tux
        if tux and self.demo:
            if tux.arrived:
                self._demo_left -= dt
            if self._demo_left <= 0:
                self._demo_i = (self._demo_i + 1) % len(DEMO)
                activity, self._demo_left = DEMO[self._demo_i]
                tux.do(activity)
        for t in self.tuxes:
            t.update(dt)
        for sid in [sid for sid, t in self.agents.items() if t.gone]:
            del self.agents[sid]
            self.names.pop(sid, None)
        if not self.agents and self.demo_tux is None and self.demo:
            self._spawn_demo()

    def key(self, k: str):
        tux = self.focus
        if tux is None:
            return
        if k == " ":
            self.demo = not self.demo
            self._demo_left = 0
        elif k in HOTKEYS:
            self.demo = False
            tux.do(HOTKEYS[k])
        elif k in STEPS:
            self.demo = False
            tux.step(*STEPS[k])

    def render(self) -> Image.Image:
        img = self.office.background.copy()
        typing = {t.desk for t in self.tuxes if t.typing}
        drawables = self.office.props(self.t, typing)
        for t in self.tuxes:
            drawables += t.drawables()
        for _, draw in sorted(drawables, key=lambda d: d[0]):
            draw(img)
        return img

    def status(self) -> str:
        tx = self.text

        def label(t: Tux) -> str:
            return tx[t.activity] if t.arrived else f"→ {tx[t.activity]}"

        if self.agents:
            parts = [f"🐧 {self.names[sid]}: {label(t)}" for sid, t in self.agents.items()]
            return " " + "   ".join(parts) + f"   · {tx['quit']}"
        if self.demo_tux:
            mode = tx["demo"] if self.demo else tx["manual"]
            return f" 🐧 Tux: {label(self.demo_tux)}   [{mode} · {tx['waiting']}]   {tx['keys']} · {tx['quit']}"
        return f" {tx['waiting']}   {tx['quit']}"


def run(backend_name: str | None, lang: str):
    from .term import Terminal

    scene = Scene(lang=lang)
    listener = Listener()
    resized = True

    def on_winch(*_):
        nonlocal resized
        resized = True

    signal.signal(signal.SIGWINCH, on_winch)
    with listener, Terminal() as term:
        backend = backends.pick(backend_name, term)
        last = time.monotonic()
        while True:
            if resized:
                resized = False
                term.refresh_size()
                term.write(backend.reset() + b"\x1b[2J")
            focus = scene.focus
            frame, status_row = backend.frame(scene.render(), term, (focus.x, focus.y) if focus else (0, 0))
            status = scene.status()[: term.cols].encode()
            term.write(frame + b"\x1b[%d;1H\x1b[2K\x1b[7m" % min(status_row, term.rows) + status + b"\x1b[0m")

            deadline = last + 1 / FPS
            for k in term.keys(deadline - time.monotonic(), wake=[listener]):
                if k in ("q", "esc"):
                    return
                scene.key(k)
            for ev in listener.drain():
                scene.handle(ev)
            now = time.monotonic()
            scene.update(min(now - last, 0.25))
            last = now


def export_gif(path: str, seconds: float, scale: int, scene: Scene | None = None, script=()):
    """Render offscreen to a GIF. `script` is [(seconds, event dict)] fed to scene.handle()."""
    scene = scene or Scene()
    script = sorted(script, key=lambda s: s[0])
    frames = []
    for i in range(int(seconds * FPS)):
        while script and script[0][0] <= i / FPS:
            scene.handle(script.pop(0)[1])
        scene.update(1 / FPS)
        img = scene.render().convert("RGB")
        frames.append(img.resize((img.width * scale, img.height * scale), Image.NEAREST))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0)
    print(f"{path}: {len(frames)} frames")


def main():
    p = argparse.ArgumentParser(prog="tux-agent", description="Claude Code agents as Tux penguins in a pixel office, in your terminal.")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("install", help="add the hooks to ~/.claude/settings.json")
    sub.add_parser("uninstall", help="remove the hooks from ~/.claude/settings.json")
    p.add_argument("--backend", choices=["kitty", "halfblock"], help="default: auto-detect")
    p.add_argument("--lang", choices=sorted(i18n.TEXT), help="status bar language (default: from $LANG)")
    p.add_argument("--gif", metavar="FILE", help="render the demo to a GIF instead of the terminal")
    p.add_argument("--seconds", type=float, default=30, help="GIF length")
    p.add_argument("--scale", type=int, default=3, help="GIF pixel scale")
    args = p.parse_args()
    if args.command in ("install", "uninstall"):
        from . import install

        getattr(install, args.command)()
    elif args.gif:
        export_gif(args.gif, args.seconds, args.scale)
    else:
        run(args.backend, args.lang or i18n.detect())

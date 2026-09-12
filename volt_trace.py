#!/usr/bin/env python3
"""Volt Trace — original ElbowOS neon light-cycle arcade (Python 3 + pygame)."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920
FPS = 30
SECONDS = 15
FRAMES = FPS * SECONDS
TITLE = "VOLT TRACE"
OUT = Path("/home/workdir/artifacts/VOLT_TRACE_ElbowOS.mp4")
CELL = 30

if "--play" not in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402


def _arena():
    return pygame.Rect(60, 220, W - 120, H - 360)


class Bike:
    def __init__(self, x, y, dx, dy, color, glow):
        self.x, self.y = float(x), float(y)
        self.dx, self.dy = dx, dy
        self.color, self.glow = color, glow
        self.trail = [(self.x, self.y)]
        self.alive = True
        self.speed = 9.0
        self.turn_cool = 0

    def pos(self):
        return int(self.x), int(self.y)

    def heading(self, dx, dy):
        if self.turn_cool > 0:
            return
        if dx == -self.dx and dy == -self.dy:
            return
        if (dx, dy) != (0, 0) and (dx == 0) != (dy == 0):
            self.dx, self.dy = dx, dy
            self.turn_cool = 6

    def step(self, walls, enemy_trail, arena):
        if not self.alive:
            return False
        if self.turn_cool:
            self.turn_cool -= 1
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        hit = False
        if not arena.inflate(-8, -8).collidepoint(self.x, self.y):
            hit = True
        px, py = self.pos()
        for i, (tx, ty) in enumerate(self.trail[:-8]):
            if math.hypot(px - tx, py - ty) < 10:
                hit = True
                break
        for tx, ty in enemy_trail[:-4]:
            if math.hypot(px - tx, py - ty) < 12:
                hit = True
                break
        self.trail.append((self.x, self.y))
        if len(self.trail) > 420:
            self.trail.pop(0)
        if hit:
            self.alive = False
        return hit

    def look(self, arena, forbidden):
        """Return a safe 90-degree turn if current heading is doomed."""
        ahead = []
        for k in range(1, 8):
            nx = self.x + self.dx * self.speed * k
            ny = self.y + self.dy * self.speed * k
            ahead.append((nx, ny))
        danger = False
        for nx, ny in ahead:
            if not arena.inflate(-18, -18).collidepoint(nx, ny):
                danger = True
            for tx, ty in forbidden:
                if math.hypot(nx - tx, ny - ty) < 16:
                    danger = True
        if not danger and self.turn_cool == 0 and random.random() < 0.045:
            danger = True  # spice for the reel
        if not danger:
            return
        cands = [(self.dy, -self.dx), (-self.dy, self.dx)]
        random.shuffle(cands)
        best, best_s = None, -1
        for dx, dy in cands:
            s = 0
            for k in range(1, 10):
                nx = self.x + dx * self.speed * k
                ny = self.y + dy * self.speed * k
                if arena.inflate(-22, -22).collidepoint(nx, ny):
                    s += 2
                else:
                    s -= 8
                    break
                close = any(math.hypot(nx - tx, ny - ty) < 16 for tx, ty in forbidden)
                s -= 6 if close else 1
            if s > best_s:
                best, best_s = (dx, dy), s
        if best:
            self.heading(*best)


def col_lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


class Game:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.arena = _arena()
        self.reset()

    def reset(self):
        a = self.arena
        self.you = Bike(a.centerx - 80, a.bottom - 80, 0, -1, (40, 255, 230), (0, 180, 160))
        self.cpu = Bike(a.centerx + 80, a.top + 80, 0, 1, (255, 170, 40), (200, 90, 0))
        self.score = getattr(self, "score", 0)
        self.crashes = 0
        self.t = 0
        self.flash = 0
        self.sparks = []

    def tick(self, human_dir=None):
        self.t += 1
        a = self.arena
        if human_dir:
            self.you.heading(*human_dir)
        else:
            forbid = self.cpu.trail + self.you.trail[:-12]
            self.you.look(a, forbid)
        self.cpu.look(a, self.you.trail + self.cpu.trail[:-12])
        yhit = self.you.step(None, self.cpu.trail, a)
        chit = self.cpu.step(None, self.you.trail, a)
        if yhit or chit:
            self.flash = 10
            self.crashes += 1
            if chit and not yhit:
                self.score += 250
            elif yhit and not chit:
                self.score = max(0, self.score - 40)
            else:
                self.score += 80
            for _ in range(28):
                ang = random.random() * 6.28
                spd = random.uniform(2, 9)
                src = self.you if yhit else self.cpu
                self.sparks.append([src.x, src.y, math.cos(ang) * spd, math.sin(ang) * spd, 18])
            self.you.alive = True
            self.cpu.alive = True
            self.you.trail = self.you.trail[-40:]
            self.cpu.trail = self.cpu.trail[-40:]
            if yhit:
                self.you.heading(random.choice((-1, 1)), 0)
            if chit:
                self.cpu.heading(random.choice((-1, 1)), 0)
        if self.t % 12 == 0 and self.you.alive:
            self.score += 1
        if self.flash:
            self.flash -= 1
        alive = []
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[4] -= 1
            if s[4] > 0:
                alive.append(s)
        self.sparks = alive


def draw(surf, g, fonts):
    font_lg, font_md, font_sm = fonts
    t = g.t
    for y in range(0, H, 6):
        k = y / H
        c = col_lerp((2, 18, 28), (8, 6, 48), k)
        pygame.draw.rect(surf, c, (0, y, W, 6))
    for i in range(18):
        yy = int((t * 3 + i * 110) % H)
        pygame.draw.line(surf, (10, 40, 55), (0, yy), (W, yy), 1)

    a = g.arena
    pygame.draw.rect(surf, (6, 24, 36), a)
    pulse = 18 + int(10 * math.sin(t * 0.08))
    grid_c = (12, 55 + pulse, 70)
    for x in range(a.left, a.right + 1, CELL):
        pygame.draw.line(surf, grid_c, (x, a.top), (x, a.bottom), 1)
    for y in range(a.top, a.bottom + 1, CELL):
        pygame.draw.line(surf, grid_c, (a.left, y), (a.right, y), 1)
    pygame.draw.rect(surf, (0, 255, 200), a, 4)
    pygame.draw.rect(surf, (255, 80, 200), a.inflate(10, 10), 2)

    def draw_bike(b):
        if len(b.trail) > 1:
            pts = [(int(x), int(y)) for x, y in b.trail]
            glow = pygame.Surface((W, H), pygame.SRCALPHA)
            if len(pts) > 2:
                pygame.draw.lines(glow, (*b.glow, 90), False, pts, 14)
            surf.blit(glow, (0, 0))
            pygame.draw.lines(surf, b.color, False, pts, 5)
        px, py = b.pos()
        pygame.draw.circle(surf, b.color, (px, py), 16)
        pygame.draw.circle(surf, (255, 255, 255), (px, py), 6)
        hx, hy = px + b.dx * 18, py + b.dy * 18
        pygame.draw.line(surf, (255, 255, 220), (px, py), (int(hx), int(hy)), 3)

    draw_bike(g.cpu)
    draw_bike(g.you)
    for s in g.sparks:
        pygame.draw.circle(surf, (255, 240, 160), (int(s[0]), int(s[1])), max(1, s[4] // 4))

    if g.flash:
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((180, 255, 240, 40))
        surf.blit(veil, (0, 0))

    bar = pygame.Surface((W, 150), pygame.SRCALPHA)
    bar.fill((0, 12, 22, 220))
    surf.blit(bar, (0, 0))
    title = font_lg.render(TITLE, True, (40, 255, 230))
    surf.blit(title, (40, 16))
    sub = font_sm.render("ElbowOS  ·  Python 3 light-cycle  ·  autoplay reel", True, (140, 220, 255))
    surf.blit(sub, (44, 92))
    sc = font_md.render(f"VOLT  {g.score:05d}", True, (255, 180, 50))
    surf.blit(sc, (W - sc.get_width() - 40, 28))

    foot = pygame.Surface((W, 90), pygame.SRCALPHA)
    foot.fill((0, 12, 22, 220))
    surf.blit(foot, (0, H - 90))
    tag = font_sm.render("x.com/ElbowOS", True, (40, 255, 230))
    surf.blit(tag, (W - tag.get_width() - 40, H - 62))
    hint = font_sm.render("ARROWS turn   ·   dodge the amber ribbon", True, (120, 170, 190))
    surf.blit(hint, (40, H - 62))


def fonts():
    try:
        return (
            pygame.font.SysFont("dejavusans", 72, bold=True),
            pygame.font.SysFont("dejavusans", 42, bold=True),
            pygame.font.SysFont("dejavusans", 28),
        )
    except Exception:
        return pygame.font.Font(None, 80), pygame.font.Font(None, 48), pygame.font.Font(None, 32)


def record(out: Path = OUT) -> Path:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    surf = pygame.Surface((W, H))
    g = Game()
    fnt = fonts()
    tmp = out.with_suffix(".tmp.mp4")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "veryfast", "-movflags", "+faststart", str(tmp),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    for _ in range(FRAMES):
        g.tick()
        draw(surf, g, fnt)
        proc.stdin.write(pygame.image.tostring(surf, "RGB"))
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    rc = proc.wait()
    pygame.quit()
    if rc != 0 or not tmp.exists():
        raise RuntimeError(f"ffmpeg failed ({rc}): {err[-800:]}")
    tmp.replace(out)
    return out


def play():
    os.environ.pop("SDL_VIDEODRIVER", None)
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((W // 2, H // 2))
    pygame.display.set_caption("Volt Trace — ElbowOS")
    canvas = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    g = Game()
    fnt = fonts()
    running = True
    while running:
        human = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif ev.key == pygame.K_LEFT:
                    human = (-1, 0)
                elif ev.key == pygame.K_RIGHT:
                    human = (1, 0)
                elif ev.key == pygame.K_UP:
                    human = (0, -1)
                elif ev.key == pygame.K_DOWN:
                    human = (0, 1)
                elif ev.key == pygame.K_r:
                    g.score = 0
                    g.reset()
        g.tick(human)
        draw(canvas, g, fnt)
        pygame.transform.smoothscale(canvas, screen.get_size(), screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    if "--play" in sys.argv:
        play()
    else:
        path = record()
        print(path)
        print("bytes", path.stat().st_size)
        sys.exit(0)

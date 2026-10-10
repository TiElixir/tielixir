#!/usr/bin/env python3
"""
Generates the animated, ordered-dithered SVGs used in README.md.

    python generate.py

Writes banner.svg and divider.svg next to this script. Everything is plain SVG
(SMIL), so GitHub renders it inside an <img> tag with no JavaScript.
Tweak the PALETTE / PHRASES below and re-run.
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette
PALETTE = {
    "bg": "#0c0f1a",        # deep ink
    "ink": "#eceff8",       # title
    "muted": "#8b93b5",     # subtitle
    "wave_back": "#161b33",
    "wave_front": "#262e55",
    "bracket": "#2b3361",
    "orb_dim": "#1c2244",
    "accent": "#ffc46b",    # the "elixir": orb, cursor, prompt
    "fringe": "#8ea2ff",    # brief glitch fringe on the title
}

PHRASES = [
    "first-year cs at iiest shibpur",
    "python, ai systems, simulations",
    "backend, automation, quantum circuits",
    "building things to see how they work",
]

# ---------------------------------------------------------------- dithering
def bayer(n):
    if n == 1:
        return [[0]]
    m = bayer(n // 2)
    s = n // 2
    out = [[0] * n for _ in range(n)]
    for y in range(s):
        for x in range(s):
            v = m[y][x] * 4
            out[y][x] = v
            out[y][x + s] = v + 2
            out[y + s][x] = v + 3
            out[y + s][x + s] = v + 1
    return out


B8 = bayer(8)


def thr(x, y):
    return (B8[y % 8][x % 8] + 0.5) / 64.0


def to_path(cells):
    """Merge horizontal runs of cells into one compact path string."""
    rows = {}
    for x, y in cells:
        rows.setdefault(y, []).append(x)
    parts = []
    for y in sorted(rows):
        xs = sorted(set(rows[y]))
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            w = prev - start + 1
            parts.append(f"M{start} {y}h{w}v1h-{w}z")
            if x is not None:
                start = prev = x
    return "".join(parts)


def animate_d(frames, dur):
    return (
        f'<animate attributeName="d" dur="{dur}s" repeatCount="indefinite" '
        f'calcMode="discrete" values="{";".join(frames)}"/>'
    )


# ---------------------------------------------------------------- 5x7 pixel font
GLYPHS = {
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "i": [".#.", "...", "##.", ".#.", ".#.", ".#.", "###"],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "l": ["##.", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
    "x": [".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "r": ["....", "....", "#.##", "##..", "#...", "#...", "#..."],
}

# ---------------------------------------------------------------- banner
W, H, CELL = 150, 36, 8  # grid in cells, 1200 x 288 px
TX, TY, TS = 8, 6, 2     # title origin and pixel scale


def title_cells(text="TiElixir"):
    cells, cx = set(), TX
    for ch in text:
        g = GLYPHS[ch]
        for ry, row in enumerate(g):
            for rx, c in enumerate(row):
                if c == "#":
                    for dy in range(TS):
                        for dx in range(TS):
                            cells.add((cx + rx * TS + dx, TY + ry * TS + dy))
        cx += (len(g[0]) + 1) * TS
    return cells, cx


CX, CY, R = 128, 18, 14.5  # the orb
N_ORB, N_WAVE = 48, 24


def orb_cells(k):
    """Moon-phase lighting: the light travels around the orb once per loop."""
    th = 2 * math.pi * k / N_ORB
    L = (math.sin(th), -0.38, math.cos(th))
    n = math.sqrt(sum(c * c for c in L))
    L = tuple(c / n for c in L)
    out = []
    for y in range(H):
        for x in range(W):
            dx, dy = (x + 0.5 - CX) / R, (y + 0.5 - CY) / R
            r2 = dx * dx + dy * dy
            if r2 > 1:
                continue
            dz = math.sqrt(1 - r2)
            i = dx * L[0] + dy * L[1] + dz * L[2]
            if i > 0 and 0.97 * i > thr(x, y):
                out.append((x, y))
    return out


def orb_dim_cells():
    out = []
    for y in range(H):
        for x in range(W):
            dx, dy = (x + 0.5 - CX) / R, (y + 0.5 - CY) / R
            if dx * dx + dy * dy <= 1 and thr(x, y) < 0.17:
                out.append((x, y))
    return out


def wave_cells(k, ytop, amp, ph_off, direction, vmax, gamma):
    phi = 2 * math.pi * k / N_WAVE
    out = []
    for x in range(W):
        yo = (
            ytop
            + amp * math.sin(2 * math.pi * x / 54 - direction * phi + ph_off)
            + amp * 0.5 * math.sin(2 * math.pi * x / 23 + direction * 2 * phi)
        )
        for y in range(H):
            yc = y + 0.5
            if yc < yo:
                continue
            # leave a clean halo around the orb
            if (x + 0.5 - CX) ** 2 + (yc - CY) ** 2 < (R + 1.6) ** 2:
                continue
            v = vmax * ((yc - yo) / (H - yo)) ** gamma
            if v > thr(x, y):
                out.append((x, y))
    return out


def bracket(x, y, sx, sy, n=4):
    cells = [(x + sx * i, y) for i in range(n)]
    cells += [(x, y + sy * i) for i in range(1, n)]
    return cells


def phrase_text(i, text):
    n = len(PHRASES)
    s = i / n
    kt = [0.0, s, s + 0.03, s + 0.22, s + 0.25, 1.0]
    vs = [0, 0, 1, 1, 0, 0]
    pairs = []
    for t, v in zip(kt, vs):
        if pairs and abs(pairs[-1][0] - t) < 1e-9:
            pairs[-1] = (t, v)
        else:
            pairs.append((t, v))
    key_times = ";".join(f"{t:.3f}" for t, _ in pairs)
    values = ";".join(str(v) for _, v in pairs)
    return (
        f'<text x="88" y="198" font-size="17" fill="{PALETTE["muted"]}" opacity="0" '
        f'textLength="{len(text) * 10.2:.1f}" lengthAdjust="spacing">{text}'
        f'<animate attributeName="opacity" dur="{n * 3.2}s" repeatCount="indefinite" '
        f'keyTimes="{key_times}" values="{values}"/></text>'
    )


def build_banner():
    P = PALETTE
    t_cells, cursor_x = title_cells()
    title_d = to_path(t_cells)

    back = [to_path(wave_cells(k, 27.2, 1.2, math.pi / 2, -1, 0.34, 1.0)) for k in range(N_WAVE)]
    front = [to_path(wave_cells(k, 29.0, 1.6, 0.0, 1, 0.92, 0.9)) for k in range(N_WAVE)]
    orb = [to_path(orb_cells(k)) for k in range(N_ORB)]

    brackets = to_path(
        bracket(2, 2, 1, 1) + bracket(W - 3, 2, -1, 1)
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W * CELL} {H * CELL}" width="{W * CELL}" height="{H * CELL}" role="img" aria-label="TiElixir, first-year CS student at IIEST Shibpur">
<title>TiElixir</title>
<defs><clipPath id="r"><rect width="{W * CELL}" height="{H * CELL}" rx="14"/></clipPath></defs>
<g clip-path="url(#r)">
<rect width="{W * CELL}" height="{H * CELL}" fill="{P["bg"]}"/>
<g transform="scale({CELL})" shape-rendering="crispEdges">
<path fill="{P["bracket"]}" d="{brackets}"/>
<path fill="{P["wave_back"]}" d="{back[0]}">{animate_d(back, 3)}</path>
<path fill="{P["wave_front"]}" d="{front[0]}">{animate_d(front, 3)}</path>
<path fill="{P["orb_dim"]}" d="{to_path(orb_dim_cells())}"/>
<path fill="{P["accent"]}" d="{orb[0]}">{animate_d(orb, 9.6)}</path>
<path fill="{P["fringe"]}" opacity="0" transform="translate(-1 0)" d="{title_d}"><animate attributeName="opacity" dur="7s" repeatCount="indefinite" keyTimes="0;0.9;0.915;0.93;0.945;0.96;1" values="0;0;0.9;0;0.9;0;0"/></path>
<path fill="{P["ink"]}" d="{title_d}"/>
<rect x="{cursor_x}" y="{TY}" width="4" height="{7 * TS}" fill="{P["accent"]}"><animate attributeName="opacity" dur="1.1s" repeatCount="indefinite" calcMode="discrete" values="1;0"/></rect>
</g>
<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace">
<text x="64" y="198" font-size="17" fill="{P["accent"]}">&gt;</text>
{"".join(phrase_text(i, t) for i, t in enumerate(PHRASES))}
</g>
</g>
</svg>
'''
    return svg


# ---------------------------------------------------------------- divider
DW, DH, DC, N_DIV = 300, 4, 4, 36  # 1200 x 16 px
WY = [0.5, 1.0, 1.0, 0.5]


def divider_cells(k):
    out = []
    for blob in (k / N_DIV * DW, (k / N_DIV * DW + DW / 2) % DW):
        for x in range(DW):
            d = abs(x - blob)
            d = min(d, DW - d)
            g = math.exp(-(d * d) / (2 * 20 * 20))
            for y in range(DH):
                if g * WY[y] > thr(x, y):
                    out.append((x, y))
    return out


def build_divider():
    frames = [to_path(divider_cells(k)) for k in range(N_DIV)]
    base = [(x, y) for x in range(DW) for y in range(DH) if 0.2 * WY[y] > thr(x, y)]
    P = PALETTE
    # Mid-tone colours so the divider reads on both GitHub light and dark themes.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {DW * DC} {DH * DC}" width="{DW * DC}" height="{DH * DC}" role="presentation">
<g transform="scale({DC})" shape-rendering="crispEdges">
<path fill="#8b93b5" opacity="0.55" d="{to_path(base)}"/>
<path fill="#f5a524" d="{frames[0]}">{animate_d(frames, 3.6)}</path>
</g>
</svg>
'''


if __name__ == "__main__":
    for name, content in (("banner.svg", build_banner()), ("divider.svg", build_divider())):
        path = os.path.join(HERE, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{name}: {len(content) / 1024:.0f} KB")

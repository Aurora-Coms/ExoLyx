#!/usr/bin/env python3
"""Collection 2 : 50 styles × 4 palettes = 200 fonds d'écran ExoLyx.

    python3 src/wallpapers/outils/collection2.py SORTIE [--largeur 1920 --hauteur 1080]
        [--miniatures 480] [--seul 07]

Chaque style est une fonction (W, H, P) -> SVG ; P est une palette :
  P["bg"] = (haut, bas), P["c"] = [accent, 2e, 3e, 4e], P["sombre"] = bool.
Sans <filter> (docs/CONVENTIONS.md) : les flous sont des dégradés radiaux.
"""

import argparse
import math
import os
import random
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from collection import rendre_png  # noqa: E402

# ---------------------------------------------------------------- palettes
PALETTES = {
    "pomme":     dict(nom="Pomme",     bg=("#16241A", "#0A0F0B"), c=["#A8D479", "#BDD479", "#6FA845", "#E4F5B8"], sombre=True),
    "ocean":     dict(nom="Océan",     bg=("#06304A", "#021320"), c=["#3FD0D4", "#0B8DB5", "#B6F5F2", "#1E6E9C"], sombre=True),
    "braise":    dict(nom="Braise",    bg=("#3A120C", "#120605"), c=["#FF6A2B", "#FFB347", "#E5383B", "#FFE0A3"], sombre=True),
    "amethyste": dict(nom="Améthyste", bg=("#241038", "#0B0616"), c=["#B04BFF", "#FF3DCB", "#7A2BFF", "#E5D4FF"], sombre=True),
    "nuit":      dict(nom="Nuit",      bg=("#152245", "#060A18"), c=["#6C8CFF", "#9DB6F0", "#F4F1E4", "#3A5A9B"], sombre=True),
    "retro":     dict(nom="Rétro",     bg=("#3B1450", "#140A2A"), c=["#FF5E8A", "#FFC857", "#2EC4B6", "#FF9A5E"], sombre=True),
    "graphite":  dict(nom="Graphite",  bg=("#22252A", "#0C0D0F"), c=["#E6E6E6", "#9AA0A6", "#5F656C", "#FFFFFF"], sombre=True),
    "corail":    dict(nom="Corail",    bg=("#FFF4EC", "#FFD9C7"), c=["#FF7E6B", "#E8556D", "#F7C59F", "#B83B5E"], sombre=False),
    "menthe":    dict(nom="Menthe",    bg=("#F1FAF3", "#D4F0DD"), c=["#4E8F3A", "#7FD1B9", "#A8D479", "#2F5D50"], sombre=False),
    "sable":     dict(nom="Sable",     bg=("#F8F1E5", "#EADFCB"), c=["#C0703A", "#E3B04B", "#2F5D50", "#9C8463"], sombre=False),
    "lavande":   dict(nom="Lavande",   bg=("#F6F1FC", "#DCD0F0"), c=["#7A66AE", "#B3A0DB", "#5A4890", "#FF9FBF"], sombre=False),
    "ciel":      dict(nom="Ciel",      bg=("#F2F8FD", "#CFE3F2"), c=["#3C82C8", "#7FB2E0", "#1E4E80", "#9CCBEA"], sombre=False),
}
ORDRE = list(PALETTES)


def palettes_du_style(i):
    """4 palettes différentes par style, en alternant sombres et claires."""
    sombres = [p for p in ORDRE if PALETTES[p]["sombre"]]
    claires = [p for p in ORDRE if not PALETTES[p]["sombre"]]
    return [sombres[i % 7], claires[i % 5], sombres[(i + 3) % 7], claires[(i + 2) % 5]]


# ---------------------------------------------------------------- outils
def K(W, H):
    return min(H, W * 9 / 16) / 1080


def doc(W, H, defs, corps):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<defs>{defs}</defs>{corps}</svg>')


def fond(W, H, P, angle="v"):
    a, b = P["bg"]
    x2, y2 = (0, 1) if angle == "v" else (1, 1)
    return (f'<linearGradient id="bg" x1="0" y1="0" x2="{x2}" y2="{y2}"><stop offset="0" stop-color="{a}"/>'
            f'<stop offset="1" stop-color="{b}"/></linearGradient>', f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')


def lg(id_, c0, c1, x2=1, y2=0, o0=1, o1=1):
    return (f'<linearGradient id="{id_}" x1="0" y1="0" x2="{x2}" y2="{y2}"><stop offset="0" stop-color="{c0}" stop-opacity="{o0}"/>'
            f'<stop offset="1" stop-color="{c1}" stop-opacity="{o1}"/></linearGradient>')


def halo(id_, x, y, r, c, op=0.6):
    return (f'<radialGradient id="{id_}" gradientUnits="userSpaceOnUse" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}">'
            f'<stop offset="0" stop-color="{c}" stop-opacity="{op}"/><stop offset="0.5" stop-color="{c}" stop-opacity="{op * 0.4:.3f}"/>'
            f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>',
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="url(#{id_})"/>')


def base(W, H, P, lueur=True, angle="v"):
    d, c = fond(W, H, P, angle)
    if lueur:
        d2, c2 = halo("lueur", W * 0.75, H * 0.25, max(W, H) * 0.6, P["c"][0], 0.22 if P["sombre"] else 0.18)
        d, c = d + d2, c + c2
    return d, c


def pts(lst):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in lst)


def crete(W, H, y0, ampl, graine, pas=10, harm=4):
    rnd = random.Random(graine)
    comps = [(rnd.uniform(0.5, 1) / (i + 1), rnd.uniform(1, 2.5) * (i + 1), rnd.uniform(0, 6.3)) for i in range(harm)]
    return [(x, y0 + ampl * sum(a * math.sin(2 * math.pi * f * x / W + p) for a, f, p in comps)) for x in range(0, W + pas, pas)]


def sol(W, H, ligne):
    return f'M0,{H} L{pts(ligne).replace(" ", " L")} L{W},{H} Z'


def etoiles(W, H, n, c, graine, k):
    rnd = random.Random(graine)
    return "".join(f'<circle cx="{rnd.random() * W:.1f}" cy="{rnd.random() * H:.1f}" r="{(0.5 + rnd.random() ** 3 * 1.8) * k:.2f}" '
                   f'fill="{c}" opacity="{0.2 + rnd.random() * 0.6:.2f}"/>' for _ in range(n))


def txt_op(P, fort=1.0):
    return min(1, (0.9 if P["sombre"] else 0.8) * fort)


# ---------------------------------------------------------------- 50 styles
def s01_cercles_decales(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    for i in range(14):
        r = (60 + i * 70) * k
        c += f'<circle cx="{W * 0.3 + i * 18 * k:.1f}" cy="{H * 0.55:.1f}" r="{r:.1f}" fill="none" stroke="{P["c"][i % 4]}" stroke-width="{(10 - i * 0.5) * k:.1f}" opacity="{0.85 - i * 0.05:.2f}"/>'
    return doc(W, H, d, c)


def s02_bandes_diagonales(W, H, P):
    d, c = fond(W, H, P)
    n = 9
    for i in range(n):
        x = -H + i * (W + H) / n
        w = (W + H) / n * 0.62
        d += lg(f"b{i}", P["c"][i % 4], P["c"][(i + 1) % 4], 0, 1, 0.9, 0.5)
        c += f'<polygon points="{pts([(x, H), (x + w, H), (x + w + H, 0), (x + H, 0)])}" fill="url(#b{i})" opacity="0.8"/>'
    return doc(W, H, d, c)


def s03_damier_degrade(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    s = 90 * k
    for j in range(int(H / s) + 1):
        for i in range(int(W / s) + 1):
            if (i + j) % 2:
                t = i * s / W
                c += f'<rect x="{i * s:.1f}" y="{j * s:.1f}" width="{s:.1f}" height="{s:.1f}" fill="{P["c"][(i // 4) % 4]}" opacity="{0.08 + 0.55 * t * t:.2f}"/>'
    return doc(W, H, d, c)


def s04_trame_points(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    s = 34 * k
    cx, cy = W * 0.7, H * 0.4
    for j in range(int(H / s) + 2):
        for i in range(int(W / s) + 2):
            x, y = i * s + (s / 2 if j % 2 else 0), j * s
            t = max(0, 1 - math.hypot(x - cx, y - cy) / (W * 0.65))
            if t > 0.02:
                c += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s * 0.48 * t:.1f}" fill="{P["c"][0]}"/>'
    return doc(W, H, d, c)


def s05_lignes_ondulees(W, H, P):
    k = K(W, H); d, c = base(W, H, P, False)
    for j in range(46):
        y0 = H * (j / 45)
        ligne = [(x, y0 + 40 * k * math.sin(x / W * 6 + j * 0.25) * math.sin(j / 45 * math.pi)) for x in range(0, W + 12, 12)]
        c += f'<polyline points="{pts(ligne)}" fill="none" stroke="{P["c"][j % 3]}" stroke-width="{2.2 * k:.1f}" opacity="{0.25 + 0.6 * math.sin(j / 45 * math.pi):.2f}"/>'
    return doc(W, H, d, c)


def s06_spirale(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    cx, cy = W * 0.5, H * 0.5
    for bras in range(4):
        l = []
        for t in range(0, 900):
            a = t / 60 + bras * math.pi / 2
            r = t * 1.15 * k
            l.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        c += f'<polyline points="{pts(l)}" fill="none" stroke="{P["c"][bras]}" stroke-width="{14 * k:.1f}" stroke-linecap="round" opacity="0.8"/>'
    return doc(W, H, d, c)


def s07_rayons(W, H, P):
    d, c = fond(W, H, P)
    cx, cy, R = W * 0.5, H * 1.05, max(W, H) * 1.5
    n = 36
    for i in range(n):
        a0, a1 = math.pi + i * math.pi / n, math.pi + (i + 0.5) * math.pi / n
        c += f'<polygon points="{pts([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))])}" fill="{P["c"][i % 2]}" opacity="0.28"/>'
    d2, c2 = halo("so", cx, cy, H * 0.75, P["c"][3], 0.9)
    return doc(W, H, d + d2, c + c2 + f'<circle cx="{cx}" cy="{cy}" r="{H * 0.28:.1f}" fill="{P["c"][1]}"/>')


def s08_bulles(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(8)
    for i in range(70):
        r = rnd.uniform(10, 140) * k
        x, y = rnd.random() * W, rnd.random() * H
        col = P["c"][i % 4]
        c += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{col}" fill-opacity="0.18" stroke="{col}" stroke-width="{2 * k:.1f}" stroke-opacity="0.6"/>'
    return doc(W, H, d, c)


def s09_eclats(W, H, P):
    d, c = fond(W, H, P, "d")
    rnd = random.Random(9)
    for i in range(16):
        p = [(rnd.uniform(-0.2, 1.2) * W, rnd.uniform(-0.2, 1.2) * H) for _ in range(3)]
        c += f'<polygon points="{pts(p)}" fill="{P["c"][i % 4]}" opacity="{rnd.uniform(0.15, 0.55):.2f}"/>'
    return doc(W, H, d, c)


def s10_arcs_empiles(W, H, P):
    k = K(W, H); d, c = base(W, H, P, False)
    for col in range(3):
        cx = W * (0.2 + col * 0.3)
        for i in range(6, 0, -1):
            r = i * 55 * k
            c += f'<path d="M{cx - r:.1f},{H} A{r:.1f},{r:.1f} 0 0 1 {cx + r:.1f},{H} Z" fill="{P["c"][(i + col) % 4]}" opacity="0.92"/>'
    return doc(W, H, d, c)


def s11_cubes_iso(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    s = 70 * k
    w, h = s * math.sqrt(3), s
    rnd = random.Random(11)
    for j in range(-1, int(H / (1.5 * s)) + 2):
        for i in range(-1, int(W / w) + 2):
            x = i * w + (w / 2 if j % 2 else 0)
            y = j * 1.5 * s
            top = [(x, y - s), (x + w / 2, y - s / 2), (x, y), (x - w / 2, y - s / 2)]
            gau = [(x - w / 2, y - s / 2), (x, y), (x, y + s), (x - w / 2, y + s / 2)]
            dro = [(x + w / 2, y - s / 2), (x, y), (x, y + s), (x + w / 2, y + s / 2)]
            o = 0.35 + 0.5 * rnd.random() * (x / W)
            c += (f'<polygon points="{pts(top)}" fill="{P["c"][3]}" opacity="{o:.2f}"/>'
                  f'<polygon points="{pts(gau)}" fill="{P["c"][0]}" opacity="{o:.2f}"/>'
                  f'<polygon points="{pts(dro)}" fill="{P["c"][2]}" opacity="{o:.2f}"/>')
    return doc(W, H, d, c)


def s12_ecailles(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    r = 70 * k
    for j in range(int(H / (r * 0.5)) + 3):
        y = j * r * 0.5
        for i in range(-1, int(W / (2 * r)) + 2):
            x = i * 2 * r + (r if j % 2 else 0)
            for m in range(4):
                rr = r * (1 - m * 0.24)
                c += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{P["c"][m] if m % 2 == 0 else P["bg"][0]}" stroke="{P["bg"][1]}" stroke-width="{2 * k:.1f}" opacity="{0.35 + 0.55 * y / H:.2f}"/>'
    return doc(W, H, d, c)


def s13_montagnes_angulaires(W, H, P):
    d, c = base(W, H, P)
    rnd = random.Random(13)
    for couche in range(4):
        y0 = H * (0.45 + couche * 0.13)
        p = [(0, H)]
        x = 0
        while x < W:
            p.append((x, y0 - rnd.uniform(0, H * 0.18)))
            x += rnd.uniform(W * 0.05, W * 0.14)
            p.append((x, y0 + rnd.uniform(0, H * 0.04)))
        p += [(W, y0), (W, H)]
        c += f'<polygon points="{pts(p)}" fill="{P["c"][couche % 4]}" opacity="{0.55 + couche * 0.15:.2f}"/>'
    return doc(W, H, d, c)


def s14_lune_nuages(W, H, P):
    k = K(W, H); d, c = base(W, H, P, False)
    d2, c2 = halo("lu", W * 0.7, H * 0.32, 320 * k, P["c"][3], 0.5)
    d, c = d + d2, c + c2 + f'<circle cx="{W * 0.7:.1f}" cy="{H * 0.32:.1f}" r="{110 * k:.1f}" fill="{P["c"][3]}"/>'
    rnd = random.Random(14)
    for rang in range(4):
        y = H * (0.6 + rang * 0.12)
        x = -100 * k
        while x < W + 100 * k:
            r = rnd.uniform(70, 150) * k
            c += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{P["c"][rang % 3]}" opacity="{0.35 + rang * 0.18:.2f}"/>'
            x += r * 1.2
        c += f'<rect x="0" y="{y:.1f}" width="{W}" height="{H - y:.1f}" fill="{P["c"][rang % 3]}" opacity="{0.35 + rang * 0.18:.2f}"/>'
    return doc(W, H, d, c)


def s15_foret(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(15)
    for rang in range(4):
        y = H * (0.55 + rang * 0.13)
        n = 18 + rang * 6
        for i in range(n):
            x = (i + rnd.random()) * W / n
            h = rnd.uniform(160, 300) * k * (1 + rang * 0.25)
            w = h * 0.32
            c += f'<polygon points="{pts([(x, y - h), (x + w, y + 10 * k), (x - w, y + 10 * k)])}" fill="{P["c"][rang]}" opacity="{0.5 + rang * 0.16:.2f}"/>'
        c += f'<rect y="{y:.1f}" width="{W}" height="{H - y:.1f}" fill="{P["c"][rang]}" opacity="{0.5 + rang * 0.16:.2f}"/>'
    return doc(W, H, d, c)


def s16_skyline(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(16)
    if P["sombre"]:
        c += etoiles(W, H, 150, P["c"][3], 16, k)
    for rang in range(3):
        x = 0
        while x < W:
            w = rnd.uniform(50, 130) * k
            h = rnd.uniform(0.15, 0.5) * H * (1 - rang * 0.2)
            col = P["c"][rang]
            c += f'<rect x="{x:.1f}" y="{H - h:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{col}" opacity="{0.35 + rang * 0.3:.2f}"/>'
            if rang == 2:
                for fy in range(int(H - h + 20 * k), H, int(28 * k)):
                    for fx in range(int(x + 10 * k), int(x + w - 10 * k), int(22 * k)):
                        if rnd.random() < 0.35:
                            c += f'<rect x="{fx}" y="{fy}" width="{8 * k:.1f}" height="{12 * k:.1f}" fill="{P["c"][3]}" opacity="0.8"/>'
            x += w + rnd.uniform(0, 20) * k
    return doc(W, H, d, c)


def s17_soleil_raye(W, H, P):
    d, c = fond(W, H, P)
    cx, cy, r = W * 0.5, H * 0.55, H * 0.3
    d += lg("so", P["c"][1], P["c"][0], 0, 1)
    d += f'<clipPath id="cs"><circle cx="{cx}" cy="{cy}" r="{r:.1f}"/></clipPath>'
    c += f'<g clip-path="url(#cs)"><rect x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r:.1f}" height="{2 * r:.1f}" fill="url(#so)"/>'
    for i in range(8):
        y = cy + r * (0.1 + i * 0.12)
        c += f'<rect x="{cx - r:.1f}" y="{y:.1f}" width="{2 * r:.1f}" height="{r * (0.015 + i * 0.012):.1f}" fill="{P["bg"][1]}"/>'
    c += "</g>"
    c += f'<rect y="{H * 0.78:.1f}" width="{W}" height="{H * 0.22:.1f}" fill="{P["c"][3]}" opacity="0.25"/>'
    for i in range(6):
        y = H * (0.8 + i * 0.035)
        c += f'<rect x="{W * (0.3 - i * 0.04):.1f}" y="{y:.1f}" width="{W * (0.4 + i * 0.08):.1f}" height="{H * 0.006:.1f}" fill="{P["c"][i % 2]}" opacity="0.5"/>'
    return doc(W, H, d, c)


def s18_synthwave(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    hz = H * 0.58
    d2, c2 = halo("so", W / 2, hz, H * 0.5, P["c"][0], 0.6)
    d, c = d + d2, c + c2
    c += etoiles(W, int(hz), 140, P["c"][3], 18, k)
    c += f'<circle cx="{W / 2}" cy="{hz - H * 0.05:.1f}" r="{H * 0.22:.1f}" fill="{P["c"][1]}"/>'
    c += f'<rect y="{hz:.1f}" width="{W}" height="{H - hz:.1f}" fill="{P["bg"][1]}"/>'
    for i in range(1, 16):
        y = hz + (H - hz) * (i / 15) ** 2
        c += f'<line x1="0" y1="{y:.1f}" x2="{W}" y2="{y:.1f}" stroke="{P["c"][0]}" stroke-width="{2 * k:.1f}" opacity="0.8"/>'
    for i in range(-20, 21):
        c += f'<line x1="{W / 2 + i * W * 0.02:.1f}" y1="{hz:.1f}" x2="{W / 2 + i * W * 0.12:.1f}" y2="{H}" stroke="{P["c"][0]}" stroke-width="{2 * k:.1f}" opacity="0.7"/>'
    return doc(W, H, d, c)


def s19_aurore(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    c += etoiles(W, H, 180, "#FFFFFF" if P["sombre"] else P["c"][2], 19, k)
    for b in range(4):
        rnd = random.Random(190 + b)
        ph = rnd.uniform(0, 6)
        d += lg(f"a{b}", P["c"][b], P["c"][b], 0, 1, 0, 0.75)
        for i in range(0, W, max(4, int(6 * k))):
            y = H * (0.35 + 0.12 * math.sin(i / W * 5 + ph) + b * 0.05)
            h = H * (0.18 + 0.1 * math.sin(i / W * 13 + ph * 2))
            c += f'<rect x="{i}" y="{y - h:.1f}" width="{max(4, int(6 * k))}" height="{h:.1f}" fill="url(#a{b})" opacity="0.35"/>'
    return doc(W, H, d, c)


def s20_pluie(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(20)
    for i in range(420):
        x, y = rnd.random() * (W + H * 0.4), rnd.random() * H
        l = rnd.uniform(40, 180) * k
        c += f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x - l * 0.35:.1f}" y2="{y + l:.1f}" stroke="{P["c"][i % 4]}" stroke-width="{rnd.uniform(1, 3.5) * k:.1f}" stroke-linecap="round" opacity="{rnd.uniform(0.2, 0.8):.2f}"/>'
    return doc(W, H, d, c)


def s21_constellations(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(21)
    c += etoiles(W, H, 250, P["c"][3], 21, k)
    for g in range(7):
        gx, gy = rnd.uniform(0.1, 0.9) * W, rnd.uniform(0.1, 0.9) * H
        p = [(gx + rnd.uniform(-160, 160) * k, gy + rnd.uniform(-120, 120) * k) for _ in range(rnd.randint(4, 7))]
        c += f'<polyline points="{pts(p)}" fill="none" stroke="{P["c"][g % 3]}" stroke-width="{3.2 * k:.1f}" opacity="0.85"/>'
        for x, y in p:
            c += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{9 * k:.1f}" fill="{P["c"][g % 3]}"/>'
    return doc(W, H, d, c)


def s22_atome(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    cx, cy = W * 0.5, H * 0.5
    for i in range(6):
        c += f'<ellipse cx="{cx}" cy="{cy}" rx="{420 * k:.1f}" ry="{120 * k:.1f}" transform="rotate({i * 30} {cx} {cy})" fill="none" stroke="{P["c"][i % 4]}" stroke-width="{5 * k:.1f}" opacity="0.75"/>'
    d2, c2 = halo("no", cx, cy, 160 * k, P["c"][0], 0.8)
    return doc(W, H, d + d2, c + c2 + f'<circle cx="{cx}" cy="{cy}" r="{50 * k:.1f}" fill="{P["c"][1]}"/>')


def s23_anneaux(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    cx, cy, R = W * 0.4, H * 0.5, 230 * k
    if P["sombre"]:
        c += etoiles(W, H, 200, P["c"][3], 23, k)
    d += lg("pl", P["c"][3], P["c"][0], 1, 1)
    for i in range(5):
        c += f'<ellipse cx="{cx}" cy="{cy}" rx="{R * (1.6 + i * 0.18):.1f}" ry="{R * (0.32 + i * 0.04):.1f}" transform="rotate(-18 {cx} {cy})" fill="none" stroke="{P["c"][i % 3]}" stroke-width="{(16 - i * 2) * k:.1f}" opacity="0.55"/>'
    c += f'<circle cx="{cx}" cy="{cy}" r="{R:.1f}" fill="url(#pl)"/>'
    d += f'<clipPath id="av"><rect x="0" y="{cy:.1f}" width="{W}" height="{H}"/></clipPath>'
    c += '<g clip-path="url(#av)">' + "".join(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{R * (1.6 + i * 0.18):.1f}" ry="{R * (0.32 + i * 0.04):.1f}" transform="rotate(-18 {cx} {cy})" fill="none" stroke="{P["c"][i % 3]}" stroke-width="{(16 - i * 2) * k:.1f}" opacity="0.9"/>'
        for i in range(5)) + "</g>"
    return doc(W, H, d, c)


def s24_galaxie(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    cx, cy = W * 0.55, H * 0.5
    d2, c2 = halo("co", cx, cy, 300 * k, P["c"][3], 0.8)
    d, c = d + d2, c + c2
    rnd = random.Random(24)
    for i in range(2600):
        bras = i % 3
        t = rnd.random() ** 0.7 * 5
        a = t * 1.3 + bras * 2.09 + rnd.gauss(0, 0.25)
        r = t * 110 * k
        x, y = cx + r * math.cos(a), cy + r * math.sin(a) * 0.55
        c += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(0.6, 2.4) * k:.1f}" fill="{P["c"][bras]}" opacity="{rnd.uniform(0.3, 0.9):.2f}"/>'
    return doc(W, H, d, c)


def s25_blobs(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(25)
    for b in range(6):
        cx, cy, r = rnd.uniform(0, 1) * W, rnd.uniform(0, 1) * H, rnd.uniform(200, 420) * k
        n = 8
        p = []
        for i in range(n):
            a = i * 2 * math.pi / n
            rr = r * rnd.uniform(0.75, 1.2)
            p.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        chemin = f"M{(p[0][0] + p[-1][0]) / 2:.1f},{(p[0][1] + p[-1][1]) / 2:.1f} "
        for i in range(n):
            a, b2 = p[i], p[(i + 1) % n]
            chemin += f"Q{a[0]:.1f},{a[1]:.1f} {(a[0] + b2[0]) / 2:.1f},{(a[1] + b2[1]) / 2:.1f} "
        d += lg(f"g{b}", P["c"][b % 4], P["c"][(b + 1) % 4], 1, 1)
        c += f'<path d="{chemin}Z" fill="url(#g{b})" opacity="0.75"/>'
    return doc(W, H, d, c)


def s26_flux(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(26)
    for i in range(260):
        x, y = rnd.random() * W, rnd.random() * H
        l = [(x, y)]
        for _ in range(60):
            a = math.sin(x / W * 4) * 1.5 + math.cos(y / H * 5) * 1.2
            x += math.cos(a) * 8 * k
            y += math.sin(a) * 8 * k
            l.append((x, y))
        c += f'<polyline points="{pts(l)}" fill="none" stroke="{P["c"][i % 4]}" stroke-width="{rnd.uniform(1, 3) * k:.1f}" stroke-linecap="round" opacity="{rnd.uniform(0.3, 0.8):.2f}"/>'
    return doc(W, H, d, c)


def s27_mosaique(W, H, P):
    d, c = fond(W, H, P)
    rnd = random.Random(27)

    def couper(x, y, w, h, n):
        nonlocal c
        if n == 0 or (w < W * 0.08 and h < H * 0.08):
            col = P["c"][rnd.randrange(4)] if rnd.random() < 0.55 else P["bg"][rnd.randrange(2)]
            c += f'<rect x="{x + 3:.1f}" y="{y + 3:.1f}" width="{w - 6:.1f}" height="{h - 6:.1f}" rx="10" fill="{col}" opacity="0.9"/>'
            return
        if w > h:
            t = rnd.uniform(0.3, 0.7) * w
            couper(x, y, t, h, n - 1); couper(x + t, y, w - t, h, n - 1)
        else:
            t = rnd.uniform(0.3, 0.7) * h
            couper(x, y, w, t, n - 1); couper(x, y + t, w, h - t, n - 1)
    couper(0, 0, W, H, 6)
    return doc(W, H, d, c)


def s28_mondrian(W, H, P):
    k = K(W, H)
    clair = "#F7F4EC" if P["sombre"] else P["bg"][0]
    trait = P["bg"][1] if P["sombre"] else "#1A1A1A"
    c = f'<rect width="{W}" height="{H}" fill="{clair}"/>'
    xs = [0, W * 0.18, W * 0.52, W * 0.71, W]
    ys = [0, H * 0.3, H * 0.62, H]
    rnd = random.Random(28)
    for i in range(4):
        for j in range(3):
            if rnd.random() < 0.4:
                c += f'<rect x="{xs[i]:.1f}" y="{ys[j]:.1f}" width="{xs[i + 1] - xs[i]:.1f}" height="{ys[j + 1] - ys[j]:.1f}" fill="{P["c"][(i + j) % 4]}"/>'
    for x in xs[1:-1]:
        c += f'<rect x="{x - 9 * k:.1f}" y="0" width="{18 * k:.1f}" height="{H}" fill="{trait}"/>'
    for y in ys[1:-1]:
        c += f'<rect x="0" y="{y - 9 * k:.1f}" width="{W}" height="{18 * k:.1f}" fill="{trait}"/>'
    return doc(W, H, "", c)


def s29_code_barre(W, H, P):
    d, c = fond(W, H, P)
    rnd = random.Random(29)
    x = 0
    while x < W:
        w = rnd.choice([4, 8, 14, 24, 40]) * K(W, H)
        c += f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="{H}" fill="{P["c"][rnd.randrange(4)]}" opacity="{rnd.uniform(0.2, 0.9):.2f}"/>'
        x += w + rnd.choice([2, 6, 12]) * K(W, H)
    d += lg("v", "#000000", "#000000", 0, 1, 0, 0.45 if P["sombre"] else 0.15)
    return doc(W, H, d, c + f'<rect width="{W}" height="{H}" fill="url(#v)"/>')


def s30_chevrons(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    s = 110 * k
    for j in range(int(H / s) + 2):
        l = []
        for i in range(int(W / s) + 2):
            l.append((i * s, j * s + (s / 2 if i % 2 else 0)))
        c += f'<polyline points="{pts(l)}" fill="none" stroke="{P["c"][j % 4]}" stroke-width="{s * 0.28:.1f}" stroke-linejoin="miter" opacity="0.8"/>'
    return doc(W, H, d, c)


def s31_losanges(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    w, h = 140 * k, 220 * k
    for j in range(-1, int(H / h * 2) + 2):
        for i in range(-1, int(W / w) + 2):
            x, y = i * w + (w / 2 if j % 2 else 0), j * h / 2
            c += f'<polygon points="{pts([(x, y - h / 2), (x + w / 2, y), (x, y + h / 2), (x - w / 2, y)])}" fill="{P["c"][(i + j) % 4]}" opacity="{0.25 + 0.5 * ((i * 7 + j * 3) % 5) / 5:.2f}"/>'
    for j in range(-2, int(W / w) * 2):
        c += f'<line x1="{j * w:.1f}" y1="0" x2="{j * w + H * w / h:.1f}" y2="{H}" stroke="{P["bg"][0]}" stroke-width="{2 * k:.1f}" stroke-dasharray="{8 * k:.1f} {8 * k:.1f}" opacity="0.6"/>'
    return doc(W, H, d, c)


def s32_pois(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    s = 80 * k
    for j in range(int(H / s) + 2):
        for i in range(int(W / s) + 2):
            x, y = i * s + (s / 2 if j % 2 else 0), j * s
            c += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s * 0.22:.1f}" fill="{P["c"][(i + j * 2) % 4]}" opacity="0.85"/>'
    return doc(W, H, d, c)


def s33_rosace(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    cx, cy = W * 0.5, H * 0.5
    for i in range(24):
        a = i * 15
        c += f'<ellipse cx="{cx}" cy="{cy - 180 * k:.1f}" rx="{70 * k:.1f}" ry="{180 * k:.1f}" transform="rotate({a} {cx} {cy})" fill="{P["c"][i % 4]}" fill-opacity="0.12" stroke="{P["c"][i % 4]}" stroke-width="{2.5 * k:.1f}" opacity="0.85"/>'
    c += f'<circle cx="{cx}" cy="{cy}" r="{40 * k:.1f}" fill="{P["c"][1]}"/>'
    return doc(W, H, d, c)


def s34_spirographe(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    cx, cy = W * 0.5, H * 0.5
    for m, (R, r, dd) in enumerate([(300, 113, 140), (260, 71, 120), (200, 47, 90)]):
        l = []
        for t in range(0, 6000):
            a = t / 40
            x = (R - r) * math.cos(a) + dd * math.cos((R - r) / r * a)
            y = (R - r) * math.sin(a) - dd * math.sin((R - r) / r * a)
            l.append((cx + x * k * 1.2, cy + y * k * 1.2))
        c += f'<polyline points="{pts(l)}" fill="none" stroke="{P["c"][m]}" stroke-width="{1.3 * k:.1f}" opacity="0.75"/>'
    return doc(W, H, d, c)


def s35_moire(W, H, P):
    k = K(W, H); d, c = base(W, H, P, False)
    for (cx, cy, col) in [(W * 0.38, H * 0.5, P["c"][0]), (W * 0.62, H * 0.5, P["c"][1])]:
        for i in range(1, 60):
            c += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{i * 16 * k:.1f}" fill="none" stroke="{col}" stroke-width="{4 * k:.1f}" opacity="0.5"/>'
    return doc(W, H, d, c)


def s36_tunnel(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    cx, cy = W * 0.5, H * 0.5
    for i in range(30, 0, -1):
        s = i * 60 * k
        c += f'<rect x="{cx - s:.1f}" y="{cy - s:.1f}" width="{2 * s:.1f}" height="{2 * s:.1f}" transform="rotate({i * 4} {cx} {cy})" fill="{P["c"][i % 4]}" opacity="{0.15 + 0.6 * (1 - i / 30):.2f}"/>'
    return doc(W, H, d, c)


def feuille(x, y, l, a, col, op, k):
    w = l * 0.35
    return (f'<path d="M0,0 Q{w:.1f},{-l / 2:.1f} 0,{-l:.1f} Q{-w:.1f},{-l / 2:.1f} 0,0 Z" fill="{col}" opacity="{op:.2f}" '
            f'transform="translate({x:.1f} {y:.1f}) rotate({a:.1f})"/>'
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + l * 0.95 * math.sin(math.radians(a)):.1f}" y2="{y - l * 0.95 * math.cos(math.radians(a)):.1f}" stroke="#FFFFFF" stroke-width="{1.5 * k:.1f}" opacity="0.25"/>')


def s37_feuillage(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(37)
    for i in range(140):
        c += feuille(rnd.random() * W, rnd.random() * H * 1.1, rnd.uniform(120, 340) * k, rnd.uniform(-60, 60) + (180 if rnd.random() < 0.3 else 0),
                     P["c"][i % 4], rnd.uniform(0.45, 0.9), k)
    return doc(W, H, d, c)


def s38_fleur(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    cx, cy = W * 0.62, H * 0.5
    for couche, (n, l) in enumerate([(12, 420), (10, 320), (8, 220)]):
        for i in range(n):
            c += feuille(cx, cy, l * k, i * 360 / n + couche * 15, P["c"][couche], 0.7, k)
    c += f'<circle cx="{cx}" cy="{cy}" r="{50 * k:.1f}" fill="{P["c"][3]}"/>'
    return doc(W, H, d, c)


def s39_collines_rondes(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    d2, c2 = halo("so", W * 0.25, H * 0.3, 260 * k, P["c"][3], 0.7)
    d, c = d + d2, c + c2 + f'<circle cx="{W * 0.25:.1f}" cy="{H * 0.3:.1f}" r="{80 * k:.1f}" fill="{P["c"][3]}"/>'
    for i, (x, y, r) in enumerate([(0.15, 1.25, 0.75), (0.75, 1.3, 0.8), (0.4, 1.45, 0.75), (0.95, 1.5, 0.7), (0.05, 1.6, 0.7)]):
        c += f'<circle cx="{W * x:.1f}" cy="{H * y:.1f}" r="{W * r * 0.6:.1f}" fill="{P["c"][i % 3]}" opacity="{0.7 + i * 0.06:.2f}"/>'
    return doc(W, H, d, c)


def s40_dunes_rayees(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    for i in range(5):
        ligne = crete(W, H, H * (0.45 + i * 0.12), H * 0.06, 400 + i)
        c += f'<path d="{sol(W, H, ligne)}" fill="{P["c"][i % 4]}" opacity="0.9"/>'
        for s in range(1, 4):
            dec = [(x, y + s * 14 * k) for x, y in ligne]
            c += f'<polyline points="{pts(dec)}" fill="none" stroke="{P["bg"][0]}" stroke-width="{2 * k:.1f}" opacity="0.3"/>'
    return doc(W, H, d, c)


def s41_bokeh(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(41)
    for i in range(60):
        x, y, r = rnd.random() * W, rnd.random() * H, rnd.uniform(20, 150) * k
        dd, cc = halo(f"bk{i}", x, y, r, P["c"][i % 4], rnd.uniform(0.3, 0.8))
        d += dd
        c += cc + f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 0.6:.1f}" fill="{P["c"][i % 4]}" opacity="0.18"/>'
    return doc(W, H, d, c)


def s42_minimal(W, H, P):
    d = lg("m", P["c"][0], P["c"][2], 1, 1)
    d2, c2 = halo("m2", W * 0.2, H * 0.85, max(W, H) * 0.6, P["c"][1], 0.7)
    c = f'<rect width="{W}" height="{H}" fill="url(#m)"/>' + c2
    rnd = random.Random(42)
    c += "".join(f'<circle cx="{rnd.random() * W:.1f}" cy="{rnd.random() * H:.1f}" r="0.9" fill="#FFFFFF" opacity="{rnd.random() * 0.15:.2f}"/>' for _ in range(int(W * H / 1800)))
    return doc(W, H, d + d2, c)


def s43_papier_decoupe(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    for i in range(6):
        ligne = crete(W, H, H * (0.2 + i * 0.14), H * 0.07, 430 + i, harm=3)
        ombre = [(x, y - 10 * k) for x, y in ligne]
        c += f'<path d="{sol(W, H, ombre)}" fill="#000000" opacity="0.18"/>'
        c += f'<path d="{sol(W, H, ligne)}" fill="{P["c"][i % 4]}"/>'
    return doc(W, H, d, c)


def s44_cristal(W, H, P):
    d, c = fond(W, H, P)
    cx, cy = W * 0.5, H * 0.5
    rnd = random.Random(44)
    n = 28
    R = math.hypot(W, H)
    for i in range(n):
        a0, a1 = i * 2 * math.pi / n, (i + 1) * 2 * math.pi / n
        r0 = rnd.uniform(0.05, 0.25) * H
        c += f'<polygon points="{pts([(cx + r0 * math.cos((a0 + a1) / 2), cy + r0 * math.sin((a0 + a1) / 2)), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))])}" fill="{P["c"][i % 4]}" opacity="{rnd.uniform(0.25, 0.75):.2f}"/>'
    return doc(W, H, d, c)


def s45_truchet_arcs(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    s = 80 * k
    rnd = random.Random(45)
    for j in range(int(H / s) + 1):
        for i in range(int(W / s) + 1):
            x, y = i * s, j * s
            col = P["c"][(i + j) % 4]
            if rnd.random() < 0.5:
                a = f"M{x + s / 2:.1f},{y:.1f} A{s / 2:.1f},{s / 2:.1f} 0 0 1 {x:.1f},{y + s / 2:.1f} M{x + s:.1f},{y + s / 2:.1f} A{s / 2:.1f},{s / 2:.1f} 0 0 0 {x + s / 2:.1f},{y + s:.1f}"
            else:
                a = f"M{x + s / 2:.1f},{y:.1f} A{s / 2:.1f},{s / 2:.1f} 0 0 0 {x + s:.1f},{y + s / 2:.1f} M{x:.1f},{y + s / 2:.1f} A{s / 2:.1f},{s / 2:.1f} 0 0 1 {x + s / 2:.1f},{y + s:.1f}"
            c += f'<path d="{a}" fill="none" stroke="{col}" stroke-width="{7 * k:.1f}" stroke-linecap="round" opacity="0.8"/>'
    return doc(W, H, d, c)


def s46_dix_print(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    s = 46 * k
    rnd = random.Random(46)
    for j in range(int(H / s) + 1):
        for i in range(int(W / s) + 1):
            x, y = i * s, j * s
            x1, x2 = (x, x + s) if rnd.random() < 0.5 else (x + s, x)
            c += f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y + s:.1f}" stroke="{P["c"][(i // 6 + j // 6) % 4]}" stroke-width="{5 * k:.1f}" stroke-linecap="round" opacity="0.75"/>'
    return doc(W, H, d, c)


def s47_circuit(W, H, P):
    k = K(W, H); d, c = base(W, H, P)
    rnd = random.Random(47)
    g = 40 * k
    for i in range(150):
        x, y = round(rnd.random() * W / g) * g, round(rnd.random() * H / g) * g
        l = [(x, y)]
        for _ in range(rnd.randint(3, 7)):
            dx, dy = rnd.choice([(1, 0), (0, 1), (1, 1), (-1, 1), (1, -1), (0, -1)])
            n = rnd.randint(1, 5)
            x, y = x + dx * g * n, y + dy * g * n
            l.append((x, y))
        col = P["c"][i % 4]
        c += f'<polyline points="{pts(l)}" fill="none" stroke="{col}" stroke-width="{3 * k:.1f}" stroke-linejoin="round" opacity="0.7"/>'
        c += f'<circle cx="{l[-1][0]:.1f}" cy="{l[-1][1]:.1f}" r="{7 * k:.1f}" fill="{P["bg"][1]}" stroke="{col}" stroke-width="{3 * k:.1f}"/>'
    return doc(W, H, d, c)


def s48_alveoles(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    s = 58 * k
    hw = math.sqrt(3) * s
    for j in range(-1, int(H / (1.5 * s)) + 2):
        for i in range(-1, int(W / hw) + 2):
            x, y = i * hw + (hw / 2 if j % 2 else 0), j * 1.5 * s
            t = (x / W + y / H) / 2
            col = P["c"][min(3, int(t * 4))]
            hexa = [(x + s * 0.94 * math.cos(math.radians(60 * m - 30)), y + s * 0.94 * math.sin(math.radians(60 * m - 30))) for m in range(6)]
            c += f'<polygon points="{pts(hexa)}" fill="{col}" opacity="{0.3 + 0.6 * abs(math.sin(i * 0.7 + j * 1.3)):.2f}"/>'
    return doc(W, H, d, c)


def s49_cometes(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    c += etoiles(W, H, 220, P["c"][3], 49, k)
    rnd = random.Random(49)
    for i in range(9):
        x, y = rnd.uniform(0.2, 1.1) * W, rnd.uniform(-0.1, 0.7) * H
        l = rnd.uniform(450, 900) * k
        d += lg(f"q{i}", P["c"][i % 3], P["c"][i % 3], 1, -0.5, 0, 0.95)
        c += f'<line x1="{x - l:.1f}" y1="{y + l * 0.5:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="url(#q{i})" stroke-width="{rnd.uniform(6, 14) * k:.1f}" stroke-linecap="round"/>'
        dd, cc = halo(f"qh{i}", x, y, 60 * k, P["c"][3], 0.8); d += dd; c += cc + f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{11 * k:.1f}" fill="{P["c"][3]}"/>'
    return doc(W, H, d, c)


def s50_horizon_minimal(W, H, P):
    k = K(W, H); d, c = fond(W, H, P)
    hz = H * 0.62
    d2, c2 = halo("so", W * 0.5, hz, H * 0.6, P["c"][0], 0.5)
    d, c = d + d2, c + c2
    d += f'<clipPath id="ho"><rect width="{W}" height="{hz:.1f}"/></clipPath>'
    c += f'<circle cx="{W / 2}" cy="{hz:.1f}" r="{H * 0.2:.1f}" fill="{P["c"][1]}" clip-path="url(#ho)"/>'
    c += f'<rect y="{hz:.1f}" width="{W}" height="{H - hz:.1f}" fill="{P["bg"][1]}"/>'
    for i in range(10):
        y = hz + (i + 1) * 12 * k * (1 + i * 0.4)
        w = H * 0.2 * (1 - i * 0.08) * 2
        c += f'<rect x="{W / 2 - w / 2:.1f}" y="{y:.1f}" width="{w:.1f}" height="{3 * k:.1f}" fill="{P["c"][1]}" opacity="{0.7 - i * 0.06:.2f}"/>'
    c += f'<line x1="0" y1="{hz:.1f}" x2="{W}" y2="{hz:.1f}" stroke="{P["c"][3]}" stroke-width="{2 * k:.1f}" opacity="0.7"/>'
    return doc(W, H, d, c)


STYLES = [
    ("Cercles décalés", s01_cercles_decales), ("Bandes diagonales", s02_bandes_diagonales),
    ("Damier", s03_damier_degrade), ("Trame", s04_trame_points), ("Lignes ondulées", s05_lignes_ondulees),
    ("Spirale", s06_spirale), ("Rayons", s07_rayons), ("Bulles", s08_bulles), ("Éclats", s09_eclats),
    ("Arcs", s10_arcs_empiles), ("Cubes", s11_cubes_iso), ("Écailles", s12_ecailles),
    ("Montagnes", s13_montagnes_angulaires), ("Lune et nuages", s14_lune_nuages), ("Forêt", s15_foret),
    ("Ville", s16_skyline), ("Soleil rayé", s17_soleil_raye), ("Synthwave", s18_synthwave), ("Aurore", s19_aurore),
    ("Pluie", s20_pluie), ("Constellations", s21_constellations), ("Atome", s22_atome), ("Anneaux", s23_anneaux),
    ("Galaxie", s24_galaxie), ("Galets", s25_blobs), ("Flux", s26_flux), ("Mosaïque", s27_mosaique),
    ("Mondrian", s28_mondrian), ("Code-barres", s29_code_barre), ("Chevrons", s30_chevrons),
    ("Losanges", s31_losanges), ("Pois", s32_pois), ("Rosace", s33_rosace), ("Spirographe", s34_spirographe),
    ("Moiré", s35_moire), ("Tunnel", s36_tunnel), ("Feuillage", s37_feuillage), ("Fleur", s38_fleur),
    ("Collines rondes", s39_collines_rondes), ("Dunes rayées", s40_dunes_rayees), ("Bokeh", s41_bokeh),
    ("Dégradé", s42_minimal), ("Papier découpé", s43_papier_decoupe), ("Cristal", s44_cristal),
    ("Labyrinthe", s45_truchet_arcs), ("Diagonales", s46_dix_print), ("Circuit", s47_circuit),
    ("Alvéoles", s48_alveoles), ("Comètes", s49_cometes), ("Horizon", s50_horizon_minimal),
]


def catalogue():
    """[(identifiant, nom du style, nom de la palette, fonction, palette)]"""
    out = []
    for i, (nom, f) in enumerate(STYLES):
        for p in palettes_du_style(i):
            out.append((f"{i + 1:02d}-{p}", nom, PALETTES[p]["nom"], f, PALETTES[p]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie")
    ap.add_argument("--largeur", type=int, default=1920)
    ap.add_argument("--hauteur", type=int, default=1080)
    ap.add_argument("--miniatures", type=int, default=0, help="largeur des miniatures (0 = aucune)")
    ap.add_argument("--seul", help="numéro de style (ex. 07)")
    ap.add_argument("--index", help="écrire la liste JSON ici")
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    cat = catalogue()
    if a.index:
        import json
        with open(a.index, "w", encoding="utf-8") as fo:
            json.dump([{"id": i, "style": s, "palette": p} for i, s, p, _, _ in cat], fo, ensure_ascii=False)
    for ident, nom, pal, f, P in cat:
        if a.seul and not ident.startswith(a.seul + "-"):
            continue
        rendre_png(f(a.largeur, a.hauteur, P), os.path.join(a.sortie, f"{ident}.png"), a.largeur, a.hauteur)
        if a.miniatures:
            mw = a.miniatures
            mh = round(mw * a.hauteur / a.largeur)
            os.makedirs(os.path.join(a.sortie, "mini"), exist_ok=True)
            rendre_png(f(a.largeur, a.hauteur, P), os.path.join(a.sortie, "mini", f"{ident}.png"), mw, mh)
        print(ident, nom, pal, flush=True)


if __name__ == "__main__":
    main()

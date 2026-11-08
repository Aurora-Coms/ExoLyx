#!/usr/bin/env python3
"""Collection de fonds d'écran ExoLyx (25 propositions).

    python3 src/wallpapers/outils/collection.py SORTIE [--largeur 1920 --hauteur 1080]

Chaque fond est une fonction (W, H) -> SVG, sans <filter> (voir docs/CONVENTIONS.md) :
les flous sont faits avec des dégradés radiaux. Les palettes sont volontairement
variées pour que l'accent de Plasma puisse suivre la couleur du fond.
"""

import argparse
import math
import os
import random
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import dessin as d  # noqa: E402


# ---------------------------------------------------------------- outils
def svg(W, H, defs, corps):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<defs>{defs}</defs>{corps}</svg>')


def lin(id_, stops, x1=0, y1=0, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in _st(stops))
    return f'<linearGradient id="{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>'


def rad(id_, stops, cx=0.5, cy=0.5, r=0.5, user=None):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in _st(stops))
    if user:
        x, y, rr = user
        return (f'<radialGradient id="{id_}" gradientUnits="userSpaceOnUse" cx="{x:.1f}" cy="{y:.1f}" '
                f'r="{rr:.1f}">{s}</radialGradient>')
    return f'<radialGradient id="{id_}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient>'


def _st(stops):
    for st in stops:
        yield st if len(st) == 3 else (st[0], st[1], 1)


def tache(id_, x, y, r, couleur, op=0.8):
    """Halo doux (remplace un flou gaussien)."""
    return (rad(id_, [(0, couleur, op), (0.45, couleur, op * 0.45), (1, couleur, 0)], user=(x, y, r)),
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="url(#{id_})"/>')


def fond_uni(W, H, haut, bas, id_="ciel"):
    return lin(id_, [(0, haut), (1, bas)]), f'<rect width="{W}" height="{H}" fill="url(#{id_})"/>'


def relief(W, H, base, ampl, graine, harmoniques=4, pas=12):
    """Ligne de crête (somme de sinus) fermée vers le bas -> chemin SVG."""
    rnd = random.Random(graine)
    comps = [(rnd.uniform(0.6, 1.0) / (i + 1) ** 1.1, rnd.uniform(1, 3) * (i + 1), rnd.uniform(0, 6.3))
             for i in range(harmoniques)]
    pts = []
    for x in range(0, W + pas, pas):
        t = x / W
        y = base + ampl * sum(a * math.sin(2 * math.pi * f * t + ph) for a, f, ph in comps)
        pts.append(f"{x},{y:.1f}")
    return f'M0,{H} L' + " L".join(pts) + f' L{W},{H} Z'


def ruban(W, H, y0, ampl, epaisseur, graine, freq=1.2, pas=16):
    """Bande ondulée (entre deux courbes décalées)."""
    rnd = random.Random(graine)
    ph, ph2 = rnd.uniform(0, 6.3), rnd.uniform(0, 6.3)
    haut, bas = [], []
    for x in range(-pas, W + 2 * pas, pas):
        t = x / W
        y = y0 + ampl * math.sin(2 * math.pi * freq * t + ph) + ampl * 0.35 * math.sin(2 * math.pi * freq * 2.3 * t + ph2)
        e = epaisseur * (0.55 + 0.45 * math.sin(2 * math.pi * 0.7 * t + ph2))
        haut.append((x, y - e / 2))
        bas.append((x, y + e / 2))
    pts = haut + bas[::-1]
    return "M" + " L".join(f"{x},{y:.1f}" for x, y in pts) + " Z"


def etoiles(W, H, n, couleurs, graine, eviter=None, rmax=1.6):
    rnd = random.Random(graine)
    k = min(W, H) / 1080
    s = []
    while len(s) < n:
        x, y = rnd.random() * W, rnd.random() * H
        if eviter and math.hypot(x - eviter[0], y - eviter[1]) < eviter[2]:
            continue
        r = (0.45 + rnd.random() ** 3 * rmax) * k
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{rnd.choice(couleurs)}" '
                 f'opacity="{0.15 + rnd.random() * 0.6:.2f}"/>')
    return "".join(s)


def scintille(x, y, r, couleur, op=0.9):
    """Étoile à 4 branches."""
    a, b = r, r * 0.16
    p = f"M{x},{y - a} Q{x + b},{y - b} {x + a},{y} Q{x + b},{y + b} {x},{y + a} Q{x - b},{y + b} {x - a},{y} Q{x - b},{y - b} {x},{y - a} Z"
    return f'<path d="{p}" fill="{couleur}" opacity="{op}"/>'


def palette(accent, clair, froid, lune, planete):
    """Palette au format de dessin.py, pour redessiner le logo dans une autre teinte."""
    p = dict(d.SOMBRE)
    p.update(accent=accent, accent_clair=clair, accent_froid=froid, lune=lune, reflet="#FFFFFF",
             orbiteA=(clair, froid), orbiteB=(accent, lune), planete=planete)
    return p


def logo(W, H, cx, cy, r, p, espace, pre="l", halo=True):
    defs = d.defs_logo(p, pre) + d.clips(cx, cy, W, H, pre) + d.defs_espace(cx, cy, r, espace, pre)
    return defs, d.logo_complet(cx, cy, r, p, W, H, f"url(#{pre}espace)", pre, halo)


def k_(W, H):
    return min(H, W * 9 / 16) / 1080


# ---------------------------------------------------------------- famille 1 : orbites
def orbites(W, H, fond, p, espace, place=(0.5, 0.5), echelle=0.2, n_et=150, grandes=True, graine=1):
    k = k_(W, H)
    cx, cy, r = W * place[0], H * place[1], echelle * 1080 * k
    diag = math.hypot(W, H)
    defs = rad("f", [(0, fond[0]), (0.3, fond[1]), (1, fond[2])], user=(cx, cy, diag * 0.75))
    corps = f'<rect width="{W}" height="{H}" fill="url(#f)"/>'
    corps += etoiles(W, H, n_et, ["#FFFFFF", p["accent_clair"]], graine, (cx, cy, r * 1.7))
    if grandes:
        for i, (fx, fy, ang, op) in enumerate([(3.0, 0.95, -24, 0.30), (4.5, 1.3, 24, 0.18), (6.5, 1.8, -16, 0.10)]):
            dash = ' stroke-dasharray="2 14"' if i == 2 else ""
            corps += (f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{fx * r:.1f}" ry="{fy * r:.1f}" '
                      f'transform="rotate({ang} {cx:.1f} {cy:.1f})" fill="none" stroke="{p["accent_clair"]}" '
                      f'stroke-width="{2.4 * k:.2f}" opacity="{op}"{dash}/>')
    dl, cl = logo(W, H, cx, cy, r, p, espace)
    return svg(W, H, defs + dl, corps + cl)


VERT = d.SOMBRE


def f01_orbite_nocturne(W, H):
    return orbites(W, H, ("#1C2D1F", "#111A14", "#070B08"), VERT, "#0F1712", (0.5, 0.48), 0.19, graine=3)


def f02_emeraude(W, H):
    p = palette("#3FD49B", "#7BE8B9", "#22B07D", "#C9F7E3", ("#D9FBEA", "#6FE0AE", "#1E8F63", "#0A2D21"))
    return orbites(W, H, ("#0E2D24", "#08191A", "#030A0B"), p, "#071615", (0.3, 0.55), 0.17, graine=5)


def f03_horizon_orbital(W, H):
    """Planète géante qui se lève en bas de l'écran."""
    k = k_(W, H)
    cx, cy, R = W * 0.5, H * 1.55, H * 1.05
    defs = lin("ciel", [(0, "#050806"), (0.6, "#0F1A12"), (1, "#1E3320")])
    defs += rad("pl", [(0, "#E4F5B8"), (0.35, "#A8D479"), (0.7, "#3E6B2C"), (1, "#0D1A0E")], 0.5, 0.0, 0.9)
    defs += rad("atm", [(0.9, "#BDD479", 0), (0.955, "#BDD479", 0.55), (1, "#BDD479", 0)], user=(cx, cy, R * 1.06))
    corps = f'<rect width="{W}" height="{H}" fill="url(#ciel)"/>'
    corps += etoiles(W, H, 260, ["#FFFFFF", "#E4F5B8"], 8)
    corps += f'<circle cx="{cx}" cy="{cy}" r="{R * 1.06:.1f}" fill="url(#atm)"/>'
    corps += f'<circle cx="{cx}" cy="{cy}" r="{R:.1f}" fill="url(#pl)"/>'
    for i, op in enumerate((0.5, 0.25)):
        corps += (f'<ellipse cx="{cx}" cy="{cy}" rx="{R * (1.5 + i * 0.35):.1f}" ry="{R * (0.42 + i * 0.12):.1f}" '
                  f'transform="rotate(-6 {cx} {cy})" fill="none" stroke="#BDD479" stroke-width="{3 * k:.1f}" opacity="{op}"/>')
    corps += f'<circle cx="{W * 0.78:.1f}" cy="{H * 0.22:.1f}" r="{14 * k:.1f}" fill="#E4F5B8"/>'
    corps += scintille(W * 0.22, H * 0.18, 26 * k, "#FFFFFF", 0.85)
    return svg(W, H, defs, corps)


def f04_aube_claire(W, H):
    k = k_(W, H)
    cx, cy, r = W * 0.62, H * 0.46, 210 * k
    defs = rad("f", [(0, "#FFFFFF"), (0.35, "#F2F8EC"), (1, "#DCE9D2")], user=(cx, cy, math.hypot(W, H) * 0.7))
    corps = f'<rect width="{W}" height="{H}" fill="url(#f)"/>'
    for i in range(7):
        corps += (f'<ellipse cx="{cx}" cy="{cy}" rx="{r * (2.2 + i * 0.9):.1f}" ry="{r * (0.75 + i * 0.3):.1f}" '
                  f'transform="rotate(-18 {cx} {cy})" fill="none" stroke="#7DB547" stroke-width="{1.6 * k:.2f}" '
                  f'opacity="{0.35 - i * 0.04:.2f}"/>')
    dl, cl = logo(W, H, cx, cy, r, d.CLAIR, "#F6FAF3")
    return svg(W, H, defs + dl, corps + cl)


# ---------------------------------------------------------------- famille 2 : paysages en couches
def paysage(W, H, ciel, couches, astre=None, et=0, graine=10, brume=None):
    k = k_(W, H)
    defs, corps = fond_uni(W, H, *ciel)
    if et:
        corps += etoiles(W, H, et, ["#FFFFFF"], graine)
    if astre:
        x, y, r, c, halo = astre
        dd, cc = tache("astreh", W * x, H * y, r * k * 4, halo, 0.55)
        defs += dd
        corps += cc + f'<circle cx="{W * x:.1f}" cy="{H * y:.1f}" r="{r * k:.1f}" fill="{c}"/>'
    n = len(couches)
    for i, (coul, base, ampl) in enumerate(couches):
        corps += f'<path d="{relief(W, H, H * base, H * ampl, graine + i * 7)}" fill="{coul}"/>'
        if brume and i < n - 1:
            defs += lin(f"br{i}", [(0, brume, 0), (1, brume, 0.22)])
            corps += f'<rect y="{H * (base - ampl):.1f}" width="{W}" height="{H * (1 - base + ampl):.1f}" fill="url(#br{i})"/>'
    return svg(W, H, defs, corps)


def f05_dunes_dorees(W, H):
    return paysage(W, H, ("#2B1B3A", "#F2A65A"),
                   [("#C9783F", 0.62, 0.05), ("#A85A2E", 0.72, 0.06), ("#7E3F22", 0.82, 0.05), ("#4F2617", 0.92, 0.04)],
                   astre=(0.7, 0.5, 70, "#FFE3A3", "#FFC36B"), graine=21)


def f06_collines_pomme(W, H):
    return paysage(W, H, ("#E9F6D3", "#BDD479"),
                   [("#A8D479", 0.55, 0.06), ("#8DC05E", 0.66, 0.06), ("#6FA845", 0.77, 0.05), ("#4E8F3A", 0.88, 0.05), ("#2B4F26", 0.97, 0.03)],
                   astre=(0.25, 0.28, 60, "#FFFFFF", "#FFFFFF"), graine=33, brume="#FFFFFF")


def f07_crepuscule_alpin(W, H):
    return paysage(W, H, ("#0B1530", "#3A5A9B"),
                   [("#34508A", 0.5, 0.12), ("#263E70", 0.62, 0.1), ("#1A2C55", 0.74, 0.08), ("#0F1C3A", 0.86, 0.06)],
                   astre=(0.78, 0.2, 34, "#F4F1E4", "#9DB6F0"), et=220, graine=44, brume="#7FA0E0")


def f08_volcan(W, H):
    k = k_(W, H)
    base = paysage(W, H, ("#14070A", "#6E1D1A"),
                   [("#3A1210", 0.66, 0.05), ("#240B0A", 0.8, 0.06), ("#120605", 0.92, 0.03)], et=90, graine=55)
    dd, cc = tache("lave", W * 0.5, H * 0.66, 520 * k, "#FF6A2B", 0.55)
    return base.replace("<defs>", "<defs>" + dd, 1).replace("</defs>", "</defs>", 1).replace(
        '<path d="M0', cc + '<path d="M0', 1)


def f09_brume_lavande(W, H):
    return paysage(W, H, ("#F3ECFA", "#C7B6E8"),
                   [("#B3A0DB", 0.52, 0.07), ("#9783C6", 0.64, 0.07), ("#7A66AE", 0.76, 0.06), ("#5A4890", 0.88, 0.05)],
                   astre=(0.68, 0.3, 80, "#FFFFFF", "#FFFFFF"), graine=66, brume="#FFFFFF")


# ---------------------------------------------------------------- famille 3 : rubans
def rubans(W, H, ciel, couleurs, graine, lueur=None):
    defs, corps = fond_uni(W, H, *ciel)
    if lueur:
        dd, cc = tache("lu", W * lueur[0], H * lueur[1], max(W, H) * 0.55, lueur[2], 0.45)
        defs += dd
        corps += cc
    n = len(couleurs)
    for i, (c0, c1, op) in enumerate(couleurs):
        defs += lin(f"r{i}", [(0, c0), (1, c1)], 0, 0, 1, 0)
        y0 = H * (0.3 + 0.5 * i / max(1, n - 1))
        corps += (f'<path d="{ruban(W, H, y0, H * 0.12, H * (0.22 - 0.02 * i), graine + i, 0.8 + 0.15 * i)}" '
                  f'fill="url(#r{i})" opacity="{op}"/>')
    return svg(W, H, defs, corps)


def f10_vagues_pomme(W, H):
    return rubans(W, H, ("#0A120C", "#132016"),
                  [("#2B4F26", "#6FA845", 0.85), ("#4E8F3A", "#A8D479", 0.8), ("#8DD479", "#E4F5B8", 0.75), ("#BDD479", "#5E9B2E", 0.6)],
                  71, (0.8, 0.2, "#A8D479"))


def f11_ocean(W, H):
    return rubans(W, H, ("#021526", "#04314D"),
                  [("#05476B", "#0A7FA3", 0.85), ("#0B8DB5", "#3FD0D4", 0.8), ("#5CE1E6", "#B6F5F2", 0.7), ("#1E6E9C", "#0B3A5C", 0.85)],
                  82, (0.2, 0.15, "#3FD0D4"))


def f12_corail(W, H):
    return rubans(W, H, ("#FFF4EC", "#FFD9C7"),
                  [("#FFB199", "#FF7E6B", 0.8), ("#FF8F80", "#E8556D", 0.75), ("#F7C59F", "#FF9F7A", 0.8), ("#E8556D", "#B83B5E", 0.7)],
                  93, (0.85, 0.15, "#FFFFFF"))


def f13_neon(W, H):
    return rubans(W, H, ("#07020F", "#120626"),
                  [("#6A1BFF", "#B04BFF", 0.8), ("#FF3DCB", "#7A2BFF", 0.7), ("#3AE0FF", "#6A1BFF", 0.65), ("#B04BFF", "#FF3DCB", 0.6)],
                  104, (0.5, 0.5, "#7A2BFF"))


# ---------------------------------------------------------------- famille 4 : topographie
def topo(W, H, fond, trait, accent, graine, n=26, clair=False):
    """Courbes de niveau autour de quelques sommets."""
    k = k_(W, H)
    rnd = random.Random(graine)
    defs, corps = fond_uni(W, H, *fond)
    sommets = [(rnd.uniform(0.15, 0.85) * W, rnd.uniform(0.2, 0.8) * H, rnd.uniform(0.6, 1.0)) for _ in range(3)]
    for (sx, sy, force), coul in zip(sommets, (accent, trait, trait)):
        ph = [rnd.uniform(0, 6.3) for _ in range(3)]
        for i in range(1, n + 1):
            r0 = i * 38 * k * force
            pts = []
            for a in range(0, 361, 6):
                t = math.radians(a)
                rr = r0 * (1 + 0.18 * math.sin(3 * t + ph[0] + i * 0.08) + 0.1 * math.sin(5 * t + ph[1]) + 0.06 * math.sin(2 * t + ph[2]))
                pts.append(f"{sx + rr * math.cos(t):.1f},{sy + rr * math.sin(t) * 0.8:.1f}")
            op = (0.9 if i % 5 == 0 else 0.45) * (1 - i / (n + 6))
            corps += (f'<path d="M{" L".join(pts)} Z" fill="none" stroke="{coul}" '
                      f'stroke-width="{(3.2 if i % 5 == 0 else 1.8) * k:.2f}" opacity="{op:.2f}"/>')
    sx, sy, _ = sommets[0]
    corps += f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{7 * k:.1f}" fill="{accent}"/>'
    corps += f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{16 * k:.1f}" fill="none" stroke="{accent}" stroke-width="{2 * k:.1f}" opacity="0.6"/>'
    return svg(W, H, defs, corps)


def f14_topo_nuit(W, H):
    return topo(W, H, ("#0F1712", "#0A100C"), "#97A893", "#A8D479", 7)


def f15_topo_sable(W, H):
    return topo(W, H, ("#F6EFE3", "#EADFCB"), "#9C8463", "#C0703A", 12, clair=True)


# ---------------------------------------------------------------- famille 5 : dégradés doux
def nuage(W, H, base, taches, graine):
    defs, corps = fond_uni(W, H, *base)
    m = max(W, H)
    for i, (x, y, r, c, op) in enumerate(taches):
        dd, cc = tache(f"t{i}", W * x, H * y, m * r, c, op)
        defs += dd
        corps += cc
    # grain très léger : petits points
    rnd = random.Random(graine)
    corps += "".join(f'<circle cx="{rnd.random() * W:.1f}" cy="{rnd.random() * H:.1f}" r="0.8" fill="#FFFFFF" '
                     f'opacity="{rnd.random() * 0.12:.2f}"/>' for _ in range(int(W * H / 2500)))
    return svg(W, H, defs, corps)


def f16_menthe(W, H):
    return nuage(W, H, ("#EAF8EE", "#D4F0DD"),
                 [(0.15, 0.2, 0.45, "#A8E6C1", 0.8), (0.85, 0.3, 0.4, "#BDD479", 0.7), (0.5, 0.95, 0.5, "#7FD1B9", 0.7),
                  (0.75, 0.75, 0.3, "#E4F5B8", 0.8)], 1)


def f17_peche(W, H):
    return nuage(W, H, ("#FFF1E6", "#FFDCC6"),
                 [(0.2, 0.75, 0.5, "#FFB38A", 0.8), (0.8, 0.2, 0.45, "#FF9FA8", 0.7), (0.55, 0.45, 0.3, "#FFE0A3", 0.8),
                  (0.95, 0.9, 0.35, "#F58BB0", 0.6)], 2)


def f18_crepuscule_rose(W, H):
    return nuage(W, H, ("#1A0E33", "#3B1450"),
                 [(0.2, 0.85, 0.5, "#FF5E8A", 0.7), (0.85, 0.75, 0.45, "#FF9A5E", 0.6), (0.6, 0.15, 0.45, "#7A3BFF", 0.7),
                  (0.1, 0.1, 0.35, "#3B2BFF", 0.6)], 3)


def f19_glacier(W, H):
    return nuage(W, H, ("#EAF4FB", "#CFE3F2"),
                 [(0.1, 0.8, 0.5, "#9CCBEA", 0.8), (0.9, 0.15, 0.45, "#B9E6F0", 0.8), (0.55, 0.5, 0.3, "#FFFFFF", 0.9),
                  (0.8, 0.9, 0.35, "#7FB2E0", 0.6)], 4)


# ---------------------------------------------------------------- famille 6 : géométrique
def f20_hexagones(W, H):
    k = k_(W, H)
    defs, corps = fond_uni(W, H, "#121A15", "#080C0A")
    dd, cc = tache("lh", W * 0.7, H * 0.4, max(W, H) * 0.5, "#A8D479", 0.35)
    defs += dd
    corps += cc
    s = 64 * k
    hw, hh = math.sqrt(3) * s, 1.5 * s
    rnd = random.Random(20)
    cx0, cy0 = W * 0.7, H * 0.4
    y, row = -s, 0
    while y < H + s:
        x = -hw + (hw / 2 if row % 2 else 0)
        while x < W + hw:
            dist = math.hypot(x - cx0, y - cy0) / max(W, H)
            op = max(0.05, 0.8 - dist * 1.1)
            pts = " ".join(f"{x + s * 0.92 * math.cos(math.radians(60 * i - 30)):.1f},"
                           f"{y + s * 0.92 * math.sin(math.radians(60 * i - 30)):.1f}" for i in range(6))
            plein = rnd.random() < 0.06 * (1 - dist)
            corps += (f'<polygon points="{pts}" fill="{"#A8D479" if plein else "none"}" '
                      f'fill-opacity="{op * 0.6:.2f}" stroke="#A8D479" stroke-width="{2.2 * k:.2f}" opacity="{op + 0.04:.2f}"/>')
            x += hw
        y += hh
        row += 1
    return svg(W, H, defs, corps)


def f21_low_poly(W, H):
    """Triangles en dégradé turquoise -> vert."""
    rnd = random.Random(21)
    cols, rows = 16, 10
    pts = [[(W * (i / cols + (rnd.uniform(-0.3, 0.3) / cols if 0 < i < cols else 0)),
             H * (j / rows + (rnd.uniform(-0.3, 0.3) / rows if 0 < j < rows else 0)))
            for i in range(cols + 1)] for j in range(rows + 1)]

    def coul(x, y):
        t = (x / W * 0.6 + y / H * 0.4)
        c0, c1 = (0x0B, 0x3D, 0x4A), (0x8D, 0xD4, 0x79)
        v = 0.85 + 0.15 * rnd.random()
        return "#%02X%02X%02X" % tuple(int((a + (b - a) * t) * v) for a, b in zip(c0, c1))

    corps = ""
    for j in range(rows):
        for i in range(cols):
            a, b, c, e = pts[j][i], pts[j][i + 1], pts[j + 1][i], pts[j + 1][i + 1]
            for tri in ((a, b, e), (a, e, c)):
                mx, my = sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3
                corps += (f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in tri)}" fill="{coul(mx, my)}" '
                          f'stroke="{coul(mx, my)}" stroke-width="1"/>')
    return svg(W, H, "", corps)


def f22_bauhaus(W, H):
    k = k_(W, H)
    defs, corps = fond_uni(W, H, "#F3E9D6", "#EADBC0")
    cx, cy = W * 0.62, H * 0.52
    for i, (r, c) in enumerate([(420, "#D9893B"), (330, "#F3E9D6"), (250, "#2F5D50"), (170, "#F3E9D6"), (95, "#C2453A")]):
        corps += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * k:.1f}" fill="{c}"/>'
    corps += f'<rect x="{W * 0.12:.1f}" y="{H * 0.18:.1f}" width="{140 * k:.1f}" height="{H * 0.64:.1f}" fill="#2F5D50"/>'
    corps += f'<path d="M{W * 0.12:.1f},{H * 0.82:.1f} A{300 * k:.1f},{300 * k:.1f} 0 0 1 {W * 0.12 + 600 * k:.1f},{H * 0.82:.1f} Z" fill="#E3B04B"/>'
    corps += f'<line x1="0" y1="{H * 0.82:.1f}" x2="{W}" y2="{H * 0.82:.1f}" stroke="#1E2A26" stroke-width="{4 * k:.1f}"/>'
    corps += f'<circle cx="{W * 0.86:.1f}" cy="{H * 0.2:.1f}" r="{40 * k:.1f}" fill="#1E2A26"/>'
    return svg(W, H, defs, corps)


# ---------------------------------------------------------------- famille 7 : cosmos
def f23_nebuleuse(W, H):
    k = k_(W, H)
    defs, corps = fond_uni(W, H, "#06030F", "#0B0518")
    for i, (x, y, r, c, op) in enumerate([(0.3, 0.4, 0.45, "#7A2BFF", 0.45), (0.45, 0.55, 0.35, "#FF3DCB", 0.3),
                                          (0.2, 0.6, 0.3, "#3AE0FF", 0.25), (0.6, 0.3, 0.25, "#B04BFF", 0.3)]):
        dd, cc = tache(f"n{i}", W * x, H * y, max(W, H) * r, c, op)
        defs += dd
        corps += cc
    corps += etoiles(W, H, 420, ["#FFFFFF", "#E5D4FF", "#BFF4FF"], 23, rmax=2.2)
    cx, cy, R = W * 0.74, H * 0.62, 150 * k
    defs += rad("pv", [(0, "#F3E6FF"), (0.4, "#B98BFF"), (0.8, "#4B1F8F"), (1, "#1A0B33")], 0.35, 0.3, 0.8)
    corps += (f'<ellipse cx="{cx}" cy="{cy}" rx="{R * 2.3:.1f}" ry="{R * 0.5:.1f}" transform="rotate(-14 {cx} {cy})" '
              f'fill="none" stroke="#E5D4FF" stroke-width="{10 * k:.1f}" opacity="0.35"/>')
    corps += f'<circle cx="{cx}" cy="{cy}" r="{R:.1f}" fill="url(#pv)"/>'
    corps += (f'<path d="M{cx - R * 2.3:.1f},{cy} A{R * 2.3:.1f},{R * 0.5:.1f} 0 0 0 {cx + R * 2.3:.1f},{cy}" '
              f'transform="rotate(-14 {cx} {cy})" fill="none" stroke="#E5D4FF" stroke-width="{10 * k:.1f}" opacity="0.7"/>')
    corps += scintille(W * 0.15, H * 0.2, 30 * k, "#FFFFFF") + scintille(W * 0.9, H * 0.12, 18 * k, "#E5D4FF")
    return svg(W, H, defs, corps)


def f24_eclipse(W, H):
    k = k_(W, H)
    cx, cy, R = W * 0.5, H * 0.45, 230 * k
    defs, corps = fond_uni(W, H, "#050403", "#0E0A05")
    defs += rad("cou", [(0.82, "#FFD27A", 0), (0.9, "#FFD27A", 0.9), (0.94, "#FFB347", 0.5), (1, "#FF8A00", 0)], user=(cx, cy, R * 1.12))
    defs += rad("cor", [(0, "#FFB347", 0.35), (0.4, "#FF8A00", 0.12), (1, "#FF8A00", 0)], user=(cx, cy, R * 3.2))
    corps += etoiles(W, H, 160, ["#FFFFFF", "#FFE7B8"], 24, (cx, cy, R * 2))
    corps += f'<circle cx="{cx}" cy="{cy}" r="{R * 3.2:.1f}" fill="url(#cor)"/>'
    corps += f'<circle cx="{cx}" cy="{cy}" r="{R * 1.12:.1f}" fill="url(#cou)"/>'
    corps += f'<circle cx="{cx}" cy="{cy}" r="{R:.1f}" fill="#050403"/>'
    corps += f'<circle cx="{cx + R * 0.72:.1f}" cy="{cy - R * 0.72:.1f}" r="{9 * k:.1f}" fill="#FFF3D6"/>'
    return svg(W, H, defs, corps)


def f25_oled(W, H):
    k = k_(W, H)
    cx, cy, r = W * 0.5, H * 0.5, 170 * k
    corps = f'<rect width="{W}" height="{H}" fill="#000000"/>'
    for i, (fx, fy, ang, op) in enumerate([(1.7, 0.58, -24, 1), (1.7, 0.58, 24, 1), (4.2, 1.3, -24, 0.4), (6.8, 2.0, 24, 0.22)]):
        corps += (f'<ellipse cx="{cx}" cy="{cy}" rx="{fx * r:.1f}" ry="{fy * r:.1f}" transform="rotate({ang} {cx} {cy})" '
                  f'fill="none" stroke="#A8D479" stroke-width="{(7 if i < 2 else 2.5) * k:.1f}" opacity="{op}"/>')
    corps += f'<circle cx="{cx}" cy="{cy}" r="{r * 0.62:.1f}" fill="#A8D479" stroke="#BDD479" stroke-width="{3 * k:.1f}"/>'
    corps += f'<circle cx="{cx + r * 1.48:.1f}" cy="{cy - r * 0.66:.1f}" r="{8 * k:.1f}" fill="#E4F5B8"/>'
    return svg(W, H, "", corps)


FONDS = [
    ("01", "Orbite nocturne", f01_orbite_nocturne),
    ("02", "Émeraude", f02_emeraude),
    ("03", "Horizon orbital", f03_horizon_orbital),
    ("04", "Aube claire", f04_aube_claire),
    ("05", "Dunes dorées", f05_dunes_dorees),
    ("06", "Collines pomme", f06_collines_pomme),
    ("07", "Crépuscule alpin", f07_crepuscule_alpin),
    ("08", "Volcan", f08_volcan),
    ("09", "Brume lavande", f09_brume_lavande),
    ("10", "Vagues pomme", f10_vagues_pomme),
    ("11", "Océan", f11_ocean),
    ("12", "Corail", f12_corail),
    ("13", "Néon", f13_neon),
    ("14", "Topographie nuit", f14_topo_nuit),
    ("15", "Topographie sable", f15_topo_sable),
    ("16", "Menthe", f16_menthe),
    ("17", "Pêche", f17_peche),
    ("18", "Crépuscule rose", f18_crepuscule_rose),
    ("19", "Glacier", f19_glacier),
    ("20", "Ruche", f20_hexagones),
    ("21", "Facettes", f21_low_poly),
    ("22", "Bauhaus", f22_bauhaus),
    ("23", "Nébuleuse", f23_nebuleuse),
    ("24", "Éclipse", f24_eclipse),
    ("25", "OLED", f25_oled),
]


def rendre_png(svg_txt, chemin, W, H):
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_txt.encode(), write_to=chemin, output_width=W, output_height=H)
    except (ImportError, OSError):
        import resvg_py  # repli sous Windows (pas de libcairo)
        with open(chemin, "wb") as f:
            f.write(bytes(resvg_py.svg_to_bytes(svg_string=svg_txt, width=W, height=H)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie")
    ap.add_argument("--largeur", type=int, default=1920)
    ap.add_argument("--hauteur", type=int, default=1080)
    ap.add_argument("--seul", help="numéro à générer (ex. 07)")
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    for num, nom, f in FONDS:
        if a.seul and num != a.seul:
            continue
        chemin = os.path.join(a.sortie, f"{num}.png")
        rendre_png(f(a.largeur, a.hauteur), chemin, a.largeur, a.hauteur)
        print(num, nom)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Génère les fonds d'écran ExoLyx (sombre et clair) au format paquet Plasma.

    python3 src/wallpapers/outils/generer.py [--apercu DOSSIER]

Produit :
  src/wallpapers/source/exolyx-{sombre,clair}.svg   (SVG maître 3840×2160)
  src/wallpapers/ExoLyx/{metadata.json,contents/screenshot.png,contents/images/*.png}
  src/wallpapers/ExoLyx-Clair/…

Le SVG est recomposé pour chaque rapport d'image (16:9, 16:10, 21:9…) afin
que la planète ne soit jamais déformée ni rognée. Nécessite cairosvg.
"""

import argparse
import io
import json
import os
import sys

import cairosvg

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import dessin as d  # noqa: E402

RACINE = os.path.dirname(ICI)  # src/wallpapers

TAILLES = [
    (1366, 768), (1920, 1080), (1920, 1200), (2560, 1080), (2560, 1440),
    (2560, 1600), (3440, 1440), (3840, 2160), (1080, 1920),
]

THEMES = {
    "ExoLyx": ("sombre", d.SOMBRE, "ExoLyx", "Fond d'écran ExoLyx sombre"),
    "ExoLyx-Clair": ("clair", d.CLAIR, "ExoLyx Clair", "Fond d'écran ExoLyx clair"),
}


def svg_fond(W, H, theme, avec_logo=True, centre=None):
    """SVG du fond. `avec_logo=False` : seulement le ciel et les grandes orbites
    (fond de GRUB). `centre` = (x, y) relatifs pour le centre des orbites."""
    p = d.SOMBRE if theme == "sombre" else d.CLAIR
    clair = theme == "clair"
    portrait = H > W
    base = min(H, W * 9 / 16) if not portrait else W * 0.9
    r = 0.20 * base
    cx = W * (0.5 if portrait else 0.635)
    cy = H * (0.42 if portrait else 0.47)
    if centre:
        cx, cy = W * centre[0], H * centre[1]

    if clair:
        f0, f1, f2, f3 = "#FFFFFF", "#F4F8F1", "#EDF3E8", "#E3ECDC"
        espace = "#F9FBF7"
    else:
        f0, f1, f2, f3 = "#1C2D1F", "#121C16", "#0D1310", "#090E0B"
        espace = "#0F1712"

    diag = (W ** 2 + H ** 2) ** 0.5
    defs = d.defs_logo(p, "l") + d.clips(cx, cy, W, H, "l") + d.defs_espace(cx, cy, r, espace, "l") + f"""
    <radialGradient id="fond" gradientUnits="userSpaceOnUse" cx="{cx:.1f}" cy="{cy:.1f}" r="{diag * 0.75:.1f}">
      <stop offset="0" stop-color="{f0}"/><stop offset="0.22" stop-color="{f1}"/>
      <stop offset="0.6" stop-color="{f2}"/><stop offset="1" stop-color="{f3}"/>
    </radialGradient>
    <radialGradient id="lueur" gradientUnits="userSpaceOnUse" cx="{W * 0.12:.1f}" cy="{H * 0.9:.1f}" r="{diag * 0.45:.1f}">
      <stop offset="0" stop-color="{p['accent_froid']}" stop-opacity="{0.10 if clair else 0.07}"/>
      <stop offset="1" stop-color="{p['accent_froid']}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="grandeA" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{p['accent']}" stop-opacity="0"/>
      <stop offset="0.5" stop-color="{p['accent_clair']}" stop-opacity="1"/>
      <stop offset="1" stop-color="{p['accent']}" stop-opacity="0.1"/>
    </linearGradient>
    <linearGradient id="grandeB" x1="1" y1="0" x2="0" y2="0">
      <stop offset="0" stop-color="{p['accent_froid']}" stop-opacity="0"/>
      <stop offset="0.55" stop-color="{p['accent']}" stop-opacity="1"/>
      <stop offset="1" stop-color="{p['accent_froid']}" stop-opacity="0.05"/>
    </linearGradient>"""

    k = base / 1080
    corps = [f'<rect width="{W}" height="{H}" fill="url(#fond)"/>',
             f'<rect width="{W}" height="{H}" fill="url(#lueur)"/>',
             d.etoiles(W, H, int(W * H / 14000), p, 11, (cx, cy, r * 1.6), clair)]

    # grandes orbites concentriques qui prolongent le logo dans tout l'écran
    grandes = [(3.1, 0.95, -24, "grandeA", 2.2, 0.30),
               (4.6, 1.30, 24, "grandeB", 1.6, 0.20),
               (6.6, 1.75, -16, "grandeA", 1.2, 0.13),
               (9.4, 2.30, 14, "grandeB", 1.0, 0.08)]
    for i, (fx, fy, ang, grad, ep, op) in enumerate(grandes):
        tiret = ' stroke-dasharray="2 14"' if i == 2 else ""
        corps.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{fx * r:.1f}" ry="{fy * r:.1f}" '
            f'transform="rotate({ang} {cx:.1f} {cy:.1f})" fill="none" stroke="url(#{grad})" '
            f'stroke-width="{ep * k * 1.6:.2f}" stroke-linecap="round" opacity="{op * (1.5 if clair else 1)}"{tiret}/>')
    # petits satellites posés sur les grandes orbites
    import math
    for (fx, fy, ang, _, _, op), t, rr in zip(grandes, (2.4, 5.6, 0.7, 3.9), (5, 4, 3.2, 2.6)):
        a = math.radians(ang)
        x0, y0 = fx * r * math.cos(t), fy * r * math.sin(t)
        x = cx + x0 * math.cos(a) - y0 * math.sin(a)
        y = cy + x0 * math.sin(a) + y0 * math.cos(a)
        corps.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr * k * 4:.1f}" fill="url(#lhalolune)" opacity="{min(1, op * 3):.2f}"/>')
        corps.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr * k * 1.3:.1f}" fill="{p["accent_clair"]}" opacity="{min(1, op * 3.5):.2f}"/>')

    if avec_logo:
        corps.append(d.logo_complet(cx, cy, r, p, W, H, "url(#lespace)", "l"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<defs>{defs}</defs>' + "".join(corps) + "</svg>")


def rendre(svg, chemin, W=None, H=None):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=chemin, output_width=W, output_height=H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apercu", help="dossier où écrire des aperçus réduits")
    ap.add_argument("--rapide", action="store_true", help="seulement 1920×1080 (tests)")
    a = ap.parse_args()

    for dossier, (theme, _p, nom, desc) in THEMES.items():
        maitre = svg_fond(3840, 2160, theme)
        os.makedirs(os.path.join(RACINE, "source"), exist_ok=True)
        with open(os.path.join(RACINE, "source", f"exolyx-{theme}.svg"), "w") as f:
            f.write(maitre)

        paquet = os.path.join(RACINE, dossier)
        meta = {"KPlugin": {
            "Authors": [{"Name": "A.DERBEZ"}],
            "Id": dossier,
            "License": "GPL-3.0-or-later",
            "Name": nom,
            "Description": desc,
        }}
        os.makedirs(os.path.join(paquet, "contents", "images"), exist_ok=True)
        with open(os.path.join(paquet, "metadata.json"), "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
            f.write("\n")

        tailles = [(1920, 1080)] if a.rapide else TAILLES
        for W, H in tailles:
            sortie = os.path.join(paquet, "contents", "images", f"{W}x{H}.png")
            rendre(svg_fond(W, H, theme), sortie)
            print("  ", os.path.relpath(sortie, RACINE))
        rendre(svg_fond(1920, 1080, theme), os.path.join(paquet, "contents", "screenshot.png"), 400, 225)

        if a.apercu:
            os.makedirs(a.apercu, exist_ok=True)
            rendre(svg_fond(1920, 1080, theme), os.path.join(a.apercu, f"wallpaper-{theme}.png"))
            rendre(svg_fond(1080, 1920, theme), os.path.join(a.apercu, f"wallpaper-{theme}-portrait.png"), 540, 960)
            rendre(svg_fond(3440, 1440, theme), os.path.join(a.apercu, f"wallpaper-{theme}-21x9.png"), 1720, 720)


if __name__ == "__main__":
    main()

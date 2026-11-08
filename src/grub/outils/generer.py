#!/usr/bin/env python3
"""Génère les images et polices du thème GRUB « exolyx ».

    python3 src/grub/outils/generer.py

Écrit dans src/grub/exolyx/ :
  fond.png                    ciel ExoLyx + grandes orbites (sans planète), 1920×1080
  logo.png                    logo 128×128 (src/branding/logo.svg)
  select_*.png                élément sélectionné (vert pomme, 9 morceaux)
  menu_*.png                  cadre du menu (9 morceaux)
  terminal_box_*.png          cadre de la console GRUB (9 morceaux)
  inter-*.pf2                 polices Inter converties par grub-mkfont

Nécessite cairosvg, Pillow, grub-mkfont et la police Inter (fc-match Inter).
Les polices Inter sont sous licence SIL OFL 1.1 (conversion autorisée).
"""

import io
import os
import subprocess
import sys

import cairosvg
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, "..", "..", ".."))
sys.path.insert(0, os.path.join(DEPOT, "src", "wallpapers", "outils"))
import dessin as d  # noqa: E402
import generer as fonds  # noqa: E402

THEME = os.path.join(DEPOT, "src", "grub", "exolyx")
P = d.SOMBRE

# Plages Unicode utiles : latin (français), ponctuation typographique, flèches.
PLAGES = "0x20-0x7E,0xA0-0x17F,0x2010-0x2027,0x2030-0x203A,0x20AC-0x20AC,0x2190-0x21FF,0x25B2-0x25BC"
POLICES = [  # (fichier Inter, taille px)
    ("Inter-Regular", 16), ("Inter-Regular", 20), ("Inter-Bold", 20), ("Inter-Bold", 30),
]


def ecrire(img, nom):
    chemin = os.path.join(THEME, nom)
    img.save(chemin, optimize=True)
    print("  ", os.path.relpath(chemin, DEPOT))


def svg_png(svg, w=None, h=None):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=w, output_height=h)))


def neuf_morceaux(prefixe, remplissage, bordure, rayon, epaisseur=0, opacite=1.0):
    """Cadre arrondi découpé en 9 PNG (nw, n, ne, w, c, e, sw, s, se) pour les
    styles « pixmap » de GRUB. Coins = rayon × rayon ; bords et centre 1 px
    d'épaisseur étirés par GRUB."""
    t = rayon * 2 + 4
    trait = (f'stroke="{bordure}" stroke-width="{epaisseur}"' if epaisseur else "")
    m = epaisseur / 2
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{t}" height="{t}">'
           f'<rect x="{m}" y="{m}" width="{t - 2 * m}" height="{t - 2 * m}" rx="{rayon - m}" '
           f'fill="{remplissage}" fill-opacity="{opacite}" {trait}/></svg>')
    img = svg_png(svg).convert("RGBA")
    r, c = rayon, t // 2
    boites = {
        "nw": (0, 0, r, r), "n": (c, 0, c + 1, r), "ne": (t - r, 0, t, r),
        "w": (0, c, r, c + 1), "c": (c, c, c + 1, c + 1), "e": (t - r, c, t, c + 1),
        "sw": (0, t - r, r, t), "s": (c, t - r, c + 1, t), "se": (t - r, t - r, t, t),
    }
    for nom, b in boites.items():
        ecrire(img.crop(b), f"{prefixe}_{nom}.png")


def police_inter(nom):
    try:
        chemin = subprocess.run(["fc-match", "-f", "%{file}", nom.replace("-", ":style=")],
                                capture_output=True, text=True, check=True).stdout.strip()
        if chemin and os.path.exists(chemin) and "Inter" in os.path.basename(chemin):
            return chemin
    except (OSError, subprocess.CalledProcessError):
        pass
    for base in ("/usr/share/fonts/inter", "/usr/share/fonts/opentype/inter", "/usr/share/fonts/OTF"):
        for ext in (".otf", ".ttf"):
            c = os.path.join(base, nom + ext)
            if os.path.exists(c):
                return c
    raise SystemExit(f"Police {nom} introuvable (installer inter-font)")


def main():
    os.makedirs(THEME, exist_ok=True)

    # fond : orbites centrées derrière le menu, sans planète (le logo est en haut)
    fond = svg_png(fonds.svg_fond(1920, 1080, "sombre", avec_logo=False, centre=(0.5, 0.52)))
    ecrire(fond.convert("RGB"), "fond.png")

    with open(os.path.join(DEPOT, "src", "branding", "logo.svg")) as f:
        ecrire(svg_png(f.read(), 128, 128), "logo.png")

    neuf_morceaux("select", P["accent"], None, 10)
    neuf_morceaux("menu", P["surface"], P["bordure"], 14, epaisseur=2, opacite=0.86)
    neuf_morceaux("terminal_box", P["fond"], P["bordure"], 10, epaisseur=2, opacite=0.96)

    for nom, taille in POLICES:
        sortie = os.path.join(THEME, f"{nom.lower()}-{taille}.pf2")
        subprocess.run(["grub-mkfont", "-s", str(taille), "-r", PLAGES, "-o", sortie, police_inter(nom)],
                       check=True, stderr=subprocess.DEVNULL)
        print("  ", os.path.relpath(sortie, DEPOT))


if __name__ == "__main__":
    main()

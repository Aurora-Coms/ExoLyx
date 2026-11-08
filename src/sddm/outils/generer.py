#!/usr/bin/env python3
"""Génère les images du thème SDDM « exolyx » depuis des SVG (cairosvg).

    python3 src/sddm/outils/generer.py

Écrit dans src/sddm/exolyx/images/ :
  fond.png              fond d'écran ExoLyx sombre (2560×1440)
  planete.png           planète du logo (avatar par défaut)
  orbites-arriere.png   moitié arrière des orbites tressées (derrière l'avatar)
  orbites-avant.png     moitié avant (devant l'avatar)
  lune.png              la lune et son halo
  logo.png              petit logo complet (coin supérieur gauche)
  icones/*.png          icônes d'actions (veille, redémarrer, éteindre…)

Géométrie des orbites : toile 900×520, centre (450, 260), planète r = 256.
Main.qml s'appuie sur ces valeurs (ORBITE_LARGEUR / ORBITE_HAUTEUR / ORBITE_R).
"""

import os
import sys

import cairosvg

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, "..", "..", ".."))
sys.path.insert(0, os.path.join(DEPOT, "src", "wallpapers", "outils"))
import dessin as d  # noqa: E402
import generer as fonds  # noqa: E402

IMAGES = os.path.join(DEPOT, "src", "sddm", "exolyx", "images")
P = d.SOMBRE

W, H, CX, CY, R = 900, 520, 450, 260, 256


def svg(w, h, defs, corps):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}"><defs>{defs}</defs>{corps}</svg>')


def png(contenu, nom, w=None, h=None):
    chemin = os.path.join(IMAGES, nom)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    cairosvg.svg2png(bytestring=contenu.encode(), write_to=chemin, output_width=w, output_height=h)
    print("  ", os.path.relpath(chemin, DEPOT))


ICONES = {
    # traits 24×24, style « ligne » arrondi
    "veille": '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/>',
    "redemarrer": '<path d="M20 12a8 8 0 1 1-2.6-5.9"/><path d="M20 4v5h-5"/>',
    "eteindre": '<path d="M12 3v8"/><path d="M6.3 6.8a8 8 0 1 0 11.4 0"/>',
    "session": ('<rect x="3" y="4" width="18" height="13" rx="2.5"/><path d="M8 21h8"/>'
                '<path d="M12 17v4"/>'),
    "clavier": ('<rect x="2.5" y="6" width="19" height="12" rx="2.5"/>'
                '<path d="M6.5 10h.01M10 10h.01M14 10h.01M17.5 10h.01M8 14h8"/>'),
    "majuscules": '<path d="M12 4l7 7h-4v5H9v-5H5z"/><path d="M9 20h6"/>',
    "fleche": '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    "coche": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
}


def icone(nom, trace, couleur, taille=96, epaisseur=2):
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
         f'fill="none" stroke="{couleur}" stroke-width="{epaisseur}" stroke-linecap="round" '
         f'stroke-linejoin="round">{trace}</svg>')
    png(s, f"icones/{nom}.png", taille, taille)


def main():
    # fond
    png(fonds.svg_fond(2560, 1440, "sombre"), "fond.png")

    defs = d.defs_logo(P, "l") + d.clips(CX, CY, W, H, "l") + d.defs_espace(CX, CY, R, P["fond"], "l")
    png(svg(W, H, defs, d.orbites_arriere(CX, CY, R, "l", opacite=0.8)), "orbites-arriere.png")
    png(svg(W, H, defs, d.orbites_avant(CX, CY, R, "url(#lespace)", "l")), "orbites-avant.png")

    # planète seule (avatar par défaut), sans halo, 512×512
    png(svg(512, 512, d.defs_logo(P, "l"), d.planete(256, 256, 256, P, "l", halo=False)), "planete.png")

    # lune : rayon 9/66 du logo ; image 96×96 avec halo
    png(svg(96, 96, d.defs_logo(P, "l"),
            '<circle cx="48" cy="48" r="48" fill="url(#lhalolune)"/>'
            f'<circle cx="48" cy="48" r="15" fill="{P["lune"]}"/>'
            '<circle cx="43" cy="43" r="6" fill="#FFFFFF" opacity="0.5"/>'), "lune.png")

    # petit logo complet
    with open(os.path.join(DEPOT, "src", "branding", "logo.svg")) as f:
        png(f.read(), "logo.png", 128, 128)

    for nom, trace in ICONES.items():
        icone(nom, trace, P["texte"])
    icone("fleche-sombre", ICONES["fleche"], P["fond"], epaisseur=2.4)
    icone("majuscules-attention", ICONES["majuscules"], "#E8C26A")


if __name__ == "__main__":
    main()

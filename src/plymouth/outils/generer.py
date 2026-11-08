#!/usr/bin/env python3
"""Génère les images du thème Plymouth « exolyx » depuis des SVG (cairosvg).

    python3 src/plymouth/outils/generer.py

Toutes les images sont rendues pour un écran de RÉFÉRENCE de 2160 px de haut
(soit 2× le 1080p) ; exolyx.script les met à l'échelle au démarrage
(facteur = hauteur d'écran / 2160).

Géométrie : planète r = 180 ; orbites sur une toile CARRÉE (côté 3,6 r) afin
qu'Image.Rotate() de Plymouth (qui garde les dimensions) ne rogne rien.
"""

import os
import sys

import cairosvg

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, "..", "..", ".."))
sys.path.insert(0, os.path.join(DEPOT, "src", "wallpapers", "outils"))
import dessin as d  # noqa: E402

THEME = os.path.join(DEPOT, "src", "plymouth", "exolyx")
P = d.SOMBRE
R = 180
COTE = int(R * 3.6)  # 648
C = COTE / 2


def svg(w, h, defs, corps):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}"><defs>{defs}</defs>{corps}</svg>')


def png(contenu, nom):
    chemin = os.path.join(THEME, nom)
    cairosvg.svg2png(bytestring=contenu.encode(), write_to=chemin)
    print("  ", os.path.relpath(chemin, DEPOT))


def main():
    os.makedirs(THEME, exist_ok=True)
    defs = d.defs_logo(P, "l") + d.clips(C, C, COTE, COTE, "l") + d.defs_espace(C, C, R, P["fond"], "l")

    png(svg(COTE, COTE, defs, d.orbites_arriere(C, C, R, "l", opacite=0.78)), "orbites-arriere.png")
    png(svg(COTE, COTE, defs, d.orbites_avant(C, C, R, "url(#lespace)", "l")), "orbites-avant.png")
    # planète seule (sans halo) et halo séparé (fixe, sous tout le reste)
    png(svg(2 * R, 2 * R, d.defs_logo(P, "l"), d.planete(R, R, R, P, "l", halo=False)), "planete.png")
    hr = int(R * 2.3)
    png(svg(2 * hr, 2 * hr, d.defs_logo(P, "l"), f'<circle cx="{hr}" cy="{hr}" r="{hr}" fill="url(#lhalo)"/>'), "halo.png")
    # lune (rayon 9/66 r ≈ 24) avec halo
    png(svg(120, 120, d.defs_logo(P, "l"),
            '<circle cx="60" cy="60" r="60" fill="url(#lhalolune)"/>'
            f'<circle cx="60" cy="60" r="{R * 9 / 66:.1f}" fill="{P["lune"]}"/>'
            '<circle cx="53" cy="53" r="8" fill="#FFFFFF" opacity="0.45"/>'), "lune.png")

    # barre de progression : piste + remplissage (étiré horizontalement par le script)
    png(svg(560, 10, "", f'<rect width="560" height="10" rx="5" fill="{P["surface_haute"]}"/>'), "barre-piste.png")
    png(svg(560, 10, f'<linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="{P["accent_froid"]}"/>'
                     f'<stop offset="1" stop-color="{P["accent_clair"]}"/></linearGradient>',
            '<rect width="560" height="10" rx="5" fill="url(#g)"/>'), "barre.png")

    # boîte de saisie du mot de passe (chiffrement)
    png(svg(900, 340, "", f'<rect x="2" y="2" width="896" height="336" rx="28" fill="{P["surface"]}" '
                          f'fill-opacity="0.96" stroke="{P["bordure"]}" stroke-width="3"/>'), "boite.png")
    png(svg(760, 104, "", f'<rect x="3" y="3" width="754" height="98" rx="49" fill="{P["surface_haute"]}" '
                          f'stroke="{P["accent"]}" stroke-width="5"/>'), "champ.png")
    png(svg(28, 28, "", f'<circle cx="14" cy="14" r="11" fill="{P["accent_clair"]}"/>'), "puce.png")
    png(svg(72, 72, "",
            f'<g fill="none" stroke="{P["accent"]}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="12" y="32" width="48" height="34" rx="8"/><path d="M22 32V22a14 14 0 0 1 28 0v10"/></g>'
            f'<circle cx="36" cy="49" r="5" fill="{P["accent"]}"/>'), "cadenas.png")


if __name__ == "__main__":
    main()

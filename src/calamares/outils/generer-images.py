#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Génère les images du branding Calamares à partir de src/branding/logo.svg.

Usage : python3 src/calamares/outils/generer-images.py
Dépendance : python-cairosvg. Les PNG produits sont versionnés dans
src/calamares/branding/exolyx/ (le PKGBUILD n'a donc pas besoin de cairosvg).
"""
from pathlib import Path
import re
import cairosvg

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent  # src/
LOGO = (RACINE / "branding" / "logo.svg").read_text(encoding="utf-8")
SORTIE = ICI.parent / "branding" / "exolyx"


def logo_png(nom: str, taille: int) -> None:
    cairosvg.svg2png(bytestring=LOGO.encode(), write_to=str(SORTIE / nom),
                     output_width=taille, output_height=taille)


def bienvenue_png() -> None:
    """Logo + nom « ExoLyx » + slogan, fond transparent (page d'accueil)."""
    interieur = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", LOGO.strip(), flags=re.S)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="300" viewBox="0 0 720 300">
  <defs>
    <linearGradient id="mot" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#BDD479"/><stop offset="1" stop-color="#8DD479"/>
    </linearGradient>
  </defs>
  <svg x="10" y="22" width="256" height="256" viewBox="0 0 256 256">{interieur}</svg>
  <text x="290" y="170" font-family="Inter" font-weight="700" font-size="104" fill="url(#mot)" letter-spacing="-2">ExoLyx</text>
  <text x="294" y="222" font-family="Inter" font-size="28" fill="#97A893">Le Linux qui vous ressemble</text>
</svg>"""
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(SORTIE / "bienvenue.png"))


if __name__ == "__main__":
    SORTIE.mkdir(parents=True, exist_ok=True)
    logo_png("logo.png", 256)
    logo_png("icone.png", 128)
    logo_png("logo-diapo.png", 512)
    bienvenue_png()
    print("images générées dans", SORTIE)

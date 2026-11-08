#!/usr/bin/env python3
"""Planches d'aperçu PNG des thèmes d'icônes (nécessite cairosvg et Pillow).

Usage : python3 planche.py DOSSIER_THEMES DOSSIER_SORTIE [taille ...]
Produit icones-planche-<taille>.png : pour chaque style, une rangée sombre et
une rangée claire de tous les pictogrammes. Les tailles < 32 sont rendues à
1:1 puis agrandies ×3 au plus proche voisin pour juger des pixels réels.
"""
import io
import os
import sys

import cairosvg
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generer  # noqa: E402

FONDS = {"sombre": (20, 28, 23), "clair": (244, 248, 241)}


def representants():
    vus, out = set(), []
    for ctx, table in generer.ICONES.items():
        for nom, pic in table.items():
            if pic not in vus:
                vus.add(pic)
                out.append((ctx, nom))
    return out


def png(chemin, taille):
    data = cairosvg.svg2png(url=chemin, output_width=taille, output_height=taille)
    return Image.open(io.BytesIO(data)).convert("RGBA")


def planche(themes, sortie, taille):
    reps = representants()
    loupe = 3 if taille < 32 else 1
    case = taille * loupe + (10 if loupe > 1 else 12)
    cols = 20
    lignes_par_bloc = (len(reps) + cols - 1) // cols
    marge_g = 120
    blocs = [(s, v) for s in generer.STYLES for v in ("sombre", "clair")]
    h_bloc = lignes_par_bloc * case + 10
    img = Image.new("RGB", (marge_g + cols * case + 10, len(blocs) * h_bloc), (60, 60, 60))
    dr = ImageDraw.Draw(img)
    for b, (style, var) in enumerate(blocs):
        y0 = b * h_bloc
        dr.rectangle([0, y0, img.width, y0 + h_bloc - 4], fill=FONDS[var])
        txt = (230, 239, 225) if var == "sombre" else (22, 32, 26)
        dr.text((8, y0 + 8), "%s\n%s\n%dpx" % (generer.STYLES[style], var, taille), fill=txt)
        theme = generer.nom_theme(style, var)
        for i, (ctx, nom) in enumerate(reps):
            chemin = os.path.join(themes, theme, str(taille), ctx, nom + ".svg")
            if not os.path.exists(chemin):
                chemin = os.path.join(themes, theme, "scalable", ctx, nom + ".svg")
            ic = png(chemin, taille)
            if loupe > 1:
                ic = ic.resize((taille * loupe, taille * loupe), Image.NEAREST)
            x = marge_g + (i % cols) * case + 5
            y = y0 + (i // cols) * case + 5
            img.paste(ic, (x, y), ic)
    chemin = os.path.join(sortie, "icones-planche-%d.png" % taille)
    img.save(chemin)
    return chemin


if __name__ == "__main__":
    themes, sortie = sys.argv[1], sys.argv[2]
    tailles = [int(t) for t in sys.argv[3:]] or [48, 32, 22, 16]
    os.makedirs(sortie, exist_ok=True)
    for t in tailles:
        print(planche(themes, sortie, t))

#!/usr/bin/env python3
"""Construit les paquets de fonds Plasma de la collection ExoLyx.

    python3 src/wallpapers/outils/paquets.py SORTIE [--largeur 3840 --hauteur 2160] [--seul ID]

Lit src/wallpapers/selection.txt et produit, pour chaque fond retenu :
  SORTIE/ExoLyx-<ID>/metadata.json
  SORTIE/ExoLyx-<ID>/contents/images/<L>x<H>.jpg   (PNG si Pillow est absent)
  SORTIE/ExoLyx-<ID>/contents/screenshot.jpg

Rendu : resvg (module Python ou commande `resvg`), sinon cairosvg.
"""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import collection as c1  # noqa: E402
import collection2 as c2  # noqa: E402

RACINE = os.path.dirname(ICI)


def selection():
    with open(os.path.join(RACINE, "selection.txt"), encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def fond(ident):
    """-> (nom affiché, fonction (W, H) -> SVG)"""
    if ident.startswith("A"):
        num = ident[1:]
        for n, nom, f in c1.FONDS:
            if n == num:
                return nom, f
    else:
        num, pal = ident.split("-", 1)
        nom, f = c2.STYLES[int(num) - 1]
        P = c2.PALETTES[pal]
        return f"{nom} · {P['nom']}", lambda W, H: f(W, H, P)
    raise KeyError(ident)


def png(svg, W, H):
    try:
        import resvg_py
        return bytes(resvg_py.svg_to_bytes(svg_string=svg, width=W, height=H))
    except ImportError:
        pass
    if shutil.which("resvg"):
        with tempfile.TemporaryDirectory() as t:
            e, s = os.path.join(t, "f.svg"), os.path.join(t, "f.png")
            with open(e, "w", encoding="utf-8") as f:
                f.write(svg)
            subprocess.run(["resvg", "-w", str(W), "-h", str(H), e, s], check=True)
            with open(s, "rb") as f:
                return f.read()
    import cairosvg
    return cairosvg.svg2png(bytestring=svg.encode(), output_width=W, output_height=H)


def ecrire(donnees, chemin_sans_ext, qualite=90):
    """JPEG si Pillow est là (bien plus léger), sinon PNG. Retourne le chemin."""
    try:
        from PIL import Image
    except ImportError:
        chemin = chemin_sans_ext + ".png"
        with open(chemin, "wb") as f:
            f.write(donnees)
        return chemin
    chemin = chemin_sans_ext + ".jpg"
    Image.open(io.BytesIO(donnees)).convert("RGB").save(chemin, "JPEG", quality=qualite, optimize=True, progressive=True)
    return chemin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie")
    ap.add_argument("--largeur", type=int, default=3840)
    ap.add_argument("--hauteur", type=int, default=2160)
    ap.add_argument("--seul")
    a = ap.parse_args()
    W, H = a.largeur, a.hauteur
    ids = selection()
    for n, ident in enumerate(ids, 1):
        if a.seul and ident != a.seul:
            continue
        nom, f = fond(ident)
        dossier = os.path.join(a.sortie, f"ExoLyx-{ident}")
        os.makedirs(os.path.join(dossier, "contents", "images"), exist_ok=True)
        svg = f(W, H)
        ecrire(png(svg, W, H), os.path.join(dossier, "contents", "images", f"{W}x{H}"))
        ecrire(png(svg, 400, 225), os.path.join(dossier, "contents", "screenshot"), 85)
        meta = {"KPlugin": {"Authors": [{"Name": "A.DERBEZ"}], "Id": f"ExoLyx-{ident}",
                            "License": "GPL-3.0-or-later", "Name": nom,
                            "Description": f"Fond d'écran ExoLyx « {nom} »"}}
        with open(os.path.join(dossier, "metadata.json"), "w", encoding="utf-8") as fo:
            json.dump(meta, fo, indent=2, ensure_ascii=False)
            fo.write("\n")
        print(f"[{n}/{len(ids)}] {ident} {nom}", flush=True)


if __name__ == "__main__":
    main()

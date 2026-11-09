# SPDX-License-Identifier: GPL-3.0-or-later
"""Teintes dynamiques ExoLyx : les couleurs du système suivent le fond d'écran.

Sans dépendance graphique : la lecture des pixels passe par PyQt6 (QImage) ou,
à défaut, Pillow. Les calculs de couleur se font dans l'espace OKLCH, où la
luminosité perçue reste constante quand on change de teinte : la palette
ExoLyx garde ses contrastes, seule la teinte (et la saturation) change.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
for d in (ICI, ICI.parent / "theme"):  # paquet installé / dépôt
    if (d / "generer_couleurs.py").exists():
        sys.path.insert(0, str(d))
        break
import generer_couleurs as gc  # noqa: E402

CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
DONNEES = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
FICHIER_REGLAGES = CONFIG / "exolyx" / "teintes.json"
APPLETSRC = CONFIG / "plasma-org.kde.plasma.desktop-appletsrc"

REGLAGES_DEFAUT = {
    "actif": True,
    "mode": "auto",          # auto (selon le fond) | sombre | clair
    "intensite": 50,         # 0 = surfaces neutres … 100 = surfaces très teintées
    "source": "dominante",   # dominante | vive
}
INTENSITES = {"Discrète": 20, "Équilibrée": 50, "Intense": 85}


# ---------------------------------------------------------------- OKLab / OKLCH
def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb_hex(rgb):
    return "#%02X%02X%02X" % tuple(round(max(0, min(1, c)) * 255) for c in rgb)


def rgb_oklch(rgb):
    r, g, b = (_lin(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    bb = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def oklch_rgb(L, C, H):
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return r, g, bl


def oklch_hex(L, C, H):
    """Couleur OKLCH -> #RRGGBB, en réduisant la saturation si elle sort du gamut sRGB."""
    for _ in range(40):
        rgb = oklch_rgb(L, C, H)
        if all(-0.0005 <= c <= 1.0005 for c in rgb):
            break
        C *= 0.92
    return rgb_hex(tuple(_gam(max(0.0, c)) for c in oklch_rgb(L, C, H)))


# ---------------------------------------------------------------- lecture du fond
def pixels_image(chemin, largeur=96):
    """Liste de (r, g, b) en 0..1 d'une version réduite de l'image."""
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QImage
        img = QImage(str(chemin))
        if img.isNull():
            raise OSError(f"image illisible : {chemin}")
        img = img.scaledToWidth(largeur, Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_RGB32)
        out = []
        for y in range(img.height()):
            for x in range(img.width()):
                c = img.pixelColor(x, y)
                out.append((c.redF(), c.greenF(), c.blueF()))
        return out
    except ImportError:
        from PIL import Image
        with Image.open(chemin) as im:
            im = im.convert("RGB")
            im.thumbnail((largeur, largeur))
            return [(r / 255, g / 255, b / 255) for r, g, b in im.getdata()]


def image_du_paquet(chemin):
    """Un dossier de paquet Plasma -> sa plus grande image."""
    p = Path(chemin)
    if p.is_dir():
        imgs = [f for f in (p / "contents" / "images").glob("*") if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".svg")]
        if not imgs:
            return None
        def surface(f):
            m = re.match(r"(\d+)x(\d+)", f.stem)
            return int(m[1]) * int(m[2]) if m else 0
        return max(imgs, key=surface)
    return p if p.exists() else None


def fond_actuel(appletsrc=None):
    """Chemin de l'image du fond d'écran du premier bureau (org.kde.image)."""
    try:
        texte = Path(appletsrc or APPLETSRC).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    groupe, trouves = "", []
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if ligne.startswith("["):
            groupe = ligne
        elif ligne.startswith("Image=") and "[Wallpaper][org.kde.image][General]" in groupe:
            m = re.match(r"\[Containments\]\[(\d+)\]", groupe)
            trouves.append((int(m[1]) if m else 0, ligne.split("=", 1)[1]))
    for _, val in sorted(trouves):
        val = re.sub(r"^file://", "", val).rstrip("/")
        img = image_du_paquet(val)
        if img:
            return img
    return None


# ---------------------------------------------------------------- analyse
def analyser(pixels):
    """Teinte dominante, saturation et luminosité moyenne d'un fond.

    Retourne {teinte, chroma, teinte_vive, chroma_vive, luminosite, neutre}.
    """
    bins = [[0.0, 0.0, 0.0, []] for _ in range(36)]  # poids, sin, cos, chromas (dominante)
    vifs = [[0.0, 0.0, 0.0, []] for _ in range(36)]
    somme_l = 0.0
    for px in pixels:
        L, C, H = rgb_oklch(px)
        somme_l += L
        if C < 0.02 or L < 0.12 or L > 0.98:
            continue
        i = int(H // 10) % 36
        for tab, w in ((bins, C), (vifs, C ** 3)):
            t = tab[i]
            t[0] += w
            t[1] += w * math.sin(math.radians(H))
            t[2] += w * math.cos(math.radians(H))
            t[3].append(C)
    n = max(1, len(pixels))

    def meilleure(tab):
        # fenêtre glissante de 3 cases pour ne pas couper une teinte en deux
        score = [tab[i - 1][0] + tab[i][0] + tab[(i + 1) % 36][0] for i in range(36)]
        i = max(range(36), key=score.__getitem__)
        if score[i] <= 0:
            return None, 0.0
        cases = [tab[i - 1], tab[i], tab[(i + 1) % 36]]
        s, c = sum(t[1] for t in cases), sum(t[2] for t in cases)
        chromas = sorted(x for t in cases for x in t[3])
        return math.degrees(math.atan2(s, c)) % 360, chromas[int(len(chromas) * 0.8)]

    h, c = meilleure(bins)
    hv, cv = meilleure(vifs)
    part_coloree = sum(t[0] for t in bins) / n
    neutre = h is None or part_coloree < 0.004
    return {"teinte": h if h is not None else 125.0, "chroma": c, "teinte_vive": hv if hv is not None else 125.0,
            "chroma_vive": cv, "luminosite": somme_l / n, "neutre": neutre}


# ---------------------------------------------------------------- palette
# Jetons de la palette ExoLyx d'origine (src/branding/palette.md), rangés par rôle.
SURFACES = ("fond", "surface", "haute", "vue", "alt", "bord", "texte", "doux", "inactif")
ACCENTS = ("accent", "accent2", "accentFroid", "lien")


def palette_dynamique(analyse, sombre=True, intensite=50, source="dominante"):
    base = gc.PALETTES["ExoLyx" if sombre else "ExoLyxClair"]
    h = analyse["teinte_vive"] if source == "vive" else analyse["teinte"]
    c_src = analyse["chroma_vive"] if source == "vive" else analyse["chroma"]
    k = intensite / 50  # 0 .. 2
    p = dict(base)
    p["nom"] = "ExoLyx Teinte" + ("" if sombre else " Claire")
    for cle in SURFACES:
        L, C, _ = rgb_oklch(hex_rgb(base[cle]))
        if analyse["neutre"]:
            C = 0.0
        else:  # chroma d'origine (le léger vert ExoLyx) modulée par l'intensité
            C = min(C * k * 1.4, 0.06 if cle in ("fond", "surface", "haute", "vue", "alt") else 0.08)
        p[cle] = oklch_hex(L, C, h)
    # accents : luminosité de la palette d'origine (contraste garanti), saturation du fond
    c_acc = 0.025 if analyse["neutre"] else max(0.09, min(0.19, c_src * 1.1))
    decalage = {"accent": 0, "accent2": 8, "accentFroid": -12, "lien": 0}
    for cle in ACCENTS:
        L, _, _ = rgb_oklch(hex_rgb(base[cle]))
        p[cle] = oklch_hex(L, c_acc, h + decalage[cle])
    p["surAccent"] = p["fond"] if sombre else "#FFFFFF"
    p["visite"] = oklch_hex(rgb_oklch(hex_rgb(base["visite"]))[0], 0.11, h + 70)
    return p


def est_sombre(analyse, mode):
    if mode == "sombre":
        return True
    if mode == "clair":
        return False
    return analyse["luminosite"] < 0.62


# ---------------------------------------------------------------- réglages et application
def lire_reglages():
    r = dict(REGLAGES_DEFAUT)
    try:
        r.update(json.loads(FICHIER_REGLAGES.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return r


def ecrire_reglages(r):
    FICHIER_REGLAGES.parent.mkdir(parents=True, exist_ok=True)
    tmp = FICHIER_REGLAGES.with_suffix(".tmp")
    tmp.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FICHIER_REGLAGES)


def schema_actuel():
    try:
        for ligne in (CONFIG / "kdeglobals").read_text(encoding="utf-8", errors="replace").splitlines():
            if ligne.startswith("ColorScheme="):
                return ligne.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def appliquer_palette(p, sombre, executer=True):
    """Écrit le schéma et l'active. Deux noms alternés (A/B) : Plasma ignore
    une réapplication du schéma déjà actif. « Clair » dans le nom = thème clair
    (convention lue par les applis ExoLyx)."""
    actuel = schema_actuel()
    lettre = "B" if actuel.startswith("ExoLyxTeinteA") else "A"
    cle = f"ExoLyxTeinte{lettre}" + ("" if sombre else "Clair")
    p = dict(p, nom=p["nom"])
    dossier = DONNEES / "color-schemes"
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{cle}.colors").write_text(gc.schema(cle, p), encoding="utf-8")
    if executer and shutil.which("plasma-apply-colorscheme"):
        subprocess.run(["plasma-apply-colorscheme", cle], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # supprime l'autre variante pour ne pas encombrer la liste des schémas
    for f in dossier.glob("ExoLyxTeinte*.colors"):
        if f.stem != cle:
            f.unlink(missing_ok=True)
    return cle


def retablir(sombre=True):
    """Revient au vert ExoLyx d'origine."""
    if shutil.which("plasma-apply-colorscheme"):
        subprocess.run(["plasma-apply-colorscheme", "ExoLyx" if sombre else "ExoLyxClair"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def calculer(image=None, reglages=None):
    """-> (image, analyse, sombre, palette) ou None si aucun fond n'est trouvé."""
    r = reglages or lire_reglages()
    image = image or fond_actuel()
    if not image:
        return None
    a = analyser(pixels_image(image))
    sombre = est_sombre(a, r["mode"])
    return image, a, sombre, palette_dynamique(a, sombre, r["intensite"], r["source"])


def mettre_a_jour(image=None, executer=True):
    """Point d'entrée du service : applique si la fonction est active."""
    r = lire_reglages()
    if not r["actif"]:
        return None
    res = calculer(image, r)
    if not res:
        return None
    _, _, sombre, p = res
    return appliquer_palette(p, sombre, executer)

#!/usr/bin/env python3
"""Aperçu APPROXIMATIF du thème GRUB « exolyx » (sans GRUB).

Analyse theme.txt (propriétés globales et composants « + type { … } »),
résout les positions (« 50%-64 », « 100%-52 »…), puis dessine avec Pillow :
fond (rogné), image, labels, boot_menu (styles pixmap 9 morceaux),
barre de progression. Le rendu des polices diffère légèrement de GRUB.

    python3 src/grub/tests/apercu.py SORTIE.png [LxH]

Échoue (code 1) si theme.txt contient une erreur de syntaxe détectable, une
image ou une police référencée absente.
"""

import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(os.path.dirname(ICI), "exolyx")

ENTREES = ["ExoLyx", "ExoLyx (options avancées)", "ExoLyx (initramfs de secours)",
           "Windows Boot Manager (sur /dev/nvme0n1p1)", "Paramètres du micrologiciel UEFI"]
SELECTION = 0
DELAI = 5


def analyser(chemin):
    glob, comps, erreurs = {}, [], []
    courant = None
    for no, ligne in enumerate(open(chemin, encoding="utf-8"), 1):
        l = ligne.strip()
        if not l or l.startswith("#"):
            continue
        if courant is None:
            m = re.match(r'^\+\s*(\w+)\s*\{$', l)
            if m:
                courant = {"_type": m.group(1)}
                continue
            m = re.match(r'^([\w-]+)\s*:\s*"(.*)"$', l)
            if m:
                glob[m.group(1)] = m.group(2)
                continue
            erreurs.append(f"ligne {no} : {l}")
        else:
            if l == "}":
                comps.append(courant)
                courant = None
                continue
            m = re.match(r'^([\w-]+)\s*=\s*(".*"|[^"\s]+)$', l)
            if m:
                v = m.group(2)
                courant[m.group(1)] = v[1:-1] if v.startswith('"') else v
                continue
            erreurs.append(f"ligne {no} : {l}")
    if courant is not None:
        erreurs.append("bloc non fermé")
    return glob, comps, erreurs


def valeur(expr, total):
    expr = str(expr).replace(" ", "")
    m = re.match(r'^(-?\d+)%([+-]\d+)?$', expr)
    if m:
        return int(total * int(m.group(1)) / 100) + int(m.group(2) or 0)
    return int(expr)


def police(nom):
    m = re.match(r'^(.*) (Regular|Bold) (\d+)$', nom)
    famille, style, taille = m.group(1), m.group(2), int(m.group(3))
    pf2 = os.path.join(THEME, f"{famille.lower()}-{style.lower()}-{taille}.pf2")
    if not os.path.exists(pf2):
        raise SystemExit(f"police GRUB absente : {pf2}")
    f = subprocess.run(["fc-match", "-f", "%{file}", f"{famille}:style={style}"],
                       capture_output=True, text=True).stdout.strip()
    return ImageFont.truetype(f, taille)


def pixmap(img, motif, x, y, w, h):
    morceaux = {}
    for n in ("nw", "n", "ne", "w", "c", "e", "sw", "s", "se"):
        c = os.path.join(THEME, motif.replace("*", n))
        if not os.path.exists(c):
            raise SystemExit(f"image absente : {c}")
        morceaux[n] = Image.open(c).convert("RGBA")
    cw, ch = morceaux["nw"].size
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))

    def coller(n, px, py, pw, ph):
        if pw > 0 and ph > 0:
            calque.paste(morceaux[n].resize((pw, ph)), (px, py))
    coller("nw", x, y, cw, ch); coller("ne", x + w - cw, y, cw, ch)
    coller("sw", x, y + h - ch, cw, ch); coller("se", x + w - cw, y + h - ch, cw, ch)
    coller("n", x + cw, y, w - 2 * cw, ch); coller("s", x + cw, y + h - ch, w - 2 * cw, ch)
    coller("w", x, y + ch, cw, h - 2 * ch); coller("e", x + w - cw, y + ch, cw, h - 2 * ch)
    coller("c", x + cw, y + ch, w - 2 * cw, h - 2 * ch)
    img.alpha_composite(calque)


def rendre(sortie, W, H):
    glob, comps, erreurs = analyser(os.path.join(THEME, "theme.txt"))
    if erreurs:
        raise SystemExit("theme.txt : " + "; ".join(erreurs))

    img = Image.new("RGBA", (W, H), glob.get("desktop-color", "#000000"))
    fond = Image.open(os.path.join(THEME, glob["desktop-image"])).convert("RGBA")
    k = max(W / fond.width, H / fond.height)  # « crop »
    fond = fond.resize((round(fond.width * k), round(fond.height * k)), Image.LANCZOS)
    img.alpha_composite(fond, (-(fond.width - W) // 2, -(fond.height - H) // 2))
    dessin = ImageDraw.Draw(img)

    for c in comps:
        x, y = valeur(c.get("left", 0), W), valeur(c.get("top", 0), H)
        w, h = valeur(c.get("width", 0), W), valeur(c.get("height", 0), H)
        t = c["_type"]
        if t == "image":
            im = Image.open(os.path.join(THEME, c["file"])).convert("RGBA").resize((w, h), Image.LANCZOS)
            img.alpha_composite(im, (x, y))
        elif t == "label":
            texte = c.get("text", "")
            if c.get("id") == "__timeout__":
                texte = texte.replace("%d", str(DELAI))
            f = police(c["font"])
            lt = dessin.textlength(texte, font=f)
            tx = x + (w - lt) / 2 if c.get("align") == "center" else x
            dessin.text((tx, y), texte, font=f, fill=c.get("color", "#FFFFFF"))
        elif t == "progress_bar":
            dessin.rectangle((x, y, x + w - 1, y + h - 1), fill=c.get("bg_color"))
            dessin.rectangle((x, y, x + int(w * 0.6) - 1, y + h - 1), fill=c.get("fg_color"))
        elif t == "boot_menu":
            ih, ip, isp = int(c["item_height"]), int(c["item_padding"]), int(c["item_spacing"])
            if "menu_pixmap_style" in c:
                pixmap(img, c["menu_pixmap_style"], x, y, w, h)
            # GRUB : marge intérieure = taille des coins du cadre
            bord = Image.open(os.path.join(THEME, c["menu_pixmap_style"].replace("*", "nw"))).size[0]
            yy = y + bord
            for i, e in enumerate(ENTREES):
                if yy + ih > y + h - bord:
                    break
                sel = i == SELECTION
                if sel:
                    pixmap(img, c["selected_item_pixmap_style"], x + bord, yy, w - 2 * bord, ih)
                f = police(c["selected_item_font" if sel else "item_font"])
                coul = c["selected_item_color" if sel else "item_color"]
                d2 = ImageDraw.Draw(img)
                asc, desc = f.getmetrics()
                d2.text((x + bord + ip, yy + (ih - asc - desc) / 2), e, font=f, fill=coul)
                yy += ih + isp
            dessin = ImageDraw.Draw(img)
    img.convert("RGB").save(sortie)
    print("  aperçu :", sortie)


if __name__ == "__main__":
    sortie = sys.argv[1]
    W, H = (int(v) for v in (sys.argv[2] if len(sys.argv) > 2 else "1920x1080").split("x"))
    rendre(sortie, W, H)

#!/usr/bin/env python3
"""Générateur du thème de curseurs « ExoLyx-Curseur » (format Xcursor).

Chaque curseur est dessiné en SVG (grille 32×32), rendu en PNG par cairosvg
aux tailles 24, 32, 48 et 64 px, puis encodé au format Xcursor par
l'encodeur Python ci-dessous (xcursorgen n'est pas nécessaire).

Format Xcursor (libXcursor, tous les entiers CARD32 petit-boutistes) :
  en-tête   : "Xcur", taille d'en-tête (16), version (0x00010000), ntoc
  table     : ntoc × (type, sous-type, position)
  image     : en-tête de chunk (36, 0xfffd0002, taille nominale, version 1),
              largeur, hauteur, xhot, yhot, délai (ms),
              puis largeur×hauteur pixels ARGB prémultipliés.

Usage : python3 generer.py [dossier_theme]   (défaut : ./ExoLyx-Curseur)
Dépendances (génération seulement) : cairosvg, Pillow.
"""

import io
import math
import os
import shutil
import struct
import sys

TAILLES = (24, 32, 48, 64)
XCUR_MAGIC = b"Xcur"
XCUR_VERSION = 0x00010000
TYPE_IMAGE = 0xFFFD0002
IMAGE_VERSION = 1

# Palette ExoLyx (src/branding/palette.md)
SOMBRE = "#0D1310"
ACCENT = "#A8D479"
ACCENT_CLAIR = "#BDD479"
ACCENT_FROID = "#8DD479"
PLANETE = ["#E4F5B8", "#BDD479", "#6FA845", "#1F3A1F"]
ERREUR = "#E5766B"
INFO = "#79C2D4"


def fmt(v):
    s = ("%.2f" % v).rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


# --------------------------------------------------------------------------
# Encodeur Xcursor
# --------------------------------------------------------------------------
def premultiplier(rgba_bytes):
    """RGBA (non prémultiplié, octets) -> liste d'entiers ARGB prémultipliés."""
    out = []
    for i in range(0, len(rgba_bytes), 4):
        r, g, b, a = rgba_bytes[i], rgba_bytes[i + 1], rgba_bytes[i + 2], rgba_bytes[i + 3]
        r = (r * a + 127) // 255
        g = (g * a + 127) // 255
        b = (b * a + 127) // 255
        out.append((a << 24) | (r << 16) | (g << 8) | b)
    return out


def encoder_xcursor(images):
    """images : liste de dict(taille, largeur, hauteur, xhot, yhot, delai, pixels[ARGB])
    dans l'ordre voulu (par taille puis par trame). Renvoie les octets du fichier."""
    ntoc = len(images)
    entete = struct.pack("<4sIII", XCUR_MAGIC, 16, XCUR_VERSION, ntoc)
    position = 16 + 12 * ntoc
    table, chunks = [], []
    for im in images:
        w, h = im["largeur"], im["hauteur"]
        if not (0 < w <= 0x7FFF and 0 < h <= 0x7FFF):
            raise ValueError("dimensions hors limites")
        if not (0 <= im["xhot"] < w and 0 <= im["yhot"] < h):
            raise ValueError("point chaud hors de l'image")
        if len(im["pixels"]) != w * h:
            raise ValueError("nombre de pixels incorrect")
        chunk = struct.pack("<IIIIIIIII", 36, TYPE_IMAGE, im["taille"], IMAGE_VERSION,
                            w, h, im["xhot"], im["yhot"], im["delai"])
        chunk += struct.pack("<%dI" % (w * h), *im["pixels"])
        table.append(struct.pack("<III", TYPE_IMAGE, im["taille"], position))
        chunks.append(chunk)
        position += len(chunk)
    return entete + b"".join(table) + b"".join(chunks)


def lire_xcursor(donnees):
    """Décodeur minimal (pour les tests) : renvoie la liste des images."""
    magic, hsize, version, ntoc = struct.unpack_from("<4sIII", donnees, 0)
    if magic != XCUR_MAGIC:
        raise ValueError("signature Xcur absente")
    images = []
    for i in range(ntoc):
        typ, sous, pos = struct.unpack_from("<III", donnees, hsize + 12 * i)
        if typ != TYPE_IMAGE:
            continue
        (ch, ctype, csub, cver, w, h, xh, yh, delai) = struct.unpack_from("<IIIIIIIII", donnees, pos)
        if ch != 36 or ctype != TYPE_IMAGE or csub != sous:
            raise ValueError("chunk image incohérent")
        pixels = struct.unpack_from("<%dI" % (w * h), donnees, pos + 36)
        images.append({"taille": sous, "largeur": w, "hauteur": h, "xhot": xh, "yhot": yh,
                       "delai": delai, "pixels": pixels, "version": version})
    return images


# --------------------------------------------------------------------------
# Dessins (grille 32×32)
# --------------------------------------------------------------------------
DEFS = (
    '<defs>'
    '<linearGradient id="vert" x1="0" y1="0" x2="0.35" y2="1">'
    '<stop offset="0" stop-color="#DDF1AE"/><stop offset="0.45" stop-color="%s"/>'
    '<stop offset="1" stop-color="#7DB547"/></linearGradient>'
    '<radialGradient id="planete" cx="0.36" cy="0.32" r="0.78" fx="0.36" fy="0.32">'
    '<stop offset="0" stop-color="%s"/><stop offset="0.28" stop-color="%s"/>'
    '<stop offset="0.62" stop-color="%s"/><stop offset="1" stop-color="%s"/></radialGradient>'
    '</defs>' % (ACCENT, PLANETE[0], PLANETE[1], PLANETE[2], PLANETE[3]))


def svg(corps):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
            + DEFS + corps + '</svg>')


def ombre(forme):
    """Ombre douce sans filtre : copies décalées, élargies et translucides."""
    s = []
    for ep, op in ((4.2, 0.07), (2.8, 0.09), (1.4, 0.12)):
        s.append('<g transform="translate(0.7 1.3)" opacity="%s">%s</g>' % (
            fmt(op), forme('#000000', '#000000', ep)))
    return "".join(s)


def plein(d, transform=None, remplissage="url(#vert)"):
    """Forme pleine verte, contour sombre, avec ombre."""
    t = ' transform="%s"' % transform if transform else ""

    def forme(fill, stroke, ep):
        return '<path d="%s"%s fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            d, t, fill, stroke, fmt(ep))
    return ombre(forme) + forme(remplissage, SOMBRE, 1.5)


def traits(d, ep=2.0, transform=None, couleur=ACCENT_CLAIR):
    """Traits verts bordés de sombre."""
    t = ' transform="%s"' % transform if transform else ""

    def forme(_fill, stroke, extra):
        return ('<path d="%s"%s fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" '
                'stroke-linejoin="round"/>' % (d, t, stroke, fmt(ep + 2.6 + extra)))
    clair = ('<path d="%s"%s fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" '
             'stroke-linejoin="round"/>' % (d, t, couleur, fmt(ep)))
    return ombre(forme) + forme(None, SOMBRE, 0) + clair


FLECHE = "M5 3.5 L5 24.2 L10.1 19.5 L13.5 27.3 L17.2 25.7 L13.8 18.1 L20.6 18.1 Z"


def fleche(transform=None):
    return plein(FLECHE, transform) + (
        '<path d="M6.6 7.4 L6.6 13.5" stroke="#FFFFFF" stroke-opacity="0.55" stroke-width="1.1" stroke-linecap="round"%s/>'
        % (' transform="%s"' % transform if transform else ""))


def pastille(contenu, fond=ACCENT_CLAIR, cx=23.5, cy=23.5, r=6.6):
    def forme(fill, stroke, ep):
        return '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
            fmt(cx), fmt(cy), fmt(r), fill, stroke, fmt(ep))
    return ombre(forme) + forme(fond, SOMBRE, 1.5) + contenu


def glyphe(d, ep=1.8, couleur=SOMBRE):
    return '<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>' % (
        d, couleur, fmt(ep))


def main(doigts, pouce, bas=28.5, x0=9.6, larg=3.6):
    """Main stylisée : doigts = hauteurs du haut de chaque doigt (4 valeurs)."""
    r = larg / 2
    x = x0
    d = "M%s %s" % (fmt(x), fmt(doigts[0] + r))
    for i, top in enumerate(doigts):
        d += " A%s %s 0 0 1 %s %s" % (fmt(r), fmt(r), fmt(x + larg), fmt(top + r))
        x += larg
        if i < 3:
            nxt = doigts[i + 1]
            d += " V%s" % fmt(max(top, nxt) + r + 1.2 if nxt > top else nxt + r + 0.0)
            if nxt < top:
                d += " V%s" % fmt(nxt + r)
    xd = x
    d += " V%s C%s %s %s %s %s %s H%s C%s %s %s %s %s %s" % (
        fmt(bas - 7.5), fmt(xd), fmt(bas - 2.5), fmt(xd - 3), fmt(bas), fmt(xd - 6.5), fmt(bas),
        fmt(x0 + 4.5), fmt(x0 + 2), fmt(bas), fmt(x0 + 0.6), fmt(bas - 1.3), fmt(x0 - 0.6), fmt(bas - 3))
    px, py = pouce
    d += " L%s %s C%s %s %s %s %s %s C%s %s %s %s %s %s Z" % (
        fmt(px), fmt(py), fmt(px - 0.8), fmt(py - 1.1), fmt(px - 0.3), fmt(py - 2.6), fmt(px + 0.9), fmt(py - 3.1),
        fmt(px + 2.0), fmt(py - 3.6), fmt(px + 3.3), fmt(py - 3.0), fmt(x0), fmt(py - 0.8))
    return d


def separations(doigts, x0=9.6, larg=3.6, long=4.2):
    s = []
    for i in range(1, 4):
        x = x0 + i * larg
        y = max(doigts[i - 1], doigts[i]) + larg / 2 + 0.8
        s.append("M%s %s V%s" % (fmt(x), fmt(y), fmt(y + long)))
    return glyphe(" ".join(s), 1.0)


def main_pointee():
    doigts = [2.5, 11.0, 12.0, 13.4]
    d = main(doigts, (6.4, 17.6), x0=11.2, larg=3.5)
    return plein(d) + separations(doigts, x0=11.2, larg=3.5, long=3.6)


def main_ouverte():
    doigts = [6.0, 4.0, 4.6, 6.8]
    return plein(main(doigts, (5.4, 15.4), x0=10.2, larg=3.6)) + separations(doigts, x0=10.2, larg=3.6, long=6)


def main_fermee():
    doigts = [11.5, 10.6, 11.0, 12.0]
    return plein(main(doigts, (8.4, 17.2), x0=10.2, larg=3.6)) + glyphe(
        "M10.6 16.6 H24" , 1.0) + separations(doigts, x0=10.2, larg=3.6, long=3)


def ibeam(rot=0):
    t = "rotate(%s 16 16)" % rot if rot else None
    return traits("M11.5 5 C13.8 5 16 5.6 16 8 V24 C16 26.4 13.8 27 11.5 27 M20.5 5 C18.2 5 16 5.6 16 8 "
                  "M16 24 C16 26.4 18.2 27 20.5 27 M13 16 H19", 1.9, t)


DOUBLE = "M16 3 L22.2 9.6 H18.1 V22.4 H22.2 L16 29 L9.8 22.4 H13.9 V9.6 H9.8 Z"


def double_fleche(rot):
    return plein(DOUBLE, "rotate(%s 16 16)" % rot if rot else None)


def fleche_barre(rot):
    t = "rotate(%s 16 16)" % rot if rot else None
    d = ("M2.5 16 L8.6 10.2 V13.9 H12.4 V18.1 H8.6 V21.8 Z M29.5 16 L23.4 10.2 V13.9 H19.6 V18.1 H23.4 V21.8 Z")
    barres = "M13.6 5.5 H15.2 V26.5 H13.6 Z M16.8 5.5 H18.4 V26.5 H16.8 Z"
    return plein(d, t) + plein(barres, t)


CROIX_DEPL = ("M16 2.5 L21.2 7.8 H17.7 V14.3 H24.2 V10.8 L29.5 16 L24.2 21.2 V17.7 H17.7 V24.2 H21.2 "
              "L16 29.5 L10.8 24.2 H14.3 V17.7 H7.8 V21.2 L2.5 16 L7.8 10.8 V14.3 H14.3 V7.8 H10.8 Z")


def viseur():
    return traits("M16 3.5 V12.2 M16 19.8 V28.5 M3.5 16 H12.2 M19.8 16 H28.5", 1.9) + (
        '<circle cx="16" cy="16" r="1.6" fill="%s" stroke="%s" stroke-width="1"/>' % (ACCENT_CLAIR, SOMBRE))


def interdit(cx=16, cy=16, r=10, ep=3.0):
    def forme(fill, stroke, e):
        return ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>'
                '<path d="M%s %s L%s %s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>') % (
            fmt(cx), fmt(cy), fmt(r), stroke, fmt(ep + 2.6 + (e if fill == "#000000" else 0)),
            fmt(cx - r * 0.7), fmt(cy - r * 0.7), fmt(cx + r * 0.7), fmt(cy + r * 0.7), stroke,
            fmt(ep + 2.6 + (e if fill == "#000000" else 0)))
    rouge = ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>'
             '<path d="M%s %s L%s %s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>') % (
        fmt(cx), fmt(cy), fmt(r), ERREUR, fmt(ep), fmt(cx - r * 0.7), fmt(cy - r * 0.7),
        fmt(cx + r * 0.7), fmt(cy + r * 0.7), ERREUR, fmt(ep))
    return ombre(forme) + forme(None, SOMBRE, 0) + rouge


def loupe(signe):
    corps = traits("M20.2 20.2 L27.5 27.5", 3.2) + (
        '<circle cx="13.5" cy="13.5" r="8.6" fill="#FFFFFF" fill-opacity="0.25" stroke="%s" stroke-width="4.4"/>'
        '<circle cx="13.5" cy="13.5" r="8.6" fill="none" stroke="%s" stroke-width="2.2"/>' % (SOMBRE, ACCENT_CLAIR))
    g = "M9.6 13.5 H17.4" + (" M13.5 9.6 V17.4" if signe == "+" else "")
    return corps + glyphe(g, 2.0)


def orbite(t, cx=16, cy=16, ech=1.0):
    """Planète et lune en orbite ; t dans [0, 1[ = position de la lune."""
    rx, ry, rot = 12.5 * ech, 4.6 * ech, -24
    r_pl = 7.0 * ech
    a = 2 * math.pi * t
    tr = math.radians(rot)
    lx = cx + rx * math.cos(a) * math.cos(tr) - ry * math.sin(a) * math.sin(tr)
    ly = cy + rx * math.cos(a) * math.sin(tr) + ry * math.sin(a) * math.cos(tr)
    devant = math.sin(a) > 0
    ell = '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" transform="rotate(%d %s %s)" fill="none" stroke="%s" stroke-width="%s" stroke-opacity="%s"/>'
    lune = ('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
        fmt(lx), fmt(ly), fmt(2.7 * ech), PLANETE[0], SOMBRE, fmt(1.2 * ech)))
    # traînée de la lune
    trainee = ""
    for k in range(1, 4):
        ak = a - k * 0.38
        tx = cx + rx * math.cos(ak) * math.cos(tr) - ry * math.sin(ak) * math.sin(tr)
        ty = cy + rx * math.cos(ak) * math.sin(tr) + ry * math.sin(ak) * math.cos(tr)
        if (math.sin(ak) > 0) == devant or devant:
            trainee += '<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="%s"/>' % (
                fmt(tx), fmt(ty), fmt((2.3 - 0.45 * k) * ech), PLANETE[0], fmt(0.55 - 0.13 * k))
    s = ell % (fmt(cx), fmt(cy), fmt(rx), fmt(ry), rot, fmt(cx), fmt(cy), SOMBRE, fmt(3.4 * ech), "0.85")
    s += ell % (fmt(cx), fmt(cy), fmt(rx), fmt(ry), rot, fmt(cx), fmt(cy), ACCENT_CLAIR, fmt(1.4 * ech), "0.9")
    planete = ('<circle cx="%s" cy="%s" r="%s" fill="#000000" fill-opacity="0.25"/>'
               '<circle cx="%s" cy="%s" r="%s" fill="url(#planete)" stroke="%s" stroke-width="%s"/>') % (
        fmt(cx + 0.6 * ech), fmt(cy + 1.1 * ech), fmt(r_pl + 1.2 * ech), fmt(cx), fmt(cy), fmt(r_pl),
        SOMBRE, fmt(1.4 * ech))
    if devant:
        return s + planete + trainee + lune
    return s + trainee + lune + planete


TRAMES = 16
DELAI = 55


def anim(fonction):
    return [fonction(i / TRAMES) for i in range(TRAMES)]


# nom principal -> (points chauds en unités 32, trames SVG, délai)
def curseurs():
    c = {}

    def statique(nom, hx, hy, corps):
        c[nom] = ((hx, hy), [svg(corps)], 0)

    statique("default", 5, 3.5, fleche())
    statique("right_ptr", 27, 3.5, fleche("matrix(-1 0 0 1 32 0)"))
    statique("pointer", 13, 2.6, main_pointee())
    statique("text", 16, 16, ibeam())
    statique("vertical-text", 16, 16, ibeam(90))
    statique("crosshair", 16, 16, viseur())
    statique("cell", 16, 16, plein("M13.2 4.5 H18.8 V13.2 H27.5 V18.8 H18.8 V27.5 H13.2 V18.8 H4.5 V13.2 H13.2 Z"))
    statique("not-allowed", 16, 16, interdit())
    statique("no-drop", 5, 3.5, fleche() + interdit(23.2, 23.2, 5.2, 2.0))
    statique("grab", 16, 15, main_ouverte())
    statique("grabbing", 16, 16, main_fermee())
    statique("move", 16, 16, plein(CROIX_DEPL))
    statique("all-scroll", 16, 16, plein(CROIX_DEPL) + '<circle cx="16" cy="16" r="2" fill="%s"/>' % SOMBRE)
    statique("help", 5, 3.5, fleche() + pastille(glyphe(
        "M21.3 21.6 a2.3 2.3 0 1 1 3.3 2 c-.7 .4-1.1 .8-1.1 1.6 V25.6", 1.7)
        + '<circle cx="23.5" cy="27.6" r="0.95" fill="%s"/>' % SOMBRE))
    statique("copy", 5, 3.5, fleche() + pastille(glyphe("M20.3 23.5 H26.7 M23.5 20.3 V26.7", 1.9)))
    statique("alias", 5, 3.5, fleche() + pastille(glyphe(
        "M20.6 26.4 V24.6 a2.6 2.6 0 0 1 2.6-2.6 H26.2 M24.2 20 L26.4 22 L24.2 24", 1.6)))
    statique("context-menu", 5, 3.5, fleche() + pastille(glyphe(
        "M20.4 21.2 H26.6 M20.4 23.5 H26.6 M20.4 25.8 H26.6", 1.4), ACCENT_CLAIR))
    statique("zoom-in", 13.5, 13.5, loupe("+"))
    statique("zoom-out", 13.5, 13.5, loupe("-"))
    statique("ns-resize", 16, 16, double_fleche(0))
    statique("ew-resize", 16, 16, double_fleche(90))
    statique("nesw-resize", 16, 16, double_fleche(45))
    statique("nwse-resize", 16, 16, double_fleche(-45))
    statique("col-resize", 16, 16, fleche_barre(0))
    statique("row-resize", 16, 16, fleche_barre(90))
    c["wait"] = ((16, 16), [svg(x) for x in anim(lambda t: orbite(t))], DELAI)
    c["progress"] = ((5, 3.5), [svg(fleche() + x) for x in anim(lambda t: orbite(t, 23.2, 23.6, 0.58))], DELAI)
    return c


ALIAS = {
    "default": ["left_ptr", "arrow", "top_left_arrow", "left-arrow"],
    "pointer": ["hand1", "hand2", "pointing_hand", "9d800788f1b08800ae810202380a0822",
                "e29285e634086352946a0e7090d73106"],
    "text": ["xterm", "ibeam"],
    "crosshair": ["cross", "tcross", "cross_reverse", "diamond_cross"],
    "cell": ["plus"],
    "not-allowed": ["forbidden", "crossed_circle", "circle", "03b6e0fcb3499374a867c041f52298f0"],
    "no-drop": ["dnd-none", "dnd-no-drop"],
    "grab": ["openhand", "fleur-open", "5aca4d189052212118709018842178c0", "9141b49c8149039304290b508d208c40"],
    "grabbing": ["closedhand", "dnd-move", "208530c400c041818281048008011002",
                 "4498f0e0c1937ffe01fd06f973665830", "9081237383d90e509aa00f00170e968f"],
    "move": ["fleur", "size_all", "pointer-move"],
    "all-scroll": [],
    "help": ["question_arrow", "whats_this", "left_ptr_help", "dnd-ask", "d9ce0ab605698f320427677b458ad60b",
             "5c6cd98b3f3ebcb1f9c7f1c204630408"],
    "copy": ["dnd-copy", "1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872",
             "b66166c04f8c3109214a4fbd64a50fc8"],
    "alias": ["link", "dnd-link", "640fb0e74195791501fd1ed57b41487f", "3085a0e285430894940527032f8b26df",
              "a2a266d0498c3104214a47bd64ab0fc8"],
    "context-menu": [],
    "zoom-in": [], "zoom-out": [],
    "ns-resize": ["n-resize", "s-resize", "size_ver", "sb_v_double_arrow", "v_double_arrow", "top_side",
                  "bottom_side", "row-resize-arrows", "00008160000006810000408080010102"],
    "ew-resize": ["e-resize", "w-resize", "size_hor", "sb_h_double_arrow", "h_double_arrow", "left_side",
                  "right_side", "028006030e0e7ebffc7f7070c0600140"],
    "nesw-resize": ["ne-resize", "sw-resize", "size_bdiag", "fd_double_arrow", "top_right_corner",
                    "bottom_left_corner", "fcf1c3c7cd4491d801f1e1c78f100000", "50585d75b494802d0151028115016902"],
    "nwse-resize": ["nw-resize", "se-resize", "size_fdiag", "bd_double_arrow", "top_left_corner",
                    "bottom_right_corner", "c7088f0f3e6c8088236ef8e1e3e70000", "38c5dff7c7b8962045400281044508d2"],
    "col-resize": ["split_h", "sb_h_double_arrow_bar", "14fef782d02440884392942c11205230"],
    "row-resize": ["split_v", "2870a09082c103050810ffdffffe0204"],
    "vertical-text": [],
    "wait": ["watch", "clock"],
    "progress": ["left_ptr_watch", "half-busy", "3ecb610c1bf2410f44200f48c40d3599",
                 "08e8e1c95fe2fc01f976f1e063a24ccd", "00000000000000020006000e7e9ffc3f"],
    "right_ptr": ["draft_large", "draft_small"],
}


def rendre(svg_txt, taille):
    import cairosvg
    from PIL import Image
    png = cairosvg.svg2png(bytestring=svg_txt.encode(), output_width=taille, output_height=taille)
    return Image.open(io.BytesIO(png)).convert("RGBA").tobytes()


def construire(nom, hot, trames, delai, cache_png=None):
    images = []
    for taille in TAILLES:
        k = taille / 32.0
        xh = min(taille - 1, int(round(hot[0] * k)))
        yh = min(taille - 1, int(round(hot[1] * k)))
        for i, t in enumerate(trames):
            rgba = rendre(t, taille)
            if cache_png is not None and i == 0:
                cache_png[(nom, taille)] = rgba
            images.append({"taille": taille, "largeur": taille, "hauteur": taille, "xhot": xh, "yhot": yh,
                           "delai": delai if len(trames) > 1 else 0, "pixels": premultiplier(rgba)})
    return encoder_xcursor(images)


INDEX = """[Icon Theme]
Name=ExoLyx-Curseur
Comment=Curseurs ExoLyx : pointeur vert pomme à contour sombre, attente en orbite
Inherits=breeze_cursors
"""


def generer(racine, apercu=None):
    dossier = os.path.join(racine, "cursors")
    if os.path.isdir(dossier):
        shutil.rmtree(dossier)
    os.makedirs(dossier)
    cache = {}
    cs = curseurs()
    for nom, (hot, trames, delai) in cs.items():
        with open(os.path.join(dossier, nom), "wb") as fh:
            fh.write(construire(nom, hot, trames, delai, cache))
    n_alias = 0
    for nom, alias in ALIAS.items():
        assert nom in cs, nom
        for a in alias:
            chemin = os.path.join(dossier, a)
            if os.path.lexists(chemin):
                os.remove(chemin)
            os.symlink(nom, chemin)
            n_alias += 1
    with open(os.path.join(racine, "index.theme"), "w", encoding="utf-8") as fh:
        fh.write(INDEX)
    with open(os.path.join(racine, "cursor.theme"), "w", encoding="utf-8") as fh:
        fh.write(INDEX)
    if apercu:
        planche(cs, apercu)
    return len(cs), n_alias


def planche(cs, chemin):
    from PIL import Image, ImageDraw
    noms = list(cs)
    cell = 76
    img = Image.new("RGBA", (cell * len(noms) // 2 + cell, cell * 4 + 20), (0, 0, 0, 255))
    dr = ImageDraw.Draw(img)
    for bloc, fond in enumerate(((20, 28, 23, 255), (244, 248, 241, 255))):
        y0 = bloc * (cell * 2 + 10)
        dr.rectangle([0, y0, img.width, y0 + cell * 2 + 8], fill=fond)
        for i, nom in enumerate(noms):
            hot, trames, _ = cs[nom]
            rgba = rendre(trames[0], 48)
            im = Image.frombytes("RGBA", (48, 48), rgba)
            x = (i % (len(noms) // 2 + 1)) * cell + 14
            y = y0 + (i // (len(noms) // 2 + 1)) * cell + 8
            img.alpha_composite(im, (x, y))
            hx, hy = x + int(hot[0] * 1.5), y + int(hot[1] * 1.5)
            dr.point([(hx, hy)], fill=(255, 0, 255, 255))
            dr.text((x - 10, y + 52), nom[:12], fill=(150, 150, 150, 255))
    img.save(chemin)


if __name__ == "__main__":
    ici = os.path.dirname(os.path.abspath(__file__))
    racine = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ici, "ExoLyx-Curseur")
    apercu = sys.argv[2] if len(sys.argv) > 2 else None
    n, a = generer(racine, apercu)
    print("%d curseurs, %d alias -> %s" % (n, a, racine))

#!/usr/bin/env python3
"""Générateur des thèmes d'icônes ExoLyx.

Trois styles partagent les mêmes pictogrammes :
  * Trait  : contours fins, accent vert, sans tuile ;
  * Duo    : deux tons (aplat doux + aplat plein) et contour, sur tuile ;
  * Relief : dégradés éclairés en haut à gauche, comme la planète du logo.

Chaque style existe en variante sombre (nom de base) et claire (« -Clair »).
Les SVG produits n'utilisent ni <filter>, ni <clipPath>, ni <mask> : seulement
chemins, formes, dégradés linéaires/radiaux et opacité (compatibles QtSvg).

Usage : python3 generer.py [dossier_sortie]   (défaut : ./themes)
Aucune dépendance hors bibliothèque standard.
"""

import math
import os
import shutil
import sys

# --------------------------------------------------------------------------
# Palette (src/branding/palette.md)
# --------------------------------------------------------------------------
PALETTE = {
    "sombre": {
        "accent": "#A8D479", "accent_clair": "#BDD479", "accent_froid": "#8DD479",
        "fond": "#0D1310", "surface": "#141C17", "surface_haute": "#1C2620",
        "bordure": "#2A362E", "texte": "#E6EFE1", "texte_doux": "#97A893",
        "erreur": "#E5766B", "attention": "#E8C26A", "info": "#79C2D4",
    },
    "clair": {
        "accent": "#5E9B2E", "accent_clair": "#7DB547", "accent_froid": "#4E8F3A",
        "fond": "#F4F8F1", "surface": "#FFFFFF", "surface_haute": "#E9F0E4",
        "bordure": "#D3DECB", "texte": "#16201A", "texte_doux": "#5B6B57",
        "erreur": "#C2453A", "attention": "#A87A12", "info": "#2F7F94",
    },
}
# Teintes de la planète du logo (identiques dans les deux variantes)
PLANETE = ["#E4F5B8", "#BDD479", "#6FA845", "#1F3A1F"]
LUMIERE = "#F4FBE2"

TRAIT_EP = 2.75      # épaisseur de trait visible (unités 48) du style Trait
TRAIT_ECH = 1.42     # agrandissement des pictogrammes sans tuile (Trait, petites tailles)
TUILE_ECH = 1.12     # agrandissement des pictogrammes posés sur une tuile
DUO_EP = 2.0         # contour des aplats Duo/Relief
LIGNE_EP = 2.6       # lignes de détail Duo/Relief


def fmt(v):
    s = ("%.2f" % v).rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


# --------------------------------------------------------------------------
# Formes géométriques (description neutre, sans peinture)
# --------------------------------------------------------------------------
class F:
    def __init__(self, tag, transform=None, **attrs):
        self.tag = tag
        self.attrs = attrs
        self.transform = transform

    def svg(self, peinture):
        a = " ".join('%s="%s"' % (k.replace("_", "-"), fmt(v) if isinstance(v, (int, float)) else v)
                     for k, v in self.attrs.items())
        t = ' transform="%s"' % self.transform if self.transform else ""
        return "<%s %s%s %s/>" % (self.tag, a, t, peinture)


def P(d, transform=None):
    return F("path", transform, d=d)


def R(x, y, w, h, rx=0, transform=None):
    return F("rect", transform, x=x, y=y, width=w, height=h, rx=rx)


def C(cx, cy, r, transform=None):
    return F("circle", transform, cx=cx, cy=cy, r=r)


def E(cx, cy, rx, ry, transform=None):
    return F("ellipse", transform, cx=cx, cy=cy, rx=rx, ry=ry)


def L(*pts):
    """Polyligne ouverte : L(x1, y1, x2, y2, ...)."""
    d = "M" + " L".join("%s %s" % (fmt(pts[i]), fmt(pts[i + 1])) for i in range(0, len(pts), 2))
    return P(d)


def engrenage(cx, cy, r_ext, r_int, n, larg=0.42):
    """Contour d'engrenage à n dents trapézoïdales."""
    pts = []
    pas = 2 * math.pi / n
    for i in range(n):
        a = i * pas - math.pi / 2
        for da, r in ((-pas * 0.5, r_int), (-pas * larg * 0.62, r_int), (-pas * larg * 0.42, r_ext),
                      (pas * larg * 0.42, r_ext), (pas * larg * 0.62, r_int)):
            pts.append((cx + r * math.cos(a + da), cy + r * math.sin(a + da)))
    return P("M" + " L".join("%s %s" % (fmt(x), fmt(y)) for x, y in pts) + "Z")


def croissant(cx, cy, r, ox, oy, r2):
    """Croissant : disque (cx,cy,r) privé du disque (ox,oy,r2)."""
    dx, dy = ox - cx, oy - cy
    d = math.hypot(dx, dy)
    a = (r * r - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(r * r - a * a, 0))
    mx, my = cx + a * dx / d, cy + a * dy / d
    p1 = (mx + h * dy / d, my - h * dx / d)
    p2 = (mx - h * dy / d, my + h * dx / d)
    return P("M%s %s A%s %s 0 1 0 %s %s A%s %s 0 0 1 %s %s Z" % (
        fmt(p1[0]), fmt(p1[1]), fmt(r), fmt(r), fmt(p2[0]), fmt(p2[1]),
        fmt(r2), fmt(r2), fmt(p1[0]), fmt(p1[1])))


def etoile4(cx, cy, r, ri=None):
    ri = ri if ri is not None else r * 0.32
    pts = []
    for i in range(8):
        a = i * math.pi / 4 - math.pi / 2
        rr = r if i % 2 == 0 else ri
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return P("M" + " L".join("%s %s" % (fmt(x), fmt(y)) for x, y in pts) + "Z")


def demi_ellipse(cx, cy, rx, ry, rot, avant):
    """Moitié d'une ellipse tournée, coupée par l'horizontale passant par le centre.
    avant=True : moitié basse (passe devant la planète)."""
    t = math.radians(rot)
    # point de l'ellipse où y_monde = cy : sin(rot)*rx*cos(u) + cos(rot)*ry*sin(u) = 0
    u = math.atan2(-math.sin(t) * rx, math.cos(t) * ry)
    pts = []
    for uu in (u, u + math.pi):
        x = cx + rx * math.cos(uu) * math.cos(t) - ry * math.sin(uu) * math.sin(t)
        y = cy + rx * math.cos(uu) * math.sin(t) + ry * math.sin(uu) * math.cos(t)
        pts.append((x, y))
    (x1, y1), (x2, y2) = sorted(pts)
    balayage = 0 if avant else 1
    return P("M%s %s A%s %s %s 0 %d %s %s" % (fmt(x1), fmt(y1), fmt(rx), fmt(ry), fmt(rot),
                                             balayage, fmt(x2), fmt(y2)))


# --------------------------------------------------------------------------
# Peintres : traduisent un rôle sémantique en peinture selon le style
# --------------------------------------------------------------------------
# Rôles :
#   corps   surface principale         arriere  surface de fond (plus sombre)
#   creux   écran / ouverture sombre   papier   feuille claire
#   accent  surface mise en valeur     ligne    trait de détail posé sur une surface
#   vif     trait accentué posé sur le fond (ou sur un creux)
#   embleme trait d'emblème de dossier point / point_vif : pastilles pleines
class Peintre:
    def __init__(self, style, variante, ident):
        self.style = style
        self.variante = variante
        self.c = PALETTE[variante]
        self.ident = ident
        self.defs = []
        self._grad = {}
        self.ech = 1.0           # agrandissement courant (pictogramme agrandi)
        self.gras = 1.0          # renfort des traits pour les petites tailles
        self.ombre = False

    # -- dégradés ---------------------------------------------------------
    def grad(self, nom, xml):
        if nom not in self._grad:
            gid = "%s-%s" % (self.ident, nom)
            self._grad[nom] = gid
            self.defs.append(xml.replace("@ID", gid))
        return "url(#%s)" % self._grad[nom]

    def lin(self, nom, stops, x1=0, y1=0, x2=1, y2=1, user=None):
        unites = ""
        if user:
            x1, y1, x2, y2 = user
            unites = ' gradientUnits="userSpaceOnUse"'
        s = "".join('<stop offset="%s" stop-color="%s"%s/>' % (
            fmt(o), col, (' stop-opacity="%s"' % fmt(op)) if op is not None else "")
            for o, col, op in [(st + (None,))[:3] for st in stops])
        return self.grad(nom, '<linearGradient id="@ID" x1="%s" y1="%s" x2="%s" y2="%s"%s>%s</linearGradient>'
                         % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), unites, s))

    def rad(self, nom, stops, cx=0.34, cy=0.28, r=0.85):
        s = "".join('<stop offset="%s" stop-color="%s"/>' % (fmt(o), col) for o, col in stops)
        return self.grad(nom, '<radialGradient id="@ID" cx="%s" cy="%s" r="%s" fx="%s" fy="%s">%s</radialGradient>'
                         % (fmt(cx), fmt(cy), fmt(r), fmt(cx), fmt(cy), s))

    # -- peintures élémentaires -------------------------------------------
    def ep(self, v):
        return fmt(v * self.gras / self.ech)

    def contour(self, col, ep, op=None):
        o = ' stroke-opacity="%s"' % fmt(op) if op is not None else ""
        return ('fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"%s'
                % (col, self.ep(ep), o))

    def aplat(self, col, op=None, trait=None, ep=DUO_EP):
        s = 'fill="%s"' % col
        if op is not None:
            s += ' fill-opacity="%s"' % fmt(op)
        if trait:
            s += ' stroke="%s" stroke-width="%s" stroke-linejoin="round"' % (trait, self.ep(ep))
        return s

    # -- rôles ------------------------------------------------------------
    def peinture(self, role, plein=False):
        c, st = self.c, self.style
        if self.ombre:
            if role in ("ligne", "vif", "embleme"):
                return self.contour("#000000", LIGNE_EP)
            return 'fill="#000000"'
        if st == "trait":
            base, acc = c["texte"], c["accent"]
            if role in ("corps", "arriere", "creux", "papier"):
                return self.aplat(base) if plein else self.contour(base, TRAIT_EP)
            if role == "accent":
                return self.aplat(acc) if plein else self.contour(acc, TRAIT_EP)
            if role == "ligne":
                return self.contour(base, TRAIT_EP)
            if role in ("vif", "embleme"):
                return self.contour(acc, TRAIT_EP)
            if role == "point":
                return self.aplat(base)
            if role == "point_vif":
                return self.aplat(acc)
        if st == "duo":
            acc = c["accent"]
            sombre = self.variante == "sombre"
            if role == "corps":
                return self.aplat(acc, 0.32 if sombre else 0.24, acc)
            if role == "arriere":
                return self.aplat(acc, 0.62 if sombre else 0.5, acc)
            if role == "creux":
                return self.aplat(c["fond"] if sombre else "#FFFFFF", None, acc)
            if role == "papier":
                return self.aplat(c["texte"] if sombre else "#FFFFFF", None, acc)
            if role == "accent":
                return self.aplat(acc, None, acc)
            if role in ("ligne", "vif"):
                return self.contour(acc, LIGNE_EP)
            if role == "embleme":
                return self.contour(c["fond"] if sombre else "#FFFFFF", LIGNE_EP)
            if role == "point":
                return self.aplat(acc)
            if role == "point_vif":
                return self.aplat(acc)
        if st == "relief":
            if role == "corps":
                g = self.rad("corps", [(0, PLANETE[0]), (0.32, PLANETE[1]), (0.75, PLANETE[2]), (1, "#3C6B2C")])
                return 'fill="%s" stroke="#1F3A1F" stroke-opacity="0.45" stroke-width="%s"' % (g, self.ep(1))
            if role == "arriere":
                g = self.lin("arriere", [(0, "#8DBF5E"), (1, "#2F5A26")])
                return 'fill="%s" stroke="#1F3A1F" stroke-opacity="0.45" stroke-width="%s"' % (g, self.ep(1))
            if role == "creux":
                g = self.lin("creux", [(0, "#0B120E"), (1, "#1E2E24")], 0, 0, 0, 1)
                bord = self.lin("bordcreux", [(0, "#BDD479"), (1, "#4E8F3A")], 0, 0, 0, 1)
                return 'fill="%s" stroke="%s" stroke-width="%s"' % (g, bord, self.ep(1.5))
            if role == "papier":
                g = self.lin("papier", [(0, "#FFFFFF"), (1, "#D3E3C4")], 0, 0, 0.5, 1)
                return 'fill="%s" stroke="#1F3A1F" stroke-opacity="0.3" stroke-width="%s"' % (g, self.ep(1))
            if role == "accent":
                if self.variante == "sombre":
                    g = self.lin("accent", [(0, "#FFFFFF"), (0.45, PLANETE[0]), (1, PLANETE[1])])
                else:
                    g = self.lin("accent", [(0, PLANETE[0]), (0.5, "#A8D479"), (1, "#7DB547")])
                return 'fill="%s" stroke="#1F3A1F" stroke-opacity="0.6" stroke-width="%s"' % (g, self.ep(1))
            if role in ("ligne", "embleme"):
                return self.contour("#1F3A1F", LIGNE_EP, 0.9)
            if role == "vif":
                if self.variante == "sombre":
                    g = self.lin("vif", [(0, PLANETE[0]), (1, "#8DD479")], user=(10, 10, 38, 38))
                else:
                    g = self.lin("vif", [(0, "#7DB547"), (1, "#2F5A26")], user=(10, 10, 38, 38))
                return self.contour(g, LIGNE_EP)
            if role == "point":
                return self.aplat("#1F3A1F", 0.9)
            if role == "point_vif":
                return self.aplat(PLANETE[0] if self.variante == "sombre" else "#4E8F3A")
        raise ValueError((st, role))


# --------------------------------------------------------------------------
# Pictogrammes. Chaque fonction reçoit le style et renvoie une liste
# d'éléments (role, forme[, plein]) ou de chaînes SVG déjà peintes.
# Pictogrammes « de tuile » : dessinés dans la boîte 12..36 (centre 24,24).
# Objets (dossiers, disques…) : dessinés dans toute la boîte 48.
# --------------------------------------------------------------------------
PICTOS = {}


def picto(nom, genre="tuile"):
    def deco(f):
        PICTOS[nom] = (genre, f)
        return f
    return deco


@picto("terminal")
def _(s):
    return [("creux", R(11, 13, 26, 22, 3.5)),
            ("vif", L(16.5, 20, 20.5, 24, 16.5, 28)),
            ("vif", L(23, 29, 30, 29))]


@picto("gestionnaire")
def _(s):
    return [("arriere", P("M11 16 a2.5 2.5 0 0 1 2.5-2.5 h6.2 a2 2 0 0 1 1.5.6 l2.3 2.4 H34.5 a2.5 2.5 0 0 1 2.5 2.5 V32.5 a2.5 2.5 0 0 1-2.5 2.5 H13.5 a2.5 2.5 0 0 1-2.5-2.5Z")),
            ("corps", P("M11 21.5 a2.5 2.5 0 0 1 2.5-2.5 H34.5 a2.5 2.5 0 0 1 2.5 2.5 V32.5 a2.5 2.5 0 0 1-2.5 2.5 H13.5 a2.5 2.5 0 0 1-2.5-2.5Z")),
            ("ligne" if s != "trait" else "vif", L(17, 27.5, 31, 27.5))]


def globe(cx=24, cy=24, r=12):
    return [("corps", C(cx, cy, r)),
            ("ligne", E(cx, cy, r * 0.42, r)),
            ("ligne", L(cx - r, cy, cx + r, cy)),
            ("ligne", P("M%s %s Q%s %s %s %s" % (fmt(cx - r * 0.82), fmt(cy - r * 0.55), fmt(cx), fmt(cy - r * 0.42),
                                                 fmt(cx + r * 0.82), fmt(cy - r * 0.55)))),
            ("ligne", P("M%s %s Q%s %s %s %s" % (fmt(cx - r * 0.82), fmt(cy + r * 0.55), fmt(cx), fmt(cy + r * 0.42),
                                                 fmt(cx + r * 0.82), fmt(cy + r * 0.55))))]


@picto("navigateur")
def _(s):
    el = globe(24, 24, 12)
    if s == "trait":
        el = [("accent", C(24, 24, 12))] + el[1:]
    return el


@picto("internet")
def _(s):
    return PICTOS["navigateur"][1](s)


@picto("reglages")
def _(s):
    return [("corps", engrenage(24, 24, 13, 9.6, 8)),
            ("creux" if s != "trait" else "accent", C(24, 24, 4.3))]


@picto("logitheque")
def _(s):
    return [("corps", P("M12.5 19 H35.5 L34 33.2 a2.8 2.8 0 0 1-2.8 2.5 H16.8 a2.8 2.8 0 0 1-2.8-2.5Z")),
            ("vif", P("M19 19 V17 a5 5 0 0 1 10 0 V19")),
            ("ligne" if s != "trait" else "vif", P("M19 25 a5 5 0 0 0 10 0"))]


def page(x=14, y=11, w=20, h=26, pli=6.5, role="papier"):
    return (role, P("M%s %s H%s L%s %s V%s a2.5 2.5 0 0 1-2.5 2.5 H%s a2.5 2.5 0 0 1-2.5-2.5 V%s a2.5 2.5 0 0 1 2.5-2.5Z" % (
        fmt(x + 2.5), fmt(y), fmt(x + w - pli), fmt(x + w), fmt(y + pli), fmt(y + h - 2.5),
        fmt(x + 2.5), fmt(y + 2.5))))


@picto("editeur")
def _(s):
    crayon = P("M33.6 19.2 l2.8 2.8 L26.2 32.2 l-4.4 1.6 1.6-4.4Z")
    return [page(12, 11, 20, 26),
            ("ligne", P("M25.5 11 V17.5 H32")),
            ("ligne", L(16, 21.5, 24, 21.5)),
            ("ligne", L(16, 26, 22.5, 26)),
            ("ligne", L(16, 30.5, 20, 30.5)),
            ("corps" if s != "trait" else "accent", crayon)]


@picto("calculatrice")
def _(s):
    el = [("corps", R(13.5, 11, 21, 26, 3.5)),
          ("creux", R(16.5, 14, 15, 6, 1.5))]
    for j, y in enumerate((23.5, 28, 32.5)):
        for i, x in enumerate((18.5, 24, 29.5)):
            role = "point_vif" if (i == 2 and j == 2) else "point"
            if s == "trait":
                role = "point_vif" if (i == 2 and j == 2) else "point"
            el.append((role, C(x, y, 1.55)))
    return el


@picto("video")
def _(s):
    if s == "trait":
        return [("corps", R(11, 13.5, 26, 21, 3.5)),
                ("accent", P("M21.2 19.2 L29.2 24 L21.2 28.8Z"), True)]
    return [("creux", R(11, 13.5, 26, 21, 3.5)),
            ("corps", P("M20.8 18.4 L30 24 L20.8 29.6Z"))]


@picto("audio")
def _(s):
    role = "corps" if s != "trait" else "accent"
    return [("vif", P("M20.5 31 V16 L33.5 13 V28")),
            (role, E(17.8, 31.2, 3.6, 3.0, "rotate(-18 17.8 31.2)"), True),
            (role, E(30.8, 28.2, 3.6, 3.0, "rotate(-18 30.8 28.2)"), True)]


@picto("images")
def _(s):
    return [("creux", R(11, 13, 26, 22, 3.5)),
            ("corps" if s != "trait" else "accent", P("M13.5 32.5 L20.5 24.5 L25 29 L28 26 L34.5 32.5Z")),
            ("point_vif", C(29.5, 19, 2.4))]


@picto("bureautique")
def _(s):
    ab = "corps" if s == "relief" else "accent"
    return [page(12, 11, 20, 26),
            ("ligne", P("M25.5 11 V17.5 H32")),
            ("ligne", L(16, 21.5, 23, 21.5)),
            (ab, R(16, 27, 3.2, 6, 0.8), True),
            (ab, R(21.2, 24, 3.2, 9, 0.8), True),
            (ab, R(26.4, 29, 3.2, 4, 0.8), True)]


@picto("aide")
def _(s):
    return [("corps", C(24, 24, 12.5)),
            ("ligne" if s != "trait" else "vif", P("M19.6 20.4 a4.5 4.5 0 1 1 6.6 4 c-1.5 .8-2.2 1.6-2.2 3.2 V28.4")),
            ("point" if s != "trait" else "point_vif", C(24, 32.2, 1.7))]


@picto("mise-a-jour")
def _(s):
    return [("corps", C(24, 24, 12.5)),
            ("ligne", P("M30.2 21.2 A6.8 6.8 0 0 0 17.6 21.6")),
            ("ligne", L(30.4, 17, 30.4, 21.4, 26.2, 21.4)),
            ("ligne", P("M17.8 26.8 A6.8 6.8 0 0 0 30.4 26.4")),
            ("ligne", L(17.6, 31, 17.6, 26.6, 21.8, 26.6))]


@picto("installeur")
def _(s):
    return [("corps", R(11, 25.5, 26, 10.5, 3)),
            ("point_vif" if s == "trait" else "point", C(31.5, 30.75, 1.7)),
            ("vif", L(24, 11, 24, 21)),
            ("vif", L(19.2, 16.8, 24, 21.6, 28.8, 16.8))]


def mini_logo(s, cx=24, cy=24, r=8.5, rx=14, ry=5.2):
    rot = -24
    el = [("vif", demi_ellipse(cx, cy, rx, ry, rot, False)),
          ("corps", C(cx, cy, r)),
          ("vif", demi_ellipse(cx, cy, rx, ry, rot, True))]
    if s == "trait":
        el[1] = ("accent", C(cx, cy, r))
    return el


@picto("bienvenue")
def _(s):
    return mini_logo(s, 23, 25.5) + [("accent", etoile4(33.5, 14.5, 4.6), True)]


@picto("maj-exolyx")
def _(s):
    el = mini_logo(s, 22.5, 22.5, 8, 13, 4.8)
    el += [("accent", C(31.5, 31.5, 6), s != "trait"),
           ({"duo": "embleme", "relief": "ligne"}.get(s, "vif"), L(31.5, 34.5, 31.5, 28.6)),
           ({"duo": "embleme", "relief": "ligne"}.get(s, "vif"), L(28.9, 31, 31.5, 28.4, 34.1, 31))]
    if s == "trait":
        el[-3] = ("accent", C(31.5, 31.5, 6))
    return el



@picto("archives")
def _(s):
    return [("corps", P("M13 20.5 H35 V32.5 a2.5 2.5 0 0 1-2.5 2.5 H15.5 a2.5 2.5 0 0 1-2.5-2.5Z")),
            ("arriere" if s != "trait" else "accent", R(11, 13, 26, 7.5, 2.2)),
            ("creux" if s != "trait" else "ligne", R(20, 24.5, 8, 3.6, 1.8))]


@picto("moniteur")
def _(s):
    return [("creux", R(11, 12, 26, 19, 3.5)),
            ("vif", L(14.5, 22.5, 18.5, 22.5, 20.6, 18, 24, 27, 27.2, 20, 29, 22.5, 33.5, 22.5)),
            ({"trait": "corps", "duo": "ligne"}.get(s, "vif"), L(24, 31, 24, 35)),
            ({"trait": "corps", "duo": "ligne"}.get(s, "vif"), L(19.5, 35.5, 28.5, 35.5))]


@picto("capture")
def _(s):
    k = 5
    el = []
    for (x, y, dx, dy) in ((12, 12, 1, 1), (36, 12, -1, 1), (12, 36, 1, -1), (36, 36, -1, -1)):
        el.append(("vif", L(x, y + dy * k, x, y, x + dx * k, y)))
    el += [("corps", C(24, 24, 6.2)), ("creux" if s != "trait" else "accent", C(24, 24, 2.4))]
    return el


@picto("courriel")
def _(s):
    return [("corps", R(11, 14.5, 26, 19, 3.5)),
            ("ligne" if s != "trait" else "vif", L(12.8, 17.5, 24, 25.5, 35.2, 17.5))]


@picto("apparence")
def _(s):
    return [("corps", P("M24 11.5 c7.5 0 13 5 13 11 c0 4-3 5.5-6 5.5 h-2.4 c-1.6 0-2.6 1.4-1.8 2.9 c.9 1.7.3 4.1-2.8 4.1 c-7.2 0-12.5-5.6-12.5-12 S16.5 11.5 24 11.5Z")),
            ("@info", C(17.5, 21.5, 2.2)), ("@attention", C(22.5, 16.8, 2.2)),
            ("@erreur", C(29, 17.4, 2.2)), ("point_vif" if s == "trait" else "@accent", C(18.4, 28, 2.2))]


@picto("deconnexion")
def _(s):
    return [({"trait": "corps", "duo": "ligne"}.get(s, "vif"), P("M23 12 H16 a3 3 0 0 0-3 3 V33 a3 3 0 0 0 3 3 H23")),
            ("vif", L(20, 24, 35, 24)),
            ("vif", L(30, 19, 35, 24, 30, 29))]


@picto("arret")
def _(s):
    return [("vif", P("M18.1 16.6 A10.5 10.5 0 1 0 29.9 16.6")),
            ("vif", L(24, 11.5, 24, 23))]


@picto("redemarrage")
def _(s):
    return [("vif", P("M33.5 24 A9.5 9.5 0 1 1 30.7 17.3")),
            ("vif", L(31.6, 11.6, 31.4, 17.6, 25.4, 17.4))]


@picto("verrou")
def _(s):
    return [("vif", P("M18.5 22 V18 a5.5 5.5 0 0 1 11 0 V22")),
            ("corps", R(14, 21.5, 20, 14.5, 3.5)),
            ("creux" if s != "trait" else "accent", P("M24 25.8 a2 2 0 0 1 1.1 3.7 V31.6 a1.1 1.1 0 0 1-2.2 0 V29.5 A2 2 0 0 1 24 25.8Z"))]


@picto("veille")
def _(s):
    return [("corps", croissant(23, 25, 11, 30.5, 18.5, 9.2)),
            ("accent", etoile4(32.5, 26, 3.4), True),
            ("accent", etoile4(30, 13.5, 2.4), True)]


# -- catégories --------------------------------------------------------------
@picto("toutes")
def _(s):
    return [("corps", R(12, 12, 10.5, 10.5, 2.8)), ("corps", R(25.5, 12, 10.5, 10.5, 2.8)),
            ("corps", R(12, 25.5, 10.5, 10.5, 2.8)), ("accent", R(25.5, 25.5, 10.5, 10.5, 2.8), s != "trait")]


@picto("multimedia")
def _(s):
    return [("corps", C(24, 24, 12.5)),
            ("accent", P("M21 18.6 L30 24 L21 29.4Z"), True)]


@picto("graphisme")
def _(s):
    return [("corps", P("M24 11 L33 23.5 L28.5 33 H19.5 L15 23.5Z")),
            ("ligne" if s != "trait" else "vif", L(24, 11.5, 24, 22.5)),
            ("point" if s != "trait" else "point_vif", C(24, 24.6, 2.2)),
            ("accent", R(18.5, 33, 11, 4, 1.5), s != "trait")]


@picto("bureau")
def _(s):
    return [("vif", P("M19.5 16 V14 a2 2 0 0 1 2-2 h5 a2 2 0 0 1 2 2 V16")),
            ("corps", R(11, 16, 26, 19, 3.5)),
            ("ligne" if s != "trait" else "corps", L(11.5, 24.5, 36.5, 24.5)),
            ("accent", R(21, 22, 6, 5.2, 1.4), True)]


@picto("developpement")
def _(s):
    return [("vif", L(17.5, 16.5, 10.5, 24, 17.5, 31.5)),
            ("vif", L(30.5, 16.5, 37.5, 24, 30.5, 31.5)),
            ("ligne" if s != "trait" else "corps", L(26.8, 13.5, 21.2, 34.5)) if s == "trait" else ("vif", L(26.8, 13.5, 21.2, 34.5))]


@picto("jeux")
def _(s):
    return [("corps", P("M17.4 16.5 H30.6 a6.2 6.2 0 0 1 6 4.7 l1.6 7 a3.7 3.7 0 0 1-6.4 3.3 L29.4 28.8 H18.6 l-2.4 2.7 a3.7 3.7 0 0 1-6.4-3.3 l1.6-7 A6.2 6.2 0 0 1 17.4 16.5Z")),
            ("ligne" if s != "trait" else "vif", L(15.4, 22.8, 20.4, 22.8)),
            ("ligne" if s != "trait" else "vif", L(17.9, 20.3, 17.9, 25.3)),
            ("point_vif" if s == "trait" else "point", C(29.2, 21.4, 1.6)),
            ("point_vif" if s == "trait" else "point", C(32.4, 24.4, 1.6))]


@picto("systeme")
def _(s):
    el = []
    for v in (19.5, 24, 28.5):
        el += [("vif", L(v, 11, v, 15)), ("vif", L(v, 33, v, 37)),
               ("vif", L(11, v, 15, v)), ("vif", L(33, v, 37, v))]
    el += [("corps", R(15, 15, 18, 18, 3.5)), ("creux" if s != "trait" else "accent", R(20, 20, 8, 8, 1.8))]
    return el


@picto("utilitaires")
def _(s):
    rot = "rotate(40 24 24)"
    return [("corps", R(21.8, 19.5, 4.4, 18.5, 2.2, rot)),
            ("accent", R(14.5, 11.5, 19, 8, 2.4, rot), s != "trait")]


@picto("education")
def _(s):
    return [("arriere" if s != "trait" else "corps", P("M16.5 23 V29.5 c0 2.2 3.4 4.2 7.5 4.2 s7.5-2 7.5-4.2 V23")),
            ("corps" if s != "trait" else "accent", P("M24 13 L38 20 L24 27 L10 20Z")),
            ("vif", L(35, 21.5, 35, 28.5)),
            ("point_vif", C(35, 30, 1.8))]


@picto("sciences")
def _(s):
    fiole = "M20.5 12 H27.5 M21.5 12 V20.2 L13.8 32.2 a2.6 2.6 0 0 0 2.2 4 H32 a2.6 2.6 0 0 0 2.2-4 L26.5 20.2 V12"
    return [("corps", P("M21.5 12 H26.5 V20.2 L34.2 32.2 a2.6 2.6 0 0 1-2.2 4 H16 a2.6 2.6 0 0 1-2.2-4 L21.5 20.2Z")),
            ("accent", P("M17.2 27 H30.8 L34.2 32.2 a2.6 2.6 0 0 1-2.2 4 H16 a2.6 2.6 0 0 1-2.2-4Z"), s != "trait"),
            ("ligne" if s != "trait" else "corps", L(19.5, 12, 28.5, 12)),
            ("point_vif" if s == "trait" else "accent", C(25.5, 22.5, 1.3))]


@picto("preferences")
def _(s):
    el = []
    for y, x in ((16, 28), (24, 18.5), (32, 25)):
        el.append(("vif", L(11.5, y, 36.5, y)))
    for y, x in ((16, 28), (24, 18.5), (32, 25)):
        el.append(("corps", C(x, y, 3.4)) if s == "trait" else ("accent", C(x, y, 3.6)))
    return el


# -- objets : emplacements ---------------------------------------------------
DOS = "M5 12 a3 3 0 0 1 3-3 h10.2 a3 3 0 0 1 2.2 1 L22.6 12.5 H40 a3 3 0 0 1 3 3 V37 a3 3 0 0 1-3 3 H8 a3 3 0 0 1-3-3Z"
FACE = "M5 18.5 a3 3 0 0 1 3-3 H40 a3 3 0 0 1 3 3 V37 a3 3 0 0 1-3 3 H8 a3 3 0 0 1-3-3Z"
FACE_OUVERTE = "M10.2 19.5 H43.4 a2 2 0 0 1 1.9 2.6 L40.7 37.8 a3 3 0 0 1-2.9 2.2 H7.6 a2.4 2.4 0 0 1-2.3-3.1 L7.8 21.4 a2.6 2.6 0 0 1 2.4-1.9Z"


def dossier(s, embleme=None, ouvert=False):
    el = [("arriere", P(DOS))]
    if ouvert:
        if s != "trait":
            el.append(("papier", R(9, 13.5, 30, 14, 1.8)))
        el.append(("corps", P(FACE_OUVERTE)))
    else:
        el.append(("corps", P(FACE)))
    if embleme:
        el += EMBLEMES[embleme](s)
    return el


def _note_emb(s):
    return [("embleme", P("M22.5 33.5 V23 L30 21.5 V31")),
            ("@emb_plein", C(20.6, 33.6, 2.2)), ("@emb_plein", C(28.1, 31.1, 2.2))]


EMBLEMES = {
    "maison": lambda s: [("embleme", L(16.8, 28.5, 24, 22.2, 31.2, 28.5)),
                         ("embleme", P("M19.3 27 V34.5 H28.7 V27")),
                         ("embleme", L(24, 34.5, 24, 30.8))],
    "bureau": lambda s: [("embleme", R(16.5, 22.5, 15, 10, 2)),
                         ("embleme", L(20.5, 35.2, 27.5, 35.2))],
    "documents": lambda s: [("embleme", P("M19.5 21.8 H25.5 L29.5 25.8 V35 H19.5Z")),
                            ("embleme", L(22.3, 29.4, 26.7, 29.4)), ("embleme", L(22.3, 32.2, 26.7, 32.2))],
    "telechargements": lambda s: [("embleme", L(24, 21.5, 24, 31.5)),
                                  ("embleme", L(19.6, 27.4, 24, 31.8, 28.4, 27.4)),
                                  ("embleme", L(18, 35.2, 30, 35.2))],
    "musique": _note_emb,
    "images": lambda s: [("embleme", R(16.5, 22, 15, 13, 2)),
                         ("embleme", L(17.5, 33.5, 21.8, 28.5, 25, 31.5, 27, 29.5, 30.5, 33.5)),
                         ("@emb_plein", C(27.2, 25.8, 1.6))],
    "videos": lambda s: [("embleme", P("M20.5 22.8 L30 28.5 L20.5 34.2Z"))],
    "modeles": lambda s: [("embleme", R(17.5, 22, 13, 13, 2)),
                          ("embleme", L(17.5, 26.6, 30.5, 26.6)), ("embleme", L(22.4, 26.6, 22.4, 35))],
    "partage": lambda s: [("embleme", L(28.6, 23.6, 20, 28.5, 28.6, 33.4)),
                          ("@emb_plein", C(29.2, 23.2, 2.6)), ("@emb_plein", C(19.4, 28.5, 2.6)),
                          ("@emb_plein", C(29.2, 33.8, 2.6))],
    "etiquette": lambda s: [("embleme", P("M17.2 22.4 H24.2 L31.3 29.5 L25 35.8 L17.2 28Z")),
                            ("@emb_plein", C(20.9, 26, 1.5))],
    "reseau": lambda s: [("embleme", C(24, 28.5, 6.8)), ("embleme", E(24, 28.5, 2.8, 6.8)),
                         ("embleme", L(17.2, 28.5, 30.8, 28.5))],
}

def _faire_dossier(emb, ouvert=False):
    return lambda s: dossier(s, emb, ouvert)


for _nom, _emb in (("dossier", None), ("dossier-maison", "maison"), ("dossier-bureau", "bureau"),
                   ("dossier-documents", "documents"), ("dossier-telechargements", "telechargements"),
                   ("dossier-musique", "musique"), ("dossier-images", "images"), ("dossier-videos", "videos"),
                   ("dossier-modeles", "modeles"), ("dossier-partage", "partage"),
                   ("dossier-etiquette", "etiquette"), ("dossier-reseau", "reseau")):
    PICTOS[_nom] = ("objet", _faire_dossier(_emb))
PICTOS["dossier-ouvert"] = ("objet", _faire_dossier(None, True))


def corbeille(s, pleine):
    el = []
    if pleine:
        el += [("papier", P("M13.5 18.5 C12.6 13.6 16.2 10.6 20 12.4 C21.6 8.6 27.4 8.4 28.8 12 C32.6 10.6 36.4 13.8 34.5 18.5Z")),
               ("ligne" if s != "trait" else "vif", P("M20.5 15.5 c1.5-1 3-1 4.5 0"))]
    else:
        el += [({"trait": "corps", "duo": "ligne"}.get(s, "vif"), P("M19.5 10.5 V9.2 a2 2 0 0 1 2-2 h5 a2 2 0 0 1 2 2 V10.5")),
               ("arriere", R(8.5, 10.5, 31, 5, 2.5))]
    el += [("corps", P("M11 18 H37 L35.1 37.4 a3 3 0 0 1-3 2.6 H15.9 a3 3 0 0 1-3-2.6Z"))]
    el += [("ligne" if s != "trait" else "vif", L(x, 22.5, x, 35)) for x in (19, 24, 29)]
    return el


PICTOS["corbeille"] = ("objet", lambda s: corbeille(s, False))
PICTOS["corbeille-pleine"] = ("objet", lambda s: corbeille(s, True))


@picto("disque", "objet")
def _(s):
    return [("arriere", P("M10.5 12 H37.5 a3 3 0 0 1 2.7 1.7 L43 21 H5 L7.8 13.7 A3 3 0 0 1 10.5 12Z")),
            ("corps", R(5, 20.5, 38, 15.5, 3.5)),
            ("ligne" if s != "trait" else "corps", L(10.5, 28.25, 27, 28.25)),
            ("point_vif", C(36.5, 28.25, 2.3))]


@picto("cle-usb", "objet")
def _(s):
    return [("arriere", R(17, 5, 14, 12, 1.8)),
            ("creux" if s != "trait" else "ligne", R(20, 8.5, 2.8, 3.4, 0.6)),
            ("creux" if s != "trait" else "ligne", R(25.2, 8.5, 2.8, 3.4, 0.6)),
            ("corps", R(13, 16.5, 22, 27, 4.5)),
            ("accent", C(24, 31, 4.2), s != "trait")]


@picto("optique", "objet")
def _(s):
    return [("corps", C(24, 24, 19)),
            ("ligne" if s != "trait" else "vif", P("M24 10.5 A13.5 13.5 0 0 0 10.5 24")),
            ("ligne" if s != "trait" else "vif", P("M37.5 24 A13.5 13.5 0 0 1 24 37.5")),
            ("accent" if s != "trait" else "corps", C(24, 24, 6.5)),
            ("creux" if s != "trait" else "corps", C(24, 24, 2.6))]


@picto("logo", "logo")
def _(s):
    return []


# --------------------------------------------------------------------------
# Correspondance nom freedesktop -> (pictogramme, contexte)
# --------------------------------------------------------------------------
ICONES = {
    "apps": {
        "system-file-manager": "gestionnaire", "org.kde.dolphin": "gestionnaire", "org.gnome.Nautilus": "gestionnaire",
        "utilities-terminal": "terminal", "org.kde.konsole": "terminal", "konsole": "terminal",
        "firefox": "navigateur", "org.mozilla.firefox": "navigateur", "web-browser": "navigateur",
        "systemsettings": "reglages", "preferences-system": "reglages", "org.kde.systemsettings": "reglages",
        "plasmadiscover": "logitheque", "org.kde.discover": "logitheque",
        "accessories-text-editor": "editeur", "org.kde.kate": "editeur", "kate": "editeur",
        "accessories-calculator": "calculatrice", "org.kde.kcalc": "calculatrice",
        "multimedia-video-player": "video", "multimedia-audio-player": "audio",
        "image-viewer": "images", "org.kde.gwenview": "images", "gwenview": "images",
        "office": "bureautique", "libreoffice-startcenter": "bureautique",
        "help-browser": "aide", "system-help": "aide",
        "system-software-update": "mise-a-jour",
        "calamares": "installeur", "installer": "installeur", "system-installer": "installeur",
        "exolyx-bienvenue": "bienvenue", "exolyx-maj": "maj-exolyx",
        "archive-manager": "archives", "ark": "archives", "org.kde.ark": "archives",
        "utilities-file-archiver": "archives",
        "utilities-system-monitor": "moniteur", "org.kde.plasma-systemmonitor": "moniteur",
        "accessories-screenshot": "capture", "spectacle": "capture", "org.kde.spectacle": "capture",
        "mail-client": "courriel", "internet-mail": "courriel",
        "preferences-desktop-theme": "apparence",
        "system-log-out": "deconnexion", "system-shutdown": "arret", "system-reboot": "redemarrage",
        "system-lock-screen": "verrou", "system-suspend": "veille",
        "distributor-logo": "logo", "distributor-logo-archlinux": "logo",
    },
    "places": {
        "folder": "dossier", "folder-open": "dossier-ouvert", "user-home": "dossier-maison",
        "user-desktop": "dossier-bureau", "folder-documents": "dossier-documents",
        "folder-download": "dossier-telechargements", "folder-downloads": "dossier-telechargements",
        "folder-music": "dossier-musique", "folder-pictures": "dossier-images", "folder-images": "dossier-images",
        "folder-videos": "dossier-videos", "folder-templates": "dossier-modeles",
        "folder-publicshare": "dossier-partage", "folder-tag": "dossier-etiquette",
        "user-trash": "corbeille", "user-trash-full": "corbeille-pleine",
        "drive-harddisk": "disque", "drive-removable-media": "cle-usb", "drive-removable-media-usb": "cle-usb",
        "media-optical": "optique", "network-workgroup": "dossier-reseau",
        "start-here": "logo", "start-here-kde": "logo", "start-here-kde-plasma": "logo",
    },
    "categories": {
        "applications-all": "toutes", "applications-internet": "internet",
        "applications-multimedia": "multimedia", "applications-graphics": "graphisme",
        "applications-office": "bureau", "applications-development": "developpement",
        "applications-games": "jeux", "applications-system": "systeme",
        "applications-utilities": "utilitaires", "applications-education": "education",
        "applications-science": "sciences", "preferences-other": "preferences",
    },
}
CONTEXTES = {"apps": "Applications", "places": "Places", "categories": "Categories"}

STYLES = {"trait": "Trait", "duo": "Duo", "relief": "Relief"}
COMMENTAIRES = {
    "trait": "contours fins, accent vert pomme",
    "duo": "deux tons, aplats doux et contour",
    "relief": "dégradés en relief, lumière en haut à gauche",
}


# --------------------------------------------------------------------------
# Rendu
# --------------------------------------------------------------------------
def tuile(p):
    c = p.c
    if p.style == "duo":
        if p.variante == "sombre":
            return '<rect x="4" y="4" width="40" height="40" rx="10" fill="%s" stroke="%s" stroke-width="1"/>' % (
                c["surface_haute"], "#34453A")
        return '<rect x="4" y="4" width="40" height="40" rx="10" fill="#FFFFFF" stroke="%s" stroke-width="1"/>' % "#C9D8BE"
    # relief
    if p.variante == "sombre":
        g = p.lin("tuile", [(0, "#2C3D31"), (1, "#0E1611")])
        bord = p.lin("bord", [(0, "#FFFFFF", 0.22), (0.5, "#FFFFFF", 0.04), (1, "#000000", 0.25)], 0, 0, 0, 1)
    else:
        g = p.lin("tuile", [(0, "#FFFFFF"), (1, "#DCE7D3")])
        bord = p.lin("bord", [(0, "#FFFFFF", 0.9), (0.5, "#9FB394", 0.4), (1, "#5B6B57", 0.55)], 0, 0, 0, 1)
    return ('<rect x="3.5" y="5" width="41" height="41" rx="10.5" fill="#000000" fill-opacity="0.18"/>'
            '<rect x="4" y="4" width="40" height="40" rx="10" fill="%s"/>'
            '<rect x="4.5" y="4.5" width="39" height="39" rx="9.5" fill="none" stroke="%s" stroke-width="1"/>'
            % (g, bord))


def couleur_speciale(p, nom):
    c = p.c
    if nom == "emb_plein":
        if p.style == "trait":
            return 'fill="%s"' % c["accent"]
        if p.style == "duo":
            return 'fill="%s"' % (c["fond"] if p.variante == "sombre" else "#FFFFFF")
        return 'fill="#1F3A1F" fill-opacity="0.9"'
    col = c[nom]
    if p.style == "trait":
        return 'fill="%s"' % col
    if p.style == "relief":
        return 'fill="%s" stroke="#000000" stroke-opacity="0.25" stroke-width="0.8"' % col
    return 'fill="%s"' % col


def peindre(p, elements):
    out = []
    for e in elements:
        if isinstance(e, str):
            out.append(e)
            continue
        role, forme = e[0], e[1]
        plein = e[2] if len(e) > 2 else False
        if role.startswith("@"):
            if p.ombre:
                out.append(forme.svg('fill="#000000"'))
            else:
                out.append(forme.svg(couleur_speciale(p, role[1:])))
        else:
            out.append(forme.svg(p.peinture(role, plein)))
    return "".join(out)


def logo(p, cx=24, cy=24, ech=1.0, fond=None, petit=None):
    """Logo ExoLyx redessiné en 48 (traits épaissis) ; petit=16/22 : planète
    plus grosse et orbites plus épaisses pour rester lisible."""
    c = p.c
    r, rx, ry, ep = 12.8 * ech, 21.2 * ech, 7.4 * ech, 3.0 * ech
    lune = (cx + 18.6 * ech, cy - 8.6 * ech, 2.2 * ech)
    if petit:
        r, rx, ry, ep = 14.2, 22.4, 8.4, (4.0 if petit == 16 else 3.5)
        lune = (cx + 19.4, cy - 9.6, 2.8) if petit == 22 else None
    trou = fond or c["fond"]
    if p.style == "relief":
        planete = p.rad("planete", [(0, PLANETE[0]), (0.28, PLANETE[1]), (0.62, PLANETE[2]), (1, PLANETE[3])], 0.36, 0.32, 0.78)
        if p.variante == "sombre":
            oa = p.lin("orbA", [(0, PLANETE[1]), (1, "#8DD479")])
            ob = p.lin("orbB", [(0, "#A8D479"), (1, PLANETE[0])], 1, 0, 0, 1)
        else:
            oa = p.lin("orbA", [(0, "#7DB547"), (1, "#4E8F3A")])
            ob = p.lin("orbB", [(0, "#5E9B2E"), (1, "#8DBF5E")], 1, 0, 0, 1)
        orbA, orbB, plan, lun = oa, ob, 'fill="%s"' % planete, PLANETE[0]
        reflet = ('<path d="M%s %s A%s %s 0 0 1 %s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-opacity="0.6"/>'
                  % (fmt(cx - 8 * ech), fmt(cy - 4.2 * ech), fmt(9.6 * ech), fmt(9.6 * ech), fmt(cx + 4.2 * ech), fmt(cy - 9.2 * ech),
                     LUMIERE, fmt(1.5 * ech)))
    elif p.style == "duo":
        orbA = orbB = c["accent_clair"] if p.variante == "sombre" else c["accent_froid"]
        plan = 'fill="%s"' % c["accent"]
        lun = orbA
        reflet = croissant(cx, cy, r, cx + 4.2 * ech, cy + 4 * ech, r * 1.02).svg(
            'fill="#FFFFFF" fill-opacity="%s"' % ("0.28" if p.variante == "sombre" else "0.35"))
    else:
        orbA = orbB = c["texte"]
        plan = 'fill="%s"' % c["accent"]
        lun = c["accent"]
        reflet = ""
    rot = 24
    s = []
    for sens, col in ((-rot, orbA), (rot, orbB)):
        s.append(demi_ellipse(cx, cy, rx, ry, sens, False).svg(
            'fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-opacity="%s"' % (
                col, fmt(ep), "0.6" if p.style != "trait" else "1")))
    s.append('<circle cx="%s" cy="%s" r="%s" %s/>' % (fmt(cx), fmt(cy), fmt(r), plan))
    s.append(reflet)
    for sens, col in ((rot, orbB), (-rot, orbA)):
        d = demi_ellipse(cx, cy, rx, ry, sens, True)
        s.append(d.svg('fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"' % (trou, fmt(ep + 2.4 * ech))))
        s.append(d.svg('fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"' % (col, fmt(ep))))
    if lune:
        s.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (fmt(lune[0]), fmt(lune[1]), fmt(lune[2]), lun))
    return "".join(s)


def rendre(nom_picto, style, variante, ident, petit=None):
    """Rend un pictogramme. petit=16 ou 22 : version sans tuile, agrandie et
    aux traits renforcés, destinée aux dossiers de taille fixe."""
    genre, f = PICTOS[nom_picto]
    p = Peintre(style, variante, ident)
    corps = []
    if genre == "logo":
        corps.append(logo(p, petit=petit))
    else:
        elements = f(style)
        agrandi = genre == "tuile" and (style == "trait" or petit)
        if genre == "tuile" and not agrandi:
            corps.append(tuile(p))
            p.ech = TUILE_ECH
        if agrandi:
            p.ech = TRAIT_ECH
            if petit:
                p.gras = {"trait": 3.0 / TRAIT_EP, "duo": 1.3, "relief": 1.3}[style]
                if petit == 22:
                    p.gras = 1 + (p.gras - 1) * 0.6
        t = "translate(24 24) scale(%s) translate(-24 -24)" % fmt(p.ech) if p.ech != 1 else None
        if style == "relief":
            p.ombre = True
            dec = "translate(0 1.2)" + (" " + t if t else "")
            corps.append('<g transform="%s" opacity="%s">%s</g>' % (
                dec, "0.35" if variante == "sombre" else "0.16", peindre(p, elements)))
            p.ombre = False
        if t:
            corps.append('<g transform="%s">%s</g>' % (t, peindre(p, elements)))
        else:
            corps.append(peindre(p, elements))
    defs = "<defs>%s</defs>" % "".join(p.defs) if p.defs else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">'
            '%s%s</svg>\n' % (defs, "".join(corps)))


PETITS = (16, 22)
CTX_PETITS = ("apps", "places", "categories")


def nom_theme(style, variante):
    return "ExoLyx-%s%s" % (STYLES[style], "-Clair" if variante == "clair" else "")


def index_theme(style, variante):
    nom = nom_theme(style, variante)
    herite = "breeze-dark" if variante == "sombre" else "breeze"
    dirs = ["%d/%s" % (n, ctx) for n in PETITS for ctx in CTX_PETITS] + ["scalable/%s" % ctx for ctx in ICONES]
    lignes = [
        "[Icon Theme]",
        "Name=%s" % nom,
        "Comment=ExoLyx %s (%s) — %s" % (STYLES[style], "sombre" if variante == "sombre" else "clair",
                                         COMMENTAIRES[style]),
        "Inherits=%s" % herite,
        "Example=folder",
        "DisplayDepth=32",
        "Directories=%s" % ",".join(dirs),
        "",
    ]
    for n in PETITS:
        for ctx in CTX_PETITS:
            lignes += ["[%d/%s]" % (n, ctx), "Size=%d" % n, "Context=%s" % CONTEXTES[ctx], "Type=Fixed", ""]
    for ctx in ICONES:
        lignes += ["[scalable/%s]" % ctx, "Size=48", "MinSize=16", "MaxSize=256",
                   "Context=%s" % CONTEXTES[ctx], "Type=Scalable", ""]
    return "\n".join(lignes)


def generer(sortie):
    total = {}
    for style in STYLES:
        for variante in ("sombre", "clair"):
            nom = nom_theme(style, variante)
            racine = os.path.join(sortie, nom)
            if os.path.isdir(racine):
                shutil.rmtree(racine)
            n = 0
            for ctx, table in ICONES.items():
                d = os.path.join(racine, "scalable", ctx)
                os.makedirs(d, exist_ok=True)
                for icone, pic in sorted(table.items()):
                    ident = "%s-%s" % (pic, style[0] + variante[0])
                    with open(os.path.join(d, icone + ".svg"), "w", encoding="utf-8") as fh:
                        fh.write(rendre(pic, style, variante, ident))
                    n += 1
                    if ctx in CTX_PETITS and PICTOS[pic][0] in ("tuile", "logo"):
                        for taille in PETITS:
                            dp = os.path.join(racine, str(taille), ctx)
                            os.makedirs(dp, exist_ok=True)
                            with open(os.path.join(dp, icone + ".svg"), "w", encoding="utf-8") as fh:
                                fh.write(rendre(pic, style, variante, ident + "-p%d" % taille, taille))
            with open(os.path.join(racine, "index.theme"), "w", encoding="utf-8") as fh:
                fh.write(index_theme(style, variante))
            total[nom] = n
    return total


APERCU = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Icônes ExoLyx</title>
<style>
  :root { --accent:#A8D479; --fond:#0D1310; --surface:#141C17; --texte:#E6EFE1; --doux:#97A893;
          --clair-fond:#F4F8F1; --clair-texte:#16201A; --bordure:#2A362E; }
  body { margin:0; background:var(--fond); color:var(--texte); font:14px Inter, system-ui, sans-serif; }
  header { padding:20px 16px 8px; }
  h1 { margin:0 0 4px; font-size:22px; color:var(--accent); }
  p { margin:0; color:var(--doux); }
  .outils { display:flex; flex-wrap:wrap; gap:8px; padding:12px 16px; }
  button { background:var(--surface); color:var(--texte); border:1px solid var(--bordure); border-radius:6px;
           padding:6px 12px; font:inherit; cursor:pointer; }
  button.actif { border-color:var(--accent); color:var(--accent); }
  section { padding:12px 16px 20px; }
  section.clair { background:var(--clair-fond); color:var(--clair-texte); }
  h2 { font-size:15px; margin:8px 0 10px; }
  .grille { display:grid; grid-template-columns:repeat(auto-fill, minmax(92px, 1fr)); gap:6px; }
  figure { margin:0; display:flex; flex-direction:column; align-items:center; gap:6px; padding:8px 2px;
           border-radius:10px; }
  figure:hover { background:rgba(168,212,121,.12); }
  figcaption { font-size:10px; opacity:.7; text-align:center; word-break:break-all; }
  img { image-rendering:auto; }
</style>
</head>
<body>
<header>
  <h1>Thèmes d'icônes ExoLyx</h1>
  <p>Trait, Duo et Relief — variantes sombre et claire. Ouvrir depuis src/icones/ (les SVG sont lus dans themes/).</p>
</header>
<div class="outils" id="tailles"></div>
<div id="planches"></div>
<script>
const ICONES = @ICONES;
const STYLES = @STYLES;
const PETITS = @PETITS;
let taille = 48;
function dessiner() {
  const racine = document.getElementById('planches');
  racine.innerHTML = '';
  for (const variante of ['sombre', 'clair']) {
    for (const [cle, nomStyle] of STYLES) {
      const theme = 'ExoLyx-' + nomStyle + (variante === 'clair' ? '-Clair' : '');
      const sec = document.createElement('section');
      if (variante === 'clair') sec.className = 'clair';
      sec.innerHTML = '<h2>' + theme + ' — ' + taille + ' px</h2>';
      const g = document.createElement('div');
      g.className = 'grille';
      for (const [ctx, nom, petit] of ICONES) {
        const dossier = (petit && PETITS.includes(taille)) ? String(taille) : 'scalable';
        const f = document.createElement('figure');
        const img = document.createElement('img');
        img.src = 'themes/' + theme + '/' + dossier + '/' + ctx + '/' + nom + '.svg';
        img.width = img.height = taille;
        img.alt = nom;
        const c = document.createElement('figcaption');
        c.textContent = nom;
        f.append(img, c);
        g.append(f);
      }
      sec.append(g);
      racine.append(sec);
    }
  }
}
const barre = document.getElementById('tailles');
for (const t of [16, 22, 32, 48, 64]) {
  const b = document.createElement('button');
  b.textContent = t + ' px';
  b.onclick = () => { taille = t; [...barre.children].forEach(x => x.classList.toggle('actif', x === b)); dessiner(); };
  if (t === taille) b.classList.add('actif');
  barre.append(b);
}
dessiner();
</script>
</body>
</html>
"""


def ecrire_apercu(chemin):
    import json
    icones = []
    for ctx, table in ICONES.items():
        for nom, pic in sorted(table.items()):
            icones.append([ctx, nom, ctx in CTX_PETITS and PICTOS[pic][0] in ("tuile", "logo")])
    html = (APERCU.replace("@ICONES", json.dumps(icones))
            .replace("@STYLES", json.dumps(list(STYLES.items())))
            .replace("@PETITS", json.dumps(list(PETITS))))
    with open(chemin, "w", encoding="utf-8") as fh:
        fh.write(html)


if __name__ == "__main__":
    ici = os.path.dirname(os.path.abspath(__file__))
    sortie = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ici, "themes")
    for nom, n in generer(sortie).items():
        print("%-20s %3d icônes" % (nom, n))
    print("Pictogrammes distincts : %d" % len(PICTOS))
    if len(sys.argv) == 1:
        ecrire_apercu(os.path.join(ici, "apercu.html"))

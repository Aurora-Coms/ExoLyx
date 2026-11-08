"""Briques SVG communes au logo ExoLyx « Orbite tressée × Relief ».

Reprend fidèlement la géométrie de src/branding/logo.svg (planète r=66,
orbites rx=112 / ry=38 inclinées de ±24°, trait 9, espace de tressage 15)
et la rend paramétrable (centre, rayon, palette) pour les fonds d'écran,
SDDM, Plymouth et GRUB.

Contraintes : pas de <filter> (voir docs/CONVENTIONS.md) ; les halos sont
faits avec des dégradés radiaux.
"""

import math
import random

# Palette (src/branding/palette.md)
SOMBRE = {
    "accent": "#A8D479", "accent_clair": "#BDD479", "accent_froid": "#8DD479",
    "fond": "#0D1310", "surface": "#141C17", "surface_haute": "#1C2620",
    "bordure": "#2A362E", "texte": "#E6EFE1", "texte_doux": "#97A893",
    "erreur": "#E5766B",
    # orbites du logo
    "orbiteA": ("#BDD479", "#8DD479"),
    "orbiteB": ("#A8D479", "#E4F5B8"),
    "planete": ("#E4F5B8", "#BDD479", "#6FA845", "#1F3A1F"),
    "reflet": "#F4FBE2",
    "lune": "#E4F5B8",
}
CLAIR = {
    "accent": "#5E9B2E", "accent_clair": "#7DB547", "accent_froid": "#4E8F3A",
    "fond": "#F4F8F1", "surface": "#FFFFFF", "surface_haute": "#E9F0E4",
    "bordure": "#D3DECB", "texte": "#16201A", "texte_doux": "#5B6B57",
    "erreur": "#C2453A",
    "orbiteA": ("#7DB547", "#4E8F3A"),
    "orbiteB": ("#5E9B2E", "#A8D479"),
    "planete": ("#E4F5B8", "#BDD479", "#6FA845", "#2B4F26"),
    "reflet": "#F4FBE2",
    "lune": "#7DB547",
}

# Géométrie du logo, rapportée au rayon de la planète (66)
RX = 112 / 66
RY = 38 / 66
TRAIT = 9 / 66
ESPACE = 15 / 66
INCLINAISON = 24
LUNE = (98 / 66, -44 / 66, 9 / 66)  # position (dx, dy) et rayon


def defs_logo(p, pre="l"):
    """Dégradés du logo (identifiants préfixés par `pre`)."""
    a0, a1 = p["orbiteA"]
    b0, b1 = p["orbiteB"]
    s0, s1, s2, s3 = p["planete"]
    return f"""
    <radialGradient id="{pre}planete" cx="0.36" cy="0.32" r="0.78">
      <stop offset="0" stop-color="{s0}"/>
      <stop offset="0.28" stop-color="{s1}"/>
      <stop offset="0.62" stop-color="{s2}"/>
      <stop offset="1" stop-color="{s3}"/>
    </radialGradient>
    <linearGradient id="{pre}orbiteA" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{a0}"/><stop offset="1" stop-color="{a1}"/>
    </linearGradient>
    <linearGradient id="{pre}orbiteB" x1="1" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{b0}"/><stop offset="1" stop-color="{b1}"/>
    </linearGradient>
    <radialGradient id="{pre}halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{p['accent']}" stop-opacity="0.30"/>
      <stop offset="0.45" stop-color="{p['accent']}" stop-opacity="0.10"/>
      <stop offset="1" stop-color="{p['accent']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="{pre}halolune" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{p['lune']}" stop-opacity="0.55"/>
      <stop offset="1" stop-color="{p['lune']}" stop-opacity="0"/>
    </radialGradient>"""


def _ellipse(cx, cy, r, angle, stroke, largeur, opacite=1.0, rx=RX, ry=RY):
    return (f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx * r:.2f}" ry="{ry * r:.2f}" '
            f'transform="rotate({angle} {cx:.2f} {cy:.2f})" stroke="{stroke}" '
            f'stroke-width="{largeur:.2f}" opacity="{opacite}"/>')


def clips(cx, cy, W, H, pre="l"):
    return (f'<clipPath id="{pre}dessus"><rect x="0" y="0" width="{W}" height="{cy:.2f}"/></clipPath>'
            f'<clipPath id="{pre}dessous"><rect x="0" y="{cy:.2f}" width="{W}" height="{H - cy:.2f}"/></clipPath>')


def defs_espace(cx, cy, r, couleur, pre="l"):
    """Dégradé de l'espace de tressage : plein sur la planète et au croisement
    des orbites, puis s'efface vers les boucles extérieures (évite l'encoche
    nette à la jonction avant/arrière sur les grands rendus)."""
    return (f'<radialGradient id="{pre}espace" gradientUnits="userSpaceOnUse" cx="{cx:.2f}" '
            f'cy="{cy:.2f}" r="{r * 1.15:.2f}"><stop offset="0.82" stop-color="{couleur}" '
            f'stop-opacity="1"/><stop offset="1" stop-color="{couleur}" stop-opacity="0"/>'
            f'</radialGradient>')


def orbites_arriere(cx, cy, r, pre="l", rx=RX, ry=RY, opacite=0.55):
    t = TRAIT * r
    return (f'<g fill="none" stroke-linecap="round" clip-path="url(#{pre}dessus)">'
            + _ellipse(cx, cy, r, -INCLINAISON, f"url(#{pre}orbiteA)", t, opacite, rx, ry)
            + _ellipse(cx, cy, r, INCLINAISON, f"url(#{pre}orbiteB)", t, opacite, rx, ry)
            + "</g>")


def orbites_avant(cx, cy, r, couleur_espace, pre="l", rx=RX, ry=RY, espace=True):
    t, e = TRAIT * r, ESPACE * r
    s = f'<g fill="none" stroke-linecap="round" clip-path="url(#{pre}dessous)">'
    for ang, grad in ((INCLINAISON, "orbiteB"), (-INCLINAISON, "orbiteA")):
        if espace:
            s += _ellipse(cx, cy, r, ang, couleur_espace, e, 1.0, rx, ry)
        s += _ellipse(cx, cy, r, ang, f"url(#{pre}{grad})", t, 1.0, rx, ry)
    return s + "</g>"


def planete(cx, cy, r, p, pre="l", halo=True, reflet=True):
    s = ""
    if halo:
        s += f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r * 2.1:.2f}" fill="url(#{pre}halo)"/>'
    s += f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="url(#{pre}planete)"/>'
    if reflet:
        k = r / 66
        s += (f'<path d="M{cx - 44 * k:.2f} {cy - 24 * k:.2f} A{50 * k:.2f} {50 * k:.2f} 0 0 1 '
              f'{cx + 22 * k:.2f} {cy - 56 * k:.2f}" fill="none" stroke="{p["reflet"]}" '
              f'stroke-width="{5 * k:.2f}" stroke-linecap="round" opacity="0.55"/>')
    return s


def lune(cx, cy, r, p, pre="l", halo=True):
    dx, dy, lr = LUNE
    x, y, rr = cx + dx * r, cy + dy * r, lr * r
    s = ""
    if halo:
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{rr * 3.2:.2f}" fill="url(#{pre}halolune)"/>'
    return s + f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{rr:.2f}" fill="{p["lune"]}"/>'


def logo_complet(cx, cy, r, p, W, H, couleur_espace, pre="l", halo=True, opacite_arriere=0.78):
    """Logo entier (sans <svg>), à insérer dans un document plus grand.
    `couleur_espace` peut être une couleur ou « url(#…espace) » (voir defs_espace)."""
    return (orbites_arriere(cx, cy, r, pre, opacite=opacite_arriere) + planete(cx, cy, r, p, pre, halo)
            + orbites_avant(cx, cy, r, couleur_espace, pre) + lune(cx, cy, r, p, pre, halo))


def etoiles(W, H, n, p, graine=7, eviter=None, clair=False):
    """Champ d'étoiles déterministe. `eviter` = (cx, cy, rayon) zone vide."""
    rnd = random.Random(graine)
    k = min(W, H) / 1080
    s = []
    while len(s) < n:
        x, y = rnd.random() * W, rnd.random() * H
        if eviter and math.hypot(x - eviter[0], y - eviter[1]) < eviter[2]:
            continue
        rr = (0.5 + rnd.random() ** 3 * 1.6) * k
        op = 0.12 + rnd.random() * (0.35 if clair else 0.55)
        coul = p["accent"] if (clair or rnd.random() < 0.3) else p["texte"]
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.2f}" fill="{coul}" opacity="{op:.2f}"/>')
    return "".join(s)

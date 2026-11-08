"""Fichiers récents (~/.local/share/recently-used.xbel, format XBEL freedesktop)."""

import os
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime


def chemin_xbel():
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "recently-used.xbel")


def _date(texte):
    if not texte:
        return 0.0
    texte = texte.strip().replace("Z", "+00:00")
    if "." in texte:
        # fractions de seconde de longueur variable
        avant, _, apres = texte.partition(".")
        chiffres = "".join(c for c in apres if c.isdigit())
        reste = apres[len(chiffres):]
        texte = f"{avant}.{chiffres[:6].ljust(6, '0')}{reste}"
    try:
        return datetime.fromisoformat(texte).timestamp()
    except ValueError:
        return 0.0


def analyser(texte, existe=os.path.exists, limite=12):
    """Liste de (chemin, horodatage) du plus récent au plus ancien, fichiers locaux existants."""
    try:
        racine = ET.fromstring(texte)
    except ET.ParseError:
        return []
    vus = {}
    for b in racine.iter("bookmark"):
        href = b.get("href", "")
        if not href.startswith("file://"):
            continue
        chemin = urllib.parse.unquote(urllib.parse.urlparse(href).path)
        quand = max(_date(b.get("modified")), _date(b.get("visited")), _date(b.get("added")))
        if chemin in vus and vus[chemin] >= quand:
            continue
        vus[chemin] = quand
    resultat = [(c, q) for c, q in vus.items() if existe(c) and not os.path.isdir(c)]
    resultat.sort(key=lambda x: x[1], reverse=True)
    return resultat[:limite]


def lire(limite=12):
    try:
        with open(chemin_xbel(), encoding="utf-8", errors="replace") as f:
            return analyser(f.read(), limite=limite)
    except OSError:
        return []

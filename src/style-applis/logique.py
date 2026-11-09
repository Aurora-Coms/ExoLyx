# SPDX-License-Identifier: GPL-3.0-or-later
"""Style des applications : « Ardoise » (ExoLyx) ou « D'origine » (suit les couleurs du bureau).

Les valeurs par défaut (Ardoise) sont dans /etc/xdg/<appli>rc (paquet exolyx-applis).
Ce module écrit les choix de l'utilisateur dans ~/.config/<appli>rc, qui l'emporte.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
ETAT = CONFIG / "exolyx" / "style-applis.json"
MARQUEUR_FIREFOX = CONFIG / "exolyx" / "firefox-origine"

ARDOISE, ORIGINE = "ardoise", "origine"

# Pour chaque logiciel : fichier de config et clés à écrire selon le style.
# « Default » = schéma de couleurs du bureau (convention KColorSchemeManager).
def _ui(valeur):
    return {("UiSettings", "ColorScheme"): valeur}

APPLIS = [
    {"id": "firefox", "nom": "Firefox", "icone": "firefox", "fichier": None},
    {"id": "konsole", "nom": "Terminal", "icone": "utilities-terminal", "fichier": "konsolerc",
     ARDOISE: {**_ui("Ardoise"), ("UiSettings", "WindowColorScheme"): "Ardoise", ("Desktop Entry", "DefaultProfile"): "Ardoise.profile"},
     ORIGINE: {**_ui("Default"), ("UiSettings", "WindowColorScheme"): "Default", ("Desktop Entry", "DefaultProfile"): "ExoLyx.profile"}},
    {"id": "kate", "nom": "Éditeur de texte", "icone": "accessories-text-editor", "fichier": "katerc",
     ARDOISE: {**_ui("Ardoise"), ("KTextEditor Renderer", "Auto Color Theme Selection"): "false", ("KTextEditor Renderer", "Color Theme"): "Ardoise"},
     ORIGINE: {**_ui("Default"), ("KTextEditor Renderer", "Auto Color Theme Selection"): "true", ("KTextEditor Renderer", "Color Theme"): "ExoLyx"}},
    {"id": "discover", "nom": "Logithèque", "icone": "plasmadiscover", "fichier": "discoverrc"},
    {"id": "systemsettings", "nom": "Configuration du système", "icone": "systemsettings", "fichier": "systemsettingsrc"},
    {"id": "spectacle", "nom": "Captures d'écran", "icone": "accessories-screenshot", "fichier": "spectaclerc"},
    {"id": "gwenview", "nom": "Images", "icone": "image-viewer", "fichier": "gwenviewrc"},
    {"id": "okular", "nom": "Documents PDF", "icone": "okular", "fichier": "okularrc"},
    {"id": "ark", "nom": "Archives", "icone": "archive-manager", "fichier": "arkrc"},
    {"id": "kcalc", "nom": "Calculatrice", "icone": "accessories-calculator", "fichier": "kcalcrc"},
]
for _a in APPLIS:
    _a.setdefault(ARDOISE, _ui("Ardoise"))
    _a.setdefault(ORIGINE, _ui("Default"))
IDS = [a["id"] for a in APPLIS]


# ---- État --------------------------------------------------------------------------------

def etat_par_defaut():
    return {"style": ARDOISE, "applis": {i: True for i in IDS}}

def lire_etat(chemin: Path = None):
    chemin = chemin or ETAT
    e = etat_par_defaut()
    try:
        d = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return e
    if d.get("style") in (ARDOISE, ORIGINE):
        e["style"] = d["style"]
    for i, v in (d.get("applis") or {}).items():
        if i in e["applis"]:
            e["applis"][i] = bool(v)
    return e

def ecrire_etat(e, chemin: Path = None):
    chemin = chemin or ETAT
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")

def style_de(e, appli_id):
    """Style effectif d'un logiciel : Ardoise seulement si le style global l'est et qu'il est coché."""
    return ARDOISE if e["style"] == ARDOISE and e["applis"].get(appli_id, True) else ORIGINE


# ---- Écriture des fichiers KDE (format INI, sans toucher au reste) ------------------------

_GROUPE = re.compile(r"^\[(.+)\]\s*$")

def regler(chemin: Path, groupe: str, cle: str, valeur: str):
    """Écrit cle=valeur dans [groupe] d'un fichier de config KDE, en préservant le reste."""
    lignes = chemin.read_text(encoding="utf-8").splitlines() if chemin.exists() else []
    debut = fin = None
    for n, l in enumerate(lignes):
        m = _GROUPE.match(l)
        if m:
            if debut is not None and fin is None:
                fin = n
            if m.group(1) == groupe:
                debut = n
    if debut is None:
        if lignes and lignes[-1].strip():
            lignes.append("")
        lignes += [f"[{groupe}]", f"{cle}={valeur}"]
    else:
        fin = fin if fin is not None else len(lignes)
        for n in range(debut + 1, fin):
            if lignes[n].split("=", 1)[0].strip() == cle and "=" in lignes[n]:
                lignes[n] = f"{cle}={valeur}"
                break
        else:
            # insérer après la dernière ligne non vide du groupe
            pos = fin
            while pos > debut + 1 and not lignes[pos - 1].strip():
                pos -= 1
            lignes.insert(pos, f"{cle}={valeur}")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8")

def lire(chemin: Path, groupe: str, cle: str):
    if not chemin.exists():
        return None
    courant = None
    for l in chemin.read_text(encoding="utf-8").splitlines():
        m = _GROUPE.match(l)
        if m:
            courant = m.group(1)
        elif courant == groupe and "=" in l and l.split("=", 1)[0].strip() == cle:
            return l.split("=", 1)[1].strip()
    return None


def appliquer(e, config: Path = None):
    """Écrit les réglages de chaque logiciel. Renvoie la liste (id, style) appliquée."""
    config = config or CONFIG
    fait = []
    for a in APPLIS:
        s = style_de(e, a["id"])
        if a["id"] == "firefox":
            marqueur = config / "exolyx" / "firefox-origine"
            if s == ORIGINE:
                marqueur.parent.mkdir(parents=True, exist_ok=True)
                marqueur.touch()
            elif marqueur.exists():
                marqueur.unlink()
        else:
            for (groupe, cle), valeur in a[s].items():
                regler(config / a["fichier"], groupe, cle, valeur)
        fait.append((a["id"], s))
    return fait

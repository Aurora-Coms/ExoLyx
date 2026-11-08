# SPDX-License-Identifier: GPL-3.0-or-later
"""Logique pure de l'appli de bienvenue ExoLyx (sans Qt, testable).

Détection du matériel, catalogue d'applications, thèmes, persistance.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ICI = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
HELPER = "/usr/lib/exolyx/exolyx-helper"
INSTALLATEUR = "/usr/bin/exolyx-installer"
URL_AIDE = "https://github.com/Aurora-Coms/ExoLyx/wiki"
URL_DEPOT = "https://github.com/Aurora-Coms/ExoLyx"


def dossier_config() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / "exolyx"


def fichier_etat() -> Path:
    return dossier_config() / "bienvenue.json"


def chemin_logo() -> str:
    """Logo installé, ou celui de src/branding en développement."""
    for p in (ICI / "images" / "logo.svg", ICI.parent / "branding" / "logo.svg"):
        if p.exists():
            return str(p)
    return ""


def mode_live() -> bool:
    """Vrai sur l'ISO live (archiso monte /run/archiso)."""
    force = os.environ.get("EXOLYX_LIVE")
    if force is not None:
        return force == "1"
    return os.path.isdir("/run/archiso")


# ---------------------------------------------------------------------------
# Persistance (~/.config/exolyx/bienvenue.json)
# ---------------------------------------------------------------------------
def lire_etat(chemin: Path | None = None) -> dict:
    chemin = chemin or fichier_etat()
    try:
        with open(chemin, encoding="utf-8") as f:
            donnees = json.load(f)
        return donnees if isinstance(donnees, dict) else {}
    except (OSError, ValueError):
        return {}


def ecrire_etat(etat: dict, chemin: Path | None = None) -> None:
    chemin = chemin or fichier_etat()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False, indent=2)
    os.replace(tmp, chemin)


def doit_afficher_au_demarrage(chemin: Path | None = None, live: bool | None = None) -> bool:
    """L'appli s'ouvre au démarrage tant qu'elle n'est pas terminée.

    En live, elle s'ouvre toujours (pas de persistance utile)."""
    if live if live is not None else mode_live():
        return True
    etat = lire_etat(chemin)
    if etat.get("termine"):
        return bool(etat.get("afficherAuDemarrage", False))
    return True


# ---------------------------------------------------------------------------
# Thème de l'interface (conventions : kdeglobals [General] ColorScheme)
# ---------------------------------------------------------------------------
PALETTES = {
    True: {  # sombre
        "accent": "#A8D479", "accentClair": "#BDD479", "accentFroid": "#8DD479",
        "fond": "#0D1310", "surface": "#141C17", "surfaceHaute": "#1C2620",
        "bordure": "#2A362E", "texte": "#E6EFE1", "texteDoux": "#97A893",
        "erreur": "#E5766B", "attention": "#E8C26A", "info": "#79C2D4",
        "surAccent": "#0D1310",
        # voiles (#AARRGGBB) : fonds teintés
        "accentVoile": "#24A8D479", "infoVoile": "#1A79C2D4", "infoBord": "#8079C2D4",
    },
    False: {  # clair
        "accent": "#5E9B2E", "accentClair": "#7DB547", "accentFroid": "#4E8F3A",
        "fond": "#F4F8F1", "surface": "#FFFFFF", "surfaceHaute": "#E9F0E4",
        "bordure": "#D3DECB", "texte": "#16201A", "texteDoux": "#5B6B57",
        "erreur": "#C2453A", "attention": "#A87A12", "info": "#2F7F94",
        "surAccent": "#FFFFFF",
        "accentVoile": "#265E9B2E", "infoVoile": "#1A2F7F94", "infoBord": "#802F7F94",
    },
}


def theme_sombre(kdeglobals: str | None = None) -> bool:
    chemin = kdeglobals or os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config"),
        "kdeglobals")
    try:
        groupe = None
        with open(chemin, encoding="utf-8", errors="replace") as f:
            for ligne in f:
                ligne = ligne.strip()
                if ligne.startswith("["):
                    groupe = ligne
                elif groupe == "[General]" and ligne.startswith("ColorScheme="):
                    return "Clair" not in ligne.split("=", 1)[1]
    except OSError:
        pass
    return True


# ---------------------------------------------------------------------------
# Apparence : noms fournis par le paquet exolyx-theme
# ---------------------------------------------------------------------------
STYLES_ICONES = ["Trait", "Duo", "Relief"]
DESCRIPTIONS_ICONES = {
    "Trait": "Contours fins, épurés",
    "Duo": "Deux tons, équilibré",
    "Relief": "Dégradés et volume",
}


def schema_couleurs(sombre: bool) -> str:
    return "ExoLyx" if sombre else "ExoLyxClair"


def look_and_feel(sombre: bool) -> str:
    return "org.exolyx.sombre" if sombre else "org.exolyx.clair"


def theme_icones(style: str, sombre: bool) -> str:
    if style not in STYLES_ICONES:
        raise ValueError(f"style d'icônes inconnu : {style}")
    return f"ExoLyx-{style}" + ("" if sombre else "-Clair")


def dossiers_icones() -> list[str]:
    env = os.environ.get("EXOLYX_DOSSIER_ICONES")
    if env:
        return [env]
    return [os.path.expanduser("~/.local/share/icons"), "/usr/share/icons"]


APERCU_ICONES = [
    ("places", "folder"), ("places", "user-home"), ("apps", "utilities-terminal"),
    ("apps", "firefox"), ("apps", "systemsettings"), ("apps", "plasmadiscover"),
]


def apercu_icones(theme: str, nombre: int = 5) -> list[str]:
    """Chemins de quelques icônes du thème pour l'aperçu (vide si absent)."""
    trouves: list[str] = []
    for base in dossiers_icones():
        racine = Path(base) / theme
        if not racine.is_dir():
            continue
        for ctx, nom in APERCU_ICONES:
            for motif in (f"scalable/{ctx}/{nom}.svg", f"{ctx}/scalable/{nom}.svg",
                          f"{ctx}/64/{nom}.svg", f"{ctx}/48/{nom}.svg"):
                p = racine / motif
                if p.exists():
                    trouves.append(str(p))
                    break
            if len(trouves) >= nombre:
                return trouves
        if trouves:
            break
    return trouves


def dossiers_fonds() -> list[str]:
    env = os.environ.get("EXOLYX_DOSSIER_FONDS")
    return [env] if env else ["/usr/share/wallpapers"]


def trouver_fond(sombre: bool) -> dict:
    """Fond d'écran ExoLyx : {"paquet": dossier à appliquer, "image": aperçu}."""
    noms = ["ExoLyx", "ExoLyx-Sombre"] if sombre else ["ExoLyx-Clair"]
    for base in dossiers_fonds():
        for nom in noms:
            d = Path(base) / nom
            images = sorted((d / "contents" / "images").glob("*.png")) + \
                sorted((d / "contents" / "images").glob("*.jpg"))
            if images:
                # aperçu : la plus petite résolution suffit
                def surface(p: Path) -> int:
                    m = re.match(r"(\d+)x(\d+)", p.stem)
                    return int(m.group(1)) * int(m.group(2)) if m else 1 << 30
                return {"paquet": str(d), "image": str(min(images, key=surface))}
    return {"paquet": "", "image": ""}


def commandes_apparence(sombre: bool, style: str, fond: bool = True) -> list[list[str]]:
    """Commandes (utilisateur, sans root) pour appliquer l'apparence choisie.

    L'ordre compte : le look-and-feel réinitialise couleurs et icônes."""
    cmds = [
        ["plasma-apply-lookandfeel", "-a", look_and_feel(sombre)],
        ["plasma-apply-colorscheme", schema_couleurs(sombre)],
    ]
    cmds += commandes_icones(style, sombre)
    if fond:
        f = trouver_fond(sombre)
        if f["paquet"]:
            cmds.append(["plasma-apply-wallpaperimage", f["paquet"]])
    return cmds


def commandes_icones(style: str, sombre: bool) -> list[list[str]]:
    theme = theme_icones(style, sombre)
    if os.path.exists("/usr/lib/plasma-changeicons"):
        return [["/usr/lib/plasma-changeicons", theme]]
    return [["kwriteconfig6", "--file", "kdeglobals", "--group", "Icons", "--key", "Theme", theme]]


# ---------------------------------------------------------------------------
# Détection du matériel
# ---------------------------------------------------------------------------
@dataclass
class CarteGraphique:
    fabricant: str          # "nvidia", "amd", "intel", "autre"
    nom: str
    id_peripherique: int    # identifiant PCI (ex. 0x1f08)

    @property
    def nvidia_open_compatible(self) -> bool:
        """nvidia-open exige une architecture Turing (GTX 16xx / RTX 20xx) ou plus récente.

        Heuristique : identifiants PCI Turing et suivants ≥ 0x1E00."""
        return self.fabricant == "nvidia" and self.id_peripherique >= 0x1E00


_RE_LSPCI = re.compile(
    r"^\S+\s+(?P<classe>[^\[]+?)\s*\[(?P<code>03[0-9a-f]{2})\]:\s*(?P<nom>.*?)\s*"
    r"\[(?P<vendeur>[0-9a-f]{4}):(?P<dev>[0-9a-f]{4})\]", re.I)
_FABRICANTS = {"10de": "nvidia", "1002": "amd", "8086": "intel"}


def analyser_lspci(sortie: str) -> list[CarteGraphique]:
    """Analyse la sortie de « lspci -nn » et renvoie les contrôleurs d'affichage."""
    cartes = []
    for ligne in sortie.splitlines():
        m = _RE_LSPCI.match(ligne.strip())
        if not m:
            continue
        nom = m.group("nom")
        # « NVIDIA Corporation TU106 [GeForce RTX 2060] » -> « GeForce RTX 2060 »
        crochets = re.findall(r"\[([^\]]+)\]", nom)
        lisible = crochets[-1] if crochets else nom
        cartes.append(CarteGraphique(
            fabricant=_FABRICANTS.get(m.group("vendeur").lower(), "autre"),
            nom=lisible.strip(),
            id_peripherique=int(m.group("dev"), 16)))
    return cartes


def executer(cmd: list[str], delai: float = 5) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=delai,
                              env={**os.environ, "LC_ALL": "C"}).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def detecter_cartes() -> list[CarteGraphique]:
    return analyser_lspci(executer(["lspci", "-nn"]))


def detecter_virtualisation() -> str:
    """« oracle » pour VirtualBox, « none » sur machine physique."""
    return executer(["systemd-detect-virt"]).strip() or "none"


@dataclass
class Pilote:
    id: str
    nom: str
    description: str
    paquets: list[str]
    recommande: bool = True


def pilotes_proposes(cartes: list[CarteGraphique], virt: str) -> tuple[list[Pilote], list[str]]:
    """Pilotes à proposer et remarques à afficher."""
    pilotes, remarques = [], []
    nvidia = [c for c in cartes if c.fabricant == "nvidia"]
    if nvidia:
        if any(c.nvidia_open_compatible for c in nvidia):
            noms = ", ".join(c.nom for c in nvidia)
            pilotes.append(Pilote(
                "nvidia", "Pilote NVIDIA",
                f"{noms} — pilote officiel (modules ouverts) pour les jeux et l'accélération 3D.",
                ["nvidia-open", "nvidia-utils", "nvidia-settings"]))
        else:
            remarques.append(
                f"Carte NVIDIA ancienne ({nvidia[0].nom}) : le pilote nvidia-open ne la prend pas "
                "en charge. Le pilote libre « nouveau » déjà inclus est conservé.")
    if virt == "oracle":
        pilotes.append(Pilote(
            "virtualbox", "Additions invité VirtualBox",
            "Presse-papiers partagé, redimensionnement automatique de l'écran et dossiers partagés.",
            ["virtualbox-guest-utils"]))
    elif virt not in ("none", ""):
        remarques.append(f"Machine virtuelle détectée ({virt}) : aucun pilote supplémentaire nécessaire.")
    return pilotes, remarques


# ---------------------------------------------------------------------------
# Catalogue d'applications (doit rester inclus dans la liste blanche du helper)
# ---------------------------------------------------------------------------
@dataclass
class Appli:
    id: str
    nom: str
    description: str
    source: str               # "pacman" ou "flatpak"
    paquets: list[str] = field(default_factory=list)
    couleur: str = "#A8D479"


CATALOGUE = [
    Appli("libreoffice", "LibreOffice", "Suite bureautique : textes, tableurs, présentations",
          "pacman", ["libreoffice-fresh", "libreoffice-fresh-fr"], "#79C2D4"),
    Appli("vlc", "VLC", "Lecteur multimédia universel", "pacman", ["vlc"], "#E8C26A"),
    Appli("gimp", "GIMP", "Retouche photo avancée", "pacman", ["gimp"], "#BDD479"),
    Appli("thunderbird", "Thunderbird", "Messagerie et agenda", "pacman",
          ["thunderbird", "thunderbird-i18n-fr"], "#79C2D4"),
    Appli("steam", "Steam", "Jeux vidéo", "flatpak", ["com.valvesoftware.Steam"], "#8DD479"),
    Appli("discord", "Discord", "Discussions vocales et textuelles", "flatpak",
          ["com.discordapp.Discord"], "#97A893"),
    Appli("spotify", "Spotify", "Musique en streaming", "flatpak", ["com.spotify.Client"], "#A8D479"),
    Appli("obs", "OBS Studio", "Enregistrement et diffusion d'écran", "pacman", ["obs-studio"], "#E5766B"),
    Appli("vscode", "Visual Studio Code", "Éditeur de code", "flatpak", ["com.visualstudio.code"], "#79C2D4"),
    Appli("kdenlive", "Kdenlive", "Montage vidéo", "pacman", ["kdenlive"], "#8DD479"),
    Appli("krita", "Krita", "Dessin et peinture numérique", "pacman", ["krita"], "#E8C26A"),
]


def appli(id_: str) -> Appli:
    for a in CATALOGUE:
        if a.id == id_:
            return a
    raise KeyError(id_)


def jetons_installation(ids_applis: list[str], paquets_pilotes: list[str] = ()) -> list[str]:
    """Arguments du helper : « pacman:<paquet> » et « flatpak:<id> »."""
    jetons: list[str] = []
    for p in paquets_pilotes:
        jetons.append(f"pacman:{p}")
    for i in ids_applis:
        a = appli(i)
        for p in a.paquets:
            jetons.append(f"{a.source}:{p}")
    # sans doublons, ordre conservé
    return list(dict.fromkeys(jetons))

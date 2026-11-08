# SPDX-License-Identifier: GPL-3.0-or-later
"""Logique pure des mises à jour ExoLyx (sans Qt, testable)."""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
HELPER = "/usr/lib/exolyx/exolyx-maj-helper"
ENV_C = {"LC_ALL": "C", "LANG": "C"}


@dataclass
class MiseAJour:
    nom: str
    ancienne: str
    nouvelle: str
    taille: int = 0          # octets à télécharger (0 = inconnu)
    source: str = "pacman"   # "pacman" ou "flatpak"
    redemarrage: bool = False


# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
def dossier_cache() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "exolyx"


def fichier_cache() -> Path:
    return dossier_cache() / "maj.json"


def chemin_logo() -> str:
    for p in (ICI / "images" / "logo.svg", ICI.parent / "branding" / "logo.svg"):
        if p.exists():
            return str(p)
    return ""


def mode_live() -> bool:
    force = os.environ.get("EXOLYX_LIVE")
    if force is not None:
        return force == "1"
    return os.path.isdir("/run/archiso")


# ---------------------------------------------------------------------------
# Redémarrage
# ---------------------------------------------------------------------------
RE_REDEMARRAGE = re.compile(
    r"^(linux(-lts|-zen|-hardened|-rt)?|systemd|systemd-libs|mesa|lib32-mesa|"
    r"nvidia[a-z0-9-]*|lib32-nvidia-utils|amd-ucode|intel-ucode)$")


def necessite_redemarrage(nom: str) -> bool:
    return bool(RE_REDEMARRAGE.match(nom))


def noyau_remplace(release: str | None = None, modules: str = "/usr/lib/modules") -> bool:
    """Vrai si les modules du noyau en cours ont disparu (noyau mis à jour)."""
    release = release or os.uname().release
    return not os.path.isdir(os.path.join(modules, release))


# ---------------------------------------------------------------------------
# Analyse des sorties
# ---------------------------------------------------------------------------
RE_CHECKUPDATES = re.compile(r"^(\S+)\s+(\S+)\s+->\s+(\S+)")


def analyser_checkupdates(sortie: str) -> list[MiseAJour]:
    """« nom ancienne -> nouvelle » par ligne (éventuellement suivi de [ignored])."""
    res = []
    for ligne in sortie.splitlines():
        m = RE_CHECKUPDATES.match(ligne.strip())
        if m and "[ignored]" not in ligne:
            nom = m.group(1)
            res.append(MiseAJour(nom, m.group(2), m.group(3), source="pacman",
                                 redemarrage=necessite_redemarrage(nom)))
    return res


_UNITES = {"B": 1, "KiB": 1024, "MiB": 1024 ** 2, "GiB": 1024 ** 3, "TiB": 1024 ** 4,
           "kB": 1000, "KB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3,
           "bytes": 1, "octets": 1}


def convertir_taille(texte: str) -> int:
    """« 12.50 MiB » / « 1,2 MB » / « 830 bytes » -> octets."""
    m = re.match(r"^\s*([\d.,\s  ]+)\s*([A-Za-z]+)", texte or "")
    if not m:
        return 0
    nombre = m.group(1).replace(" ", "").replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return int(float(nombre) * _UNITES.get(m.group(2), 0))
    except ValueError:
        return 0


def analyser_pacman_si(sortie: str) -> dict[str, int]:
    """Tailles de téléchargement par paquet depuis « LC_ALL=C pacman -Si »."""
    tailles, nom = {}, None
    for ligne in sortie.splitlines():
        if ":" not in ligne:
            continue
        cle, _, val = ligne.partition(":")
        cle, val = cle.strip(), val.strip()
        if cle == "Name":
            nom = val
        elif cle == "Download Size" and nom:
            tailles[nom] = convertir_taille(val)
    return tailles


def analyser_flatpak(sortie_maj: str, sortie_liste: str = "") -> list[MiseAJour]:
    """« flatpak remote-ls --updates --columns=application,version,branch,download-size »
    croisé avec « flatpak list --columns=application,version » (anciennes versions)."""
    anciennes = {}
    for ligne in sortie_liste.splitlines():
        champs = ligne.split("\t")
        if len(champs) >= 2 and champs[0]:
            anciennes[champs[0]] = champs[1]
    res = []
    for ligne in sortie_maj.splitlines():
        champs = ligne.split("\t")
        if not champs or not champs[0] or champs[0].lower() in ("application", "application id"):
            continue
        champs += [""] * (4 - len(champs))
        app, version, branche, taille = champs[:4]
        res.append(MiseAJour(app, anciennes.get(app, "") or "—",
                             version or branche or "—", convertir_taille(taille), "flatpak"))
    return res


def formater_taille(octets: int) -> str:
    if octets <= 0:
        return "—"
    for unite, f in (("Go", 1024 ** 3), ("Mo", 1024 ** 2), ("ko", 1024)):
        if octets >= f:
            return f"{octets / f:.1f} {unite}".replace(".", ",")
    return f"{octets} o"


# ---------------------------------------------------------------------------
# Vérification
# ---------------------------------------------------------------------------
def _executer(cmd: list[str], env_extra: dict | None = None, delai: int = 180):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=delai,
                           env={**os.environ, **ENV_C, **(env_extra or {})})
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return 127, ""


def verifier_pacman() -> tuple[list[MiseAJour], str]:
    """Renvoie (mises à jour, erreur). checkupdates : 0 = mises à jour, 2 = aucune."""
    db = dossier_cache() / "checkup-db"
    db.parent.mkdir(parents=True, exist_ok=True)
    code, sortie = _executer(["checkupdates", "--nocolor"], {"CHECKUPDATES_DB": str(db)})
    if code == 2:
        return [], ""
    if code != 0:
        return [], "Impossible de vérifier les mises à jour (réseau ?)."
    maj = analyser_checkupdates(sortie)
    if maj:
        _, si = _executer(["pacman", "-Si", "--dbpath", str(db), "--logfile", "/dev/null",
                           *[m.nom for m in maj]], delai=60)
        tailles = analyser_pacman_si(si)
        for m in maj:
            m.taille = tailles.get(m.nom, 0)
    return maj, ""


def verifier_flatpak() -> list[MiseAJour]:
    code, sortie = _executer(["flatpak", "remote-ls", "--updates",
                              "--columns=application,version,branch,download-size"])
    if code != 0 or not sortie.strip():
        return []
    _, liste = _executer(["flatpak", "list", "--columns=application,version"])
    return analyser_flatpak(sortie, liste)


def verifier() -> dict:
    pacman, erreur = verifier_pacman()
    flatpak = verifier_flatpak()
    return {"date": datetime.now().isoformat(timespec="seconds"),
            "pacman": [asdict(m) for m in pacman],
            "flatpak": [asdict(m) for m in flatpak],
            "erreur": erreur}


def ecrire_cache(resultat: dict, chemin: Path | None = None) -> None:
    chemin = chemin or fichier_cache()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(".tmp")
    tmp.write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, chemin)


def lire_cache(chemin: Path | None = None) -> dict:
    try:
        d = json.loads((chemin or fichier_cache()).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def nombre(resultat: dict) -> int:
    return len(resultat.get("pacman", [])) + len(resultat.get("flatpak", []))


# ---------------------------------------------------------------------------
# Progression de « pacman -Syu » (sortie non interactive, --noprogressbar)
# ---------------------------------------------------------------------------
RE_PAQUETS = re.compile(r"^Packages? \((\d+)\)")
RE_ETAPE = re.compile(r"^\(\s*(\d+)/(\d+)\)\s+(\S+)")
VERBES_TRANSACTION = ("upgrading", "installing", "reinstalling", "downgrading", "removing")


class ProgressionPacman:
    """Convertit les lignes de pacman en fraction 0..1 (monotone).

    Téléchargement 5 → 40 %, transaction 45 → 90 %, hooks 90 → 100 %."""

    def __init__(self):
        self.total = 0
        self.telecharges = 0
        self.phase = "sync"
        self.valeur = 0.0
        self.texte = "Synchronisation des dépôts…"

    def _fixer(self, v: float, texte: str | None = None):
        self.valeur = max(self.valeur, min(v, 1.0))
        if texte:
            self.texte = texte

    def lire(self, ligne: str) -> float:
        l = ligne.strip()
        if m := RE_PAQUETS.match(l):
            self.total = int(m.group(1))
        elif l.startswith(":: Retrieving packages"):
            self.phase = "telechargement"
            self._fixer(0.05, "Téléchargement des paquets…")
        elif l.startswith(":: Running pre-transaction hooks"):
            self.phase = "pre"
            self._fixer(0.42, "Instantané de sécurité (snapper)…")
        elif l.startswith(":: Processing package changes"):
            self.phase = "transaction"
            self._fixer(0.45, "Installation des mises à jour…")
        elif l.startswith(":: Running post-transaction hooks"):
            self.phase = "post"
            self._fixer(0.90, "Finalisation…")
        elif self.phase == "telechargement" and l.endswith("downloading..."):
            self.telecharges += 1
            if self.total:
                self._fixer(0.05 + 0.35 * min(self.telecharges / self.total, 1))
        elif m := RE_ETAPE.match(l):
            i, n, verbe = int(m.group(1)), int(m.group(2)), m.group(3)
            if self.phase == "transaction" and verbe in VERBES_TRANSACTION and n:
                nom = l.split()[-1]
                self._fixer(0.45 + 0.45 * i / n, f"Mise à jour de {nom} ({i}/{n})")
            elif self.phase == "post" and n:
                self._fixer(0.90 + 0.10 * i / n)
        elif l.startswith("there is nothing to do"):
            self._fixer(1.0, "Le système est déjà à jour.")
        return self.valeur

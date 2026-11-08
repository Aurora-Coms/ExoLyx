"""Configuration persistante (~/.config/exolyx/fichiers.json) et thème ExoLyx."""

import configparser
import json
import os

from PyQt6.QtCore import QObject, QStandardPaths, pyqtProperty, pyqtSignal, pyqtSlot

# Palette officielle (src/branding/palette.md) : jeton -> (sombre, clair)
PALETTE = {
    "accent": ("#A8D479", "#5E9B2E"),
    "accentClair": ("#BDD479", "#7DB547"),
    "accentFroid": ("#8DD479", "#4E8F3A"),
    "fond": ("#0D1310", "#F4F8F1"),
    "surface": ("#141C17", "#FFFFFF"),
    "surfaceHaute": ("#1C2620", "#E9F0E4"),
    "bordure": ("#2A362E", "#D3DECB"),
    "texte": ("#E6EFE1", "#16201A"),
    "texteDoux": ("#97A893", "#5B6B57"),
    "erreur": ("#E5766B", "#C2453A"),
    "attention": ("#E8C26A", "#A87A12"),
    "info": ("#79C2D4", "#2F7F94"),
}

# Texte posé sur l'accent (contraste suffisant dans les deux thèmes)
SUR_ACCENT = ("#0D1310", "#FFFFFF")

PAR_DEFAUT = {
    "epingles": None,          # None = initialiser avec les dossiers XDG
    "vue": "grille",           # grille | liste
    "tri": "nom",              # nom | date | taille | type
    "triDecroissant": False,
    "caches": False,
    "theme": "auto",           # auto | sombre | clair
    "apercu": False,
    "confirmerCorbeille": False,
    "couleursEtiquettes": {},
    "tailleIcones": 112,
}


def dossier_config():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "exolyx")


def chemin_config():
    return os.path.join(dossier_config(), "fichiers.json")


def dossiers_xdg():
    """Dossiers utilisateur standard existants : liste de (clé, chemin)."""
    emplacements = [
        ("bureau", QStandardPaths.StandardLocation.DesktopLocation),
        ("documents", QStandardPaths.StandardLocation.DocumentsLocation),
        ("telechargements", QStandardPaths.StandardLocation.DownloadLocation),
        ("images", QStandardPaths.StandardLocation.PicturesLocation),
        ("musique", QStandardPaths.StandardLocation.MusicLocation),
        ("videos", QStandardPaths.StandardLocation.MoviesLocation),
    ]
    maison = os.path.expanduser("~")
    resultat = []
    for cle, emp in emplacements:
        chemin = QStandardPaths.writableLocation(emp)
        if chemin and os.path.isdir(chemin) and os.path.realpath(chemin) != os.path.realpath(maison):
            resultat.append((cle, chemin))
    return resultat


def theme_systeme_clair(chemin_kdeglobals=None):
    """Lit ~/.config/kdeglobals : un ColorScheme contenant « Clair » = thème clair."""
    chemin = chemin_kdeglobals or os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "kdeglobals")
    analyseur = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        analyseur.read(chemin, encoding="utf-8")
        schema = analyseur.get("General", "ColorScheme", fallback="")
    except (configparser.Error, OSError, UnicodeDecodeError):
        return False
    return "clair" in schema.lower()


class Config:
    def __init__(self, chemin=None):
        self.chemin = chemin or chemin_config()
        self.donnees = dict(PAR_DEFAUT)
        try:
            with open(self.chemin, encoding="utf-8") as f:
                lu = json.load(f)
            if isinstance(lu, dict):
                self.donnees.update(lu)
        except (OSError, ValueError):
            pass
        if self.donnees.get("epingles") is None:
            self.donnees["epingles"] = [c for _, c in dossiers_xdg()]

    def get(self, cle):
        return self.donnees.get(cle, PAR_DEFAUT.get(cle))

    def set(self, cle, valeur):
        self.donnees[cle] = valeur
        self.sauver()

    def sauver(self):
        os.makedirs(os.path.dirname(self.chemin), exist_ok=True)
        temporaire = self.chemin + ".tmp"
        with open(temporaire, "w", encoding="utf-8") as f:
            json.dump(self.donnees, f, ensure_ascii=False, indent=2)
        os.replace(temporaire, self.chemin)


class Theme(QObject):
    """Couleurs exposées au QML ; changent en direct quand le mode change."""

    change = pyqtSignal()

    def __init__(self, mode="auto", parent=None):
        super().__init__(parent)
        self._mode = mode
        self._clair = self._calculer_clair()

    def _calculer_clair(self):
        if self._mode == "clair":
            return True
        if self._mode == "sombre":
            return False
        return theme_systeme_clair()

    def definir_mode(self, mode):
        self._mode = mode
        clair = self._calculer_clair()
        if clair != self._clair:
            self._clair = clair
            self.change.emit()

    def couleur(self, jeton):
        return PALETTE[jeton][1 if self._clair else 0]

    @pyqtProperty(bool, notify=change)
    def clair(self):
        return self._clair

    @pyqtProperty(str, notify=change)
    def surAccent(self):
        return SUR_ACCENT[1 if self._clair else 0]

    @pyqtSlot(str, result=str)
    def jeton(self, nom):
        return self.couleur(nom)

    # Une propriété par jeton de la palette
    def _fabrique(nom, signal):
        return pyqtProperty(str, lambda self: self.couleur(nom), notify=signal)

    for _nom in PALETTE:
        locals()[_nom] = _fabrique(_nom, change)
    del _nom, _fabrique

"""Étiquettes de fichiers, stockées dans l'attribut étendu « user.xdg.tags »
(liste séparée par des virgules, convention freedesktop partagée avec Baloo/Dolphin)."""

import json
import os
import threading
import zlib

ATTRIBUT = "user.xdg.tags"

# Couleurs proposées (jetons de la palette), attribuées par défaut selon le nom
COULEURS = ["accent", "info", "attention", "erreur", "accentFroid", "accentClair"]

DOSSIERS_EXCLUS = {"node_modules", "__pycache__", ".git", ".cache", ".local", ".var", ".mozilla"}


def lire(chemin):
    try:
        brut = os.getxattr(chemin, ATTRIBUT, follow_symlinks=False)
    except OSError:
        return []
    texte = brut.decode("utf-8", "replace").strip("\x00")
    vus = []
    for e in texte.split(","):
        e = e.strip()
        if e and e not in vus:
            vus.append(e)
    return vus


def ecrire(chemin, liste):
    """Écrit les étiquettes ; liste vide = suppression de l'attribut. Lève OSError si
    le système de fichiers ne gère pas les attributs étendus."""
    propre = []
    for e in liste:
        e = e.replace(",", " ").strip()
        if e and e not in propre:
            propre.append(e)
    if propre:
        os.setxattr(chemin, ATTRIBUT, ",".join(propre).encode("utf-8"), follow_symlinks=False)
    else:
        try:
            os.removexattr(chemin, ATTRIBUT, follow_symlinks=False)
        except OSError:
            pass
    return propre


def ajouter(chemin, etiquette):
    return ecrire(chemin, lire(chemin) + [etiquette])


def retirer(chemin, etiquette):
    return ecrire(chemin, [e for e in lire(chemin) if e != etiquette])


def couleur_par_defaut(nom):
    return COULEURS[zlib.crc32(nom.encode("utf-8")) % len(COULEURS)]


def parcourir(racine, annule=None, profondeur_max=12, caches=False):
    """Générateur (chemin, étiquettes) des éléments étiquetés sous « racine »."""
    pile = [(racine, 0)]
    while pile:
        if annule is not None and annule.is_set():
            return
        dossier, prof = pile.pop()
        try:
            it = os.scandir(dossier)
        except OSError:
            continue
        with it:
            for e in it:
                if not caches and e.name.startswith("."):
                    continue
                etq = lire(e.path)
                if etq:
                    yield e.path, etq
                try:
                    if e.is_dir(follow_symlinks=False) and prof < profondeur_max and e.name not in DOSSIERS_EXCLUS:
                        pile.append((e.path, prof + 1))
                except OSError:
                    pass


# ---------------------------------------------------------------------------
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal  # noqa: E402


def chemin_cache():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "exolyx", "etiquettes.json")


class IndexEtiquettes(QObject):
    """Index étiquette -> chemins, construit en tâche de fond depuis le dossier personnel."""

    change = pyqtSignal()
    _finInterne = pyqtSignal(dict)

    def __init__(self, racine=None, parent=None):
        super().__init__(parent)
        self.racine = racine or os.path.expanduser("~")
        self._index = {}       # chemin -> [étiquettes]
        self._annule = threading.Event()
        self._enCours = False
        self._finInterne.connect(self._surFin)
        try:
            with open(chemin_cache(), encoding="utf-8") as f:
                lu = json.load(f)
            self._index = {c: e for c, e in lu.items() if isinstance(e, list) and os.path.lexists(c)}
        except (OSError, ValueError, AttributeError):
            pass

    def demarrer(self):
        if self._enCours:
            return
        self._enCours = True
        self._annule.clear()

        def travail():
            trouve = dict(parcourir(self.racine, self._annule))
            if not self._annule.is_set():
                self._finInterne.emit(trouve)

        threading.Thread(target=travail, daemon=True, name="index-etiquettes").start()

    def arreter(self):
        self._annule.set()

    def _surFin(self, trouve):
        self._enCours = False
        # Les chemins hors racine (autres lecteurs) déjà connus sont conservés s'ils existent
        for c, e in self._index.items():
            if not c.startswith(self.racine + os.sep) and c not in trouve and os.path.lexists(c):
                trouve[c] = lire(c) or e
        self._index = trouve
        self._sauver()
        self.change.emit()

    def _sauver(self):
        try:
            os.makedirs(os.path.dirname(chemin_cache()), exist_ok=True)
            with open(chemin_cache(), "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False)
        except OSError:
            pass

    def mettre_a_jour(self, chemin, liste):
        """Appelé quand l'appli modifie les étiquettes d'un fichier (ou le déplace)."""
        if liste:
            self._index[chemin] = list(liste)
        else:
            self._index.pop(chemin, None)
        self._sauver()
        self.change.emit()

    def renommer(self, ancien, nouveau):
        changes = False
        for c in list(self._index):
            if c == ancien or c.startswith(ancien + os.sep):
                self._index[nouveau + c[len(ancien):]] = self._index.pop(c)
                changes = True
        if changes:
            self._sauver()
            self.change.emit()

    def oublier(self, chemin):
        changes = False
        for c in list(self._index):
            if c == chemin or c.startswith(chemin + os.sep):
                del self._index[c]
                changes = True
        if changes:
            self._sauver()
            self.change.emit()

    def toutes(self):
        """Étiquettes connues avec leur nombre d'éléments, triées par nom."""
        compte = {}
        for e in self._index.values():
            for t in e:
                compte[t] = compte.get(t, 0) + 1
        return sorted(compte.items(), key=lambda x: x[0].lower())

    def fichiers(self, etiquette):
        return sorted(c for c, e in self._index.items() if etiquette in e and os.path.lexists(c))

    @pyqtProperty(bool, notify=change)
    def enCours(self):
        return self._enCours

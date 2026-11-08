"""Modèle de liste des éléments d'un dossier (ou d'une liste de résultats) pour le QML."""

import functools
import os
import stat
import time
from datetime import datetime

from PyQt6.QtCore import (QAbstractListModel, QCollator, QFileSystemWatcher, QMimeDatabase,
                          QModelIndex, Qt, QTimer, pyqtProperty, pyqtSignal, pyqtSlot)

import etiquettes

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
UNITES = ["o", "Ko", "Mo", "Go", "To", "Po"]


def format_taille(octets):
    octets = float(octets or 0)
    i = 0
    while octets >= 1024 and i < len(UNITES) - 1:
        octets /= 1024
        i += 1
    if i == 0:
        return f"{int(octets)}\u00a0o"
    texte = f"{octets:.1f}" if octets < 100 else f"{octets:.0f}"
    if texte.endswith(".0"):
        texte = texte[:-2]
    return texte.replace(".", ",") + "\u00a0" + UNITES[i]


def format_date(horodatage, maintenant=None):
    if not horodatage:
        return ""
    d = datetime.fromtimestamp(horodatage)
    m = datetime.fromtimestamp(maintenant) if maintenant else datetime.now()
    jours = (m.date() - d.date()).days
    heure = d.strftime("%H:%M")
    if jours == 0:
        return f"Aujourd’hui, {heure}"
    if jours == 1:
        return f"Hier, {heure}"
    if d.year == m.year:
        return f"{d.day} {MOIS[d.month - 1]}, {heure}"
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


CATEGORIES = {
    "dossier": "Dossier",
    "image": "Image",
    "video": "Vidéo",
    "audio": "Audio",
    "pdf": "Document PDF",
    "archive": "Archive",
    "code": "Code source",
    "texte": "Texte",
    "document": "Document",
    "tableur": "Classeur",
    "presentation": "Présentation",
    "executable": "Programme",
    "disque": "Image disque",
    "lien": "Lien",
    "fichier": "Fichier",
}

_ARCHIVES = ("zip", "x-tar", "gzip", "x-7z", "x-rar", "vnd.rar", "zstd", "x-xz", "x-bzip", "x-compressed-tar",
             "x-bzip2-compressed-tar", "x-xz-compressed-tar", "x-zstd-compressed-tar", "x-lzma", "x-archive",
             "x-cpio", "vnd.debian.binary-package", "x-rpm", "x-alpm-package", "x-bzip2", "x-lz4")
_CODE = ("x-shellscript", "json", "xml", "javascript", "x-python", "x-perl", "x-ruby", "x-php", "sql",
         "x-yaml", "toml", "x-desktop", "x-qml", "x-ipynb+json")


def categorie_mime(mime):
    if mime == "inode/directory":
        return "dossier"
    principal, _, sous = mime.partition("/")
    if principal == "image":
        return "image"
    if principal == "video":
        return "video"
    if principal == "audio":
        return "audio"
    if mime == "application/pdf":
        return "pdf"
    if principal == "application" and sous in _ARCHIVES:
        return "archive"
    if mime in ("application/x-cd-image", "application/x-raw-disk-image", "application/x-iso9660-image",
                "application/vnd.efi.iso", "application/vnd.efi.img", "application/x-qemu-disk"):
        return "disque"
    if "spreadsheet" in sous or "ms-excel" in sous or sous == "csv" or mime == "text/csv":
        return "tableur"
    if "presentation" in sous or "powerpoint" in sous:
        return "presentation"
    if "opendocument.text" in sous or "msword" in sous or "wordprocessing" in sous or sous == "rtf":
        return "document"
    if principal == "text" and (sous.startswith("x-") or sous in ("css", "html", "javascript", "markdown")):
        return "code"
    if principal == "application" and sous in _CODE:
        return "code"
    if principal == "text":
        return "texte"
    if sous in ("x-executable", "x-sharedlib", "x-pie-executable", "x-appimage", "vnd.appimage"):
        return "executable"
    return "fichier"


class Classifieur:
    """Mime, catégorie et libellé de type pour un nom de fichier (par extension, rapide)."""

    def __init__(self):
        self.base = QMimeDatabase()
        self._cache = {}

    def classer(self, nom, est_dossier, est_lien=False):
        if est_dossier:
            return "inode/directory", "dossier", "Dossier"
        ext = os.path.splitext(nom)[1].lower()
        cle = ext or nom
        if cle not in self._cache:
            mime = self.base.mimeTypeForFile(nom, QMimeDatabase.MatchMode.MatchExtension).name()
            cat = categorie_mime(mime)
            if cat == "fichier" and not ext:
                libelle = "Fichier"
            else:
                libelle = CATEGORIES[cat] + (f" {ext[1:].upper()}" if ext and cat not in ("pdf",) else "")
            self._cache[cle] = (mime, cat, libelle)
        return self._cache[cle]


CLASSIFIEUR = None


def classifieur():
    global CLASSIFIEUR
    if CLASSIFIEUR is None:
        CLASSIFIEUR = Classifieur()
    return CLASSIFIEUR


def entree_pour(chemin, nom=None):
    """Dict décrivant un élément du système de fichiers (None s'il a disparu)."""
    try:
        st = os.lstat(chemin)
    except OSError:
        return None
    lien = stat.S_ISLNK(st.st_mode)
    cible = st
    if lien:
        try:
            cible = os.stat(chemin)
        except OSError:
            pass
    dossier = stat.S_ISDIR(cible.st_mode)
    nom = nom or os.path.basename(chemin) or chemin
    mime, cat, libelle = classifieur().classer(nom, dossier, lien)
    if not dossier and cible.st_mode & 0o111 and cat == "fichier":
        cat, libelle = "executable", "Programme"
    import apercu
    return {
        "nom": nom,
        "chemin": chemin,
        "dossier": dossier,
        "lien": lien,
        "taille": 0 if dossier else cible.st_size,
        "date": cible.st_mtime,
        "mime": mime,
        "categorie": cat,
        "type": libelle,
        "cache": nom.startswith("."),
        "etiquettes": etiquettes.lire(chemin),
        "miniature": (not dossier) and apercu.peut_miniaturiser(cat, nom, cible.st_size),
        "origine": "",
        "dateSuppression": 0.0,
    }


class ModeleDossier(QAbstractListModel):
    NOMS = ["nom", "chemin", "dossier", "lien", "taille", "tailleTexte", "date", "dateTexte", "type",
            "categorie", "mime", "cache", "etiquettes", "miniature", "selectionne", "origine",
            "dateSuppressionTexte", "dossierParent"]
    ROLES = {Qt.ItemDataRole.UserRole + i + 1: n.encode() for i, n in enumerate(NOMS)}
    _ROLE_PAR_NOM = {v.decode(): k for k, v in ROLES.items()}

    countChange = pyqtSignal()
    selectionChange = pyqtSignal()
    triChange = pyqtSignal()
    recharge = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entrees = []
        self._selection = set()
        self._ancre = -1
        self._courant = -1
        self._tri = "nom"
        self._decroissant = False
        self._caches = False
        self._dossier = ""
        self.collateur = QCollator()
        self.collateur.setNumericMode(True)
        self.collateur.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.surveillant = QFileSystemWatcher(self)
        self.surveillant.directoryChanged.connect(lambda _: self._minuterie.start())
        self._minuterie = QTimer(self, singleShot=True, interval=250)
        self._minuterie.timeout.connect(self.rafraichir)

    # --- Qt ---
    def roleNames(self):
        return self.ROLES

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._entrees)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._entrees):
            return None
        e = self._entrees[index.row()]
        nom = self.ROLES.get(role, b"").decode()
        if nom == "tailleTexte":
            if e["dossier"]:
                return ""
            return format_taille(e["taille"])
        if nom == "dateTexte":
            return format_date(e["date"])
        if nom == "dateSuppressionTexte":
            return format_date(e["dateSuppression"])
        if nom == "selectionne":
            return e["chemin"] in self._selection
        if nom == "dossierParent":
            return os.path.dirname(e["chemin"])
        return e.get(nom)

    @pyqtProperty(int, notify=countChange)
    def count(self):
        return len(self._entrees)

    # --- chargement ---
    @pyqtProperty(str, notify=recharge)
    def dossier(self):
        return self._dossier

    def _surveiller(self, chemin):
        if self.surveillant.directories():
            self.surveillant.removePaths(self.surveillant.directories())
        if chemin:
            self.surveillant.addPath(chemin)

    def charger(self, chemin, caches=None):
        """Charge le contenu d'un dossier. Lève OSError si illisible."""
        if caches is not None:
            self._caches = caches
        noms = os.listdir(chemin)
        entrees = []
        for n in noms:
            if n.startswith(".") and not self._caches:
                continue
            e = entree_pour(os.path.join(chemin, n), n)
            if e:
                entrees.append(e)
        garder = self._selection if chemin == self._dossier else set()
        self._dossier = chemin
        self._surveiller(chemin)
        self._remplacer(entrees, garder)

    def definir_entrees(self, entrees):
        """Liste arbitraire (recherche, étiquette, corbeille) : pas de surveillance."""
        self._dossier = ""
        self._surveiller("")
        self._remplacer(entrees, set())

    def ajouter_entrees(self, entrees):
        if not entrees:
            return
        debut = len(self._entrees)
        self.beginInsertRows(QModelIndex(), debut, debut + len(entrees) - 1)
        self._entrees.extend(entrees)
        self.endInsertRows()
        self.countChange.emit()
        self.selectionChange.emit()   # le résumé (« n éléments ») dépend du nombre

    def _remplacer(self, entrees, selection):
        self.beginResetModel()
        self._entrees = entrees
        self._trier()
        chemins = {e["chemin"] for e in entrees}
        self._selection = {c for c in selection if c in chemins}
        self._ancre = -1
        self.endResetModel()
        self.countChange.emit()
        self.selectionChange.emit()
        self.recharge.emit()

    @pyqtSlot()
    def rafraichir(self):
        if self._dossier:
            try:
                self.charger(self._dossier)
            except OSError:
                pass
        else:
            entrees = [entree_pour(e["chemin"]) or None for e in self._entrees]
            garder = []
            for ancienne, nouvelle in zip(self._entrees, entrees):
                if nouvelle:
                    nouvelle["origine"] = ancienne["origine"]
                    nouvelle["dateSuppression"] = ancienne["dateSuppression"]
                    if ancienne["origine"]:
                        nouvelle["nom"] = ancienne["nom"]
                    garder.append(nouvelle)
            self._remplacer(garder, set(self._selection))

    def maj_etiquettes(self, chemin):
        for i, e in enumerate(self._entrees):
            if e["chemin"] == chemin:
                e["etiquettes"] = etiquettes.lire(chemin)
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [self._ROLE_PAR_NOM["etiquettes"]])

    # --- tri ---
    def _cle_nom(self):
        return functools.cmp_to_key(lambda a, b: self.collateur.compare(a["nom"], b["nom"]))

    def _trier(self):
        cle_nom = self._cle_nom()
        if self._tri == "date":
            cle = lambda e: e["date"]  # noqa: E731
        elif self._tri == "taille":
            cle = lambda e: e["taille"]  # noqa: E731
        elif self._tri == "type":
            cle = lambda e: e["type"].casefold()  # noqa: E731
        else:
            cle = None
        # tri stable : d'abord par nom, puis par la clé choisie
        self._entrees.sort(key=cle_nom, reverse=self._decroissant and cle is None)
        if cle is not None:
            self._entrees.sort(key=cle, reverse=self._decroissant)
        # dossiers toujours en tête
        self._entrees.sort(key=lambda e: not e["dossier"])

    def definir_tri(self, tri, decroissant):
        self._tri = tri
        self._decroissant = decroissant
        self.beginResetModel()
        self._trier()
        self.endResetModel()
        self.triChange.emit()

    # --- sélection ---
    def _notifier_selection(self, lignes=None):
        role = [self._ROLE_PAR_NOM["selectionne"]]
        if lignes is None or len(lignes) > 50:
            if self._entrees:
                self.dataChanged.emit(self.index(0), self.index(len(self._entrees) - 1), role)
        else:
            for i in lignes:
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, role)
        self.selectionChange.emit()

    @pyqtSlot(int, str)
    def selectionner(self, ligne, mode="seul"):
        """mode : seul | basculer (Ctrl) | etendre (Maj) | ajouter."""
        if not 0 <= ligne < len(self._entrees):
            return
        chemin = self._entrees[ligne]["chemin"]
        if mode == "basculer":
            self._selection.symmetric_difference_update({chemin})
            self._ancre = ligne
        elif mode == "etendre" and self._ancre >= 0:
            a, b = sorted((self._ancre, ligne))
            self._selection = {self._entrees[i]["chemin"] for i in range(a, b + 1)}
        elif mode == "ajouter":
            self._selection.add(chemin)
        else:
            self._selection = {chemin}
            self._ancre = ligne
        self._courant = ligne
        self._notifier_selection()

    @pyqtSlot(list, bool)
    def selectionnerLignes(self, lignes, ajouter):
        nouvelles = {self._entrees[i]["chemin"] for i in lignes if 0 <= i < len(self._entrees)}
        if ajouter:
            nouvelles |= self._selection
        if nouvelles != self._selection:
            self._selection = nouvelles
            self._notifier_selection()

    @pyqtSlot()
    def toutSelectionner(self):
        self._selection = {e["chemin"] for e in self._entrees}
        self._notifier_selection()

    @pyqtSlot()
    def viderSelection(self):
        if self._selection:
            self._selection = set()
            self._notifier_selection()

    def selectionner_chemins(self, chemins):
        presents = {e["chemin"] for e in self._entrees}
        self._selection = {c for c in chemins if c in presents}
        lignes = [i for i, e in enumerate(self._entrees) if e["chemin"] in self._selection]
        if lignes:
            self._ancre = self._courant = lignes[0]
        self._notifier_selection()

    def selection(self):
        """Chemins sélectionnés, dans l'ordre d'affichage."""
        return [e["chemin"] for e in self._entrees if e["chemin"] in self._selection]

    def entrees_selectionnees(self):
        return [e for e in self._entrees if e["chemin"] in self._selection]

    @pyqtProperty(int, notify=selectionChange)
    def nbSelection(self):
        return len(self._selection)

    @pyqtProperty(int, notify=selectionChange)
    def ligneCourante(self):
        return self._courant if self._selection else -1

    @pyqtProperty(str, notify=selectionChange)
    def resumeSelection(self):
        sel = self.entrees_selectionnees()
        if not sel:
            n = len(self._entrees)
            return f"{n} élément{'s' if n > 1 else ''}"
        if len(sel) == 1:
            e = sel[0]
            return e["nom"] + ("" if e["dossier"] else f" — {format_taille(e['taille'])}")
        taille = sum(e["taille"] for e in sel)
        return f"{len(sel)} éléments sélectionnés — {format_taille(taille)}"

    @pyqtSlot(str, result=int)
    def ligneDe(self, chemin):
        for i, e in enumerate(self._entrees):
            if e["chemin"] == chemin:
                return i
        return -1

    @pyqtSlot(int, result="QVariant")
    def entree(self, ligne):
        if 0 <= ligne < len(self._entrees):
            e = dict(self._entrees[ligne])
            e["tailleTexte"] = "" if e["dossier"] else format_taille(e["taille"])
            e["dateTexte"] = format_date(e["date"])
            return e
        return None

    @pyqtSlot(result="QVariant")
    def premiereSelectionnee(self):
        for i, e in enumerate(self._entrees):
            if e["chemin"] in self._selection:
                return self.entree(i)
        return None

    @pyqtSlot(str, result=int)
    def ligneParPrefixe(self, prefixe):
        """Saut au clavier : premier élément dont le nom commence par « prefixe »."""
        p = prefixe.casefold()
        depart = self._courant + 1 if len(prefixe) == 1 else max(self._courant, 0)
        n = len(self._entrees)
        for k in range(n):
            i = (depart + k) % n
            if self._entrees[i]["nom"].casefold().startswith(p):
                return i
        return -1

    def entrees(self):
        return self._entrees


def maintenant():
    return time.time()

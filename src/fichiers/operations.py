"""Opérations longues sur les fichiers : copie, déplacement, suppression, corbeille.

Le moteur (classe Tache) est indépendant de Qt pour être testable ; il tourne dans
un thread et rend compte via des fonctions de rappel. GestionnaireOperations fait
le lien avec l'interface (liste des tâches, progression, conflits).
"""

import errno
import os
import shutil
import stat
import threading
import time

# Politiques de conflit
DEMANDER = "demander"
REMPLACER = "remplacer"
IGNORER = "ignorer"
RENOMMER = "renommer"

TAILLE_BLOC = 1024 * 1024

# Extensions doubles conservées entières par nom_unique
EXTENSIONS_DOUBLES = (".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst", ".tar.lz", ".tar.lzma")


class OperationAnnulee(Exception):
    pass


def separer_extension(nom):
    """Sépare « archive.tar.gz » en (« archive », « .tar.gz »). Un nom caché sans
    autre point (« .bashrc ») n'a pas d'extension."""
    bas = nom.lower()
    for ext in EXTENSIONS_DOUBLES:
        if bas.endswith(ext) and len(nom) > len(ext):
            return nom[: -len(ext)], nom[-len(ext):]
    base, ext = os.path.splitext(nom)
    if not base:
        return nom, ""
    return base, ext


def nom_unique(dossier, nom, est_libre=None):
    """Renvoie un nom libre dans « dossier » : « nom.ext », sinon « nom (2).ext »…
    Un nom déjà numéroté « nom (3).ext » continue la numérotation."""
    est_libre = est_libre or (lambda n: not os.path.lexists(os.path.join(dossier, n)))
    if est_libre(nom):
        return nom
    base, ext = separer_extension(nom)
    n = 2
    if base.endswith(")") and " (" in base:
        racine, _, num = base[:-1].rpartition(" (")
        if num.isdigit():
            base, n = racine, int(num) + 1
    while True:
        candidat = f"{base} ({n}){ext}"
        if est_libre(candidat):
            return candidat
        n += 1


def meme_systeme(a, b):
    """Vrai si les deux chemins sont sur le même système de fichiers."""
    try:
        da = os.lstat(a).st_dev
        cible = b
        while not os.path.exists(cible):
            parent = os.path.dirname(cible)
            if parent == cible:
                break
            cible = parent
        return da == os.stat(cible).st_dev
    except OSError:
        return False


def est_dans(chemin, dossier):
    """Vrai si « chemin » est « dossier » ou se trouve dedans."""
    c = os.path.realpath(chemin)
    d = os.path.realpath(dossier)
    return c == d or c.startswith(d.rstrip(os.sep) + os.sep)


def mesurer(chemins, annule=None):
    """(octets, nombre d'éléments) des chemins, liens non suivis."""
    octets = 0
    nombre = 0
    pile = list(chemins)
    while pile:
        if annule is not None and annule.is_set():
            raise OperationAnnulee()
        p = pile.pop()
        try:
            st = os.lstat(p)
        except OSError:
            continue
        nombre += 1
        if stat.S_ISDIR(st.st_mode):
            try:
                with os.scandir(p) as it:
                    pile.extend(e.path for e in it)
            except OSError:
                pass
        elif stat.S_ISREG(st.st_mode):
            octets += st.st_size
    return octets, nombre


def copier_xattrs(src, dst):
    """Copie les attributs étendus user.* (dont les étiquettes)."""
    try:
        noms = os.listxattr(src, follow_symlinks=False)
    except OSError:
        return
    for nom in noms:
        if not nom.startswith("user."):
            continue
        try:
            os.setxattr(dst, nom, os.getxattr(src, nom, follow_symlinks=False), follow_symlinks=False)
        except OSError:
            pass


class Tache:
    """Une opération : type in {copier, deplacer, supprimer, corbeille}.

    Rappels (facultatifs, appelés depuis le thread de travail) :
      progression(octets_faits, octets_total, fichier_courant)
      conflit(source, destination) -> (choix, pour_tous)  [bloquant]
      erreur(chemin, message)
    """

    def __init__(self, type_, sources, destination=None, politique=DEMANDER,
                 progression=None, conflit=None, erreur=None, corbeille=None):
        self.type = type_
        self.sources = [os.path.abspath(s) for s in sources]
        self.destination = os.path.abspath(destination) if destination else None
        self.politique = politique
        self.rappel_progression = progression
        self.rappel_conflit = conflit
        self.rappel_erreur = erreur
        self.corbeille = corbeille
        self.annule = threading.Event()
        self.total = 0
        self.fait = 0
        self.courant = ""
        self.erreurs = []
        self.resultats = []      # chemins créés (destinations effectives)
        self._dernier_signal = 0.0

    # --- utilitaires internes ---
    def annuler(self):
        self.annule.set()

    def _verifier(self):
        if self.annule.is_set():
            raise OperationAnnulee()

    def _progres(self, force=False):
        maintenant = time.monotonic()
        if self.rappel_progression and (force or maintenant - self._dernier_signal > 0.08):
            self._dernier_signal = maintenant
            self.rappel_progression(self.fait, self.total, self.courant)

    def _erreur(self, chemin, exc):
        message = exc.strerror if isinstance(exc, OSError) and exc.strerror else str(exc)
        self.erreurs.append((chemin, message))
        if self.rappel_erreur:
            self.rappel_erreur(chemin, message)

    def _resoudre_conflit(self, src, dst):
        """Renvoie le chemin de destination à utiliser, ou None pour ignorer."""
        choix = self.politique
        if choix == DEMANDER:
            if self.rappel_conflit is None:
                choix = RENOMMER
            else:
                choix, pour_tous = self.rappel_conflit(src, dst)
                if choix == "annuler":
                    raise OperationAnnulee()
                if pour_tous:
                    self.politique = choix
        if choix == IGNORER:
            return None
        if choix == RENOMMER:
            return os.path.join(os.path.dirname(dst), nom_unique(os.path.dirname(dst), os.path.basename(dst)))
        return dst  # REMPLACER

    # --- exécution ---
    def executer(self):
        try:
            if self.type in ("copier", "deplacer"):
                self._transferer()
            elif self.type == "supprimer":
                self._supprimer_tout()
            elif self.type == "corbeille":
                self._vers_corbeille()
            else:
                raise ValueError(self.type)
        except OperationAnnulee:
            self._progres(force=True)
            return False
        self.fait = max(self.fait, self.total)
        self._progres(force=True)
        return True

    def _transferer(self):
        dest = self.destination
        sources = []
        for s in self.sources:
            if os.path.isdir(s) and not os.path.islink(s) and est_dans(dest, s):
                self._erreur(s, OSError(errno.EINVAL, "Impossible de copier un dossier dans lui-même"))
                continue
            sources.append(s)
        # Les déplacements sur le même système sont des renommages : pas d'octets à compter
        a_copier = [s for s in sources if not (self.type == "deplacer" and meme_systeme(s, dest))]
        self.total = mesurer(a_copier, self.annule)[0]
        self._progres(force=True)
        for s in sources:
            self._verifier()
            cible = os.path.join(dest, os.path.basename(s.rstrip(os.sep)))
            if self.type == "deplacer" and os.path.dirname(s) == dest:
                continue  # déjà là
            if os.path.lexists(cible):
                if os.path.realpath(cible) == os.path.realpath(s):
                    if self.type == "deplacer":
                        continue
                    cible = os.path.join(dest, nom_unique(dest, os.path.basename(cible)))
                else:
                    cible = self._resoudre_conflit(s, cible)
                    if cible is None:
                        if s in a_copier:
                            self._sauter(s)
                        continue
            try:
                if self.type == "deplacer":
                    self._deplacer(s, cible)
                else:
                    self._copier(s, cible)
                self.resultats.append(cible)
            except OperationAnnulee:
                raise
            except OSError as e:
                self._erreur(s, e)

    def _deplacer(self, src, dst):
        self._verifier()
        self.courant = src
        meme = meme_systeme(src, os.path.dirname(dst))
        src_dossier = os.path.isdir(src) and not os.path.islink(src)
        if os.path.lexists(dst):
            if src_dossier and os.path.isdir(dst) and not os.path.islink(dst):
                self._deplacer_contenu(src, dst)
                return
            self._supprimer(dst)
        if meme:
            os.rename(src, dst)
            self._progres()
        elif src_dossier:
            # autre système de fichiers : dossier recréé puis vidé élément par élément,
            # pour ne jamais supprimer ce qui a été ignoré
            os.makedirs(dst)
            self._deplacer_contenu(src, dst)
        else:
            self._copier(src, dst)
            os.unlink(src)

    def _deplacer_contenu(self, src, dst):
        for e in sorted(os.listdir(src)):
            self._verifier()
            s2 = os.path.join(src, e)
            d2 = os.path.join(dst, e)
            if os.path.lexists(d2):
                d2 = self._resoudre_conflit(s2, d2)
                if d2 is None:
                    if not meme_systeme(s2, dst):
                        self._sauter(s2)
                    continue
            try:
                self._deplacer(s2, d2)
            except OperationAnnulee:
                raise
            except OSError as exc:
                self._erreur(s2, exc)
        try:
            shutil.copystat(src, dst)
        except OSError:
            pass
        try:
            os.rmdir(src)   # échoue si des éléments ont été ignorés : on les garde
        except OSError:
            pass

    def _copier(self, src, dst):
        self._verifier()
        self.courant = src
        st = os.lstat(src)
        if stat.S_ISLNK(st.st_mode):
            if os.path.lexists(dst):
                self._supprimer(dst)
            os.symlink(os.readlink(src), dst)
            return
        if stat.S_ISDIR(st.st_mode):
            if os.path.lexists(dst) and not os.path.isdir(dst):
                self._supprimer(dst)
            os.makedirs(dst, exist_ok=True)
            for e in sorted(os.listdir(src)):
                self._verifier()
                s2 = os.path.join(src, e)
                d2 = os.path.join(dst, e)
                if os.path.lexists(d2):
                    d2 = self._resoudre_conflit(s2, d2)
                    if d2 is None:
                        self._sauter(s2)
                        continue
                try:
                    self._copier(s2, d2)
                except OperationAnnulee:
                    raise
                except OSError as e2:
                    self._erreur(s2, e2)
            try:
                shutil.copystat(src, dst)
            except OSError:
                pass
            return
        if not stat.S_ISREG(st.st_mode):
            return  # tubes, sockets, périphériques : ignorés
        if os.path.lexists(dst) and os.path.isdir(dst) and not os.path.islink(dst):
            self._supprimer(dst)
        temporaire = dst + ".exolyx-partiel"
        try:
            with open(src, "rb") as fs, open(temporaire, "wb") as fd:
                while True:
                    self._verifier()
                    bloc = fs.read(TAILLE_BLOC)
                    if not bloc:
                        break
                    fd.write(bloc)
                    self.fait += len(bloc)
                    self._progres()
            shutil.copystat(src, temporaire)
            copier_xattrs(src, temporaire)
            os.replace(temporaire, dst)
        except BaseException:
            try:
                os.unlink(temporaire)
            except OSError:
                pass
            raise

    def _sauter(self, chemin):
        """Un élément ignoré compte comme fait dans la progression."""
        self.fait += mesurer([chemin])[0]
        self._progres()

    def _supprimer(self, chemin):
        if os.path.isdir(chemin) and not os.path.islink(chemin):
            for e in os.listdir(chemin):
                self._verifier()
                self._supprimer(os.path.join(chemin, e))
            os.rmdir(chemin)
        else:
            os.unlink(chemin)
        self.fait += 1 if self.type == "supprimer" else 0

    def _supprimer_tout(self):
        self.total = mesurer(self.sources, self.annule)[1]
        self._progres(force=True)
        for s in self.sources:
            self._verifier()
            self.courant = s
            try:
                self._supprimer_compte(s)
                self.resultats.append(s)
            except OperationAnnulee:
                raise
            except OSError as e:
                self._erreur(s, e)

    def _supprimer_compte(self, chemin):
        self.courant = chemin
        if os.path.isdir(chemin) and not os.path.islink(chemin):
            for e in os.listdir(chemin):
                self._verifier()
                self._supprimer_compte(os.path.join(chemin, e))
            os.rmdir(chemin)
        else:
            os.unlink(chemin)
        self.fait += 1
        self._progres()

    def _vers_corbeille(self):
        self.total = len(self.sources)
        for s in self.sources:
            self._verifier()
            self.courant = s
            try:
                self.resultats.append(self.corbeille.jeter(s))
            except OSError as e:
                self._erreur(s, e)
            self.fait += 1
            self._progres()


# ---------------------------------------------------------------------------
# Lien avec Qt

from PyQt6.QtCore import (QAbstractListModel, QModelIndex, QObject, Qt,  # noqa: E402
                          pyqtProperty, pyqtSignal, pyqtSlot)

TITRES = {
    "copier": "Copie",
    "deplacer": "Déplacement",
    "supprimer": "Suppression",
    "corbeille": "Mise à la corbeille",
}


class GestionnaireOperations(QAbstractListModel):
    """Liste des tâches en cours pour le panneau de progression."""

    ROLES = {
        Qt.ItemDataRole.UserRole + 1: b"titre",
        Qt.ItemDataRole.UserRole + 2: b"courant",
        Qt.ItemDataRole.UserRole + 3: b"progression",
        Qt.ItemDataRole.UserRole + 4: b"detail",
        Qt.ItemDataRole.UserRole + 5: b"vitesse",
        Qt.ItemDataRole.UserRole + 6: b"terminee",
        Qt.ItemDataRole.UserRole + 7: b"ident",
        Qt.ItemDataRole.UserRole + 8: b"erreurs",
    }

    # signaux internes (émis depuis le thread de travail, reçus dans le thread principal)
    _progresInterne = pyqtSignal(int, float, float, str)
    _finInterne = pyqtSignal(int, bool)
    _conflitInterne = pyqtSignal(int, str, str)

    conflitDemande = pyqtSignal(int, str, str, arguments=["ident", "source", "destination"])
    tacheTerminee = pyqtSignal(str, list, arguments=["type", "resultats"])
    message = pyqtSignal(str, arguments=["texte"])
    actifChange = pyqtSignal()

    def __init__(self, corbeille, parent=None):
        super().__init__(parent)
        self.corbeille = corbeille
        self._taches = []        # dicts : tache, debut, vitesse, terminee
        self._suivant = 1
        self._reponses = {}      # ident -> [Event, réponse]
        self._progresInterne.connect(self._surProgres)
        self._finInterne.connect(self._surFin)
        self._conflitInterne.connect(self.conflitDemande)

    # --- modèle ---
    def roleNames(self):
        return self.ROLES

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._taches)

    def data(self, index, role):
        if not index.isValid():
            return None
        e = self._taches[index.row()]
        t = e["tache"]
        nom = self.ROLES.get(role)
        if nom == b"titre":
            n = len(t.sources)
            quoi = os.path.basename(t.sources[0]) if n == 1 else f"{n} éléments"
            vers = f" vers {os.path.basename(t.destination) or t.destination}" if t.destination else ""
            return f"{TITRES[t.type]} de {quoi}{vers}"
        if nom == b"courant":
            return os.path.basename(t.courant)
        if nom == b"progression":
            return 1.0 if e["terminee"] else (t.fait / t.total if t.total else 0.0)
        if nom == b"detail":
            from modele import format_taille
            if t.type in ("copier", "deplacer"):
                return f"{format_taille(t.fait)} sur {format_taille(t.total)}"
            return f"{t.fait} sur {t.total}"
        if nom == b"vitesse":
            from modele import format_taille
            if t.type not in ("copier", "deplacer") or e["terminee"]:
                return ""
            return f"{format_taille(e['vitesse'])}/s" if e["vitesse"] > 0 else ""
        if nom == b"terminee":
            return e["terminee"]
        if nom == b"ident":
            return e["ident"]
        if nom == b"erreurs":
            return len(t.erreurs)
        return None

    @pyqtProperty(bool, notify=actifChange)
    def actif(self):
        return any(not e["terminee"] for e in self._taches)

    # --- lancement ---
    def lancer(self, type_, sources, destination=None, politique=DEMANDER):
        if not sources:
            return None
        ident = self._suivant
        self._suivant += 1
        tache = Tache(
            type_, sources, destination, politique,
            progression=lambda f, tot, c, i=ident: self._progresInterne.emit(i, float(f), float(tot), c),
            conflit=lambda s, d, i=ident: self._attendreConflit(i, s, d),
            corbeille=self.corbeille,
        )
        self.beginInsertRows(QModelIndex(), len(self._taches), len(self._taches))
        self._taches.append({"ident": ident, "tache": tache, "debut": time.monotonic(),
                             "vitesse": 0.0, "terminee": False})
        self.endInsertRows()
        self.actifChange.emit()

        def travail():
            ok = tache.executer()
            self._finInterne.emit(ident, ok)

        threading.Thread(target=travail, daemon=True, name=f"operation-{ident}").start()
        return tache

    def _attendreConflit(self, ident, src, dst):
        evenement = threading.Event()
        self._reponses[ident] = [evenement, ("annuler", False)]
        self._conflitInterne.emit(ident, src, dst)
        while not evenement.wait(0.2):
            e = self._entree(ident)
            if e is None or e["tache"].annule.is_set():
                return "annuler", False
        return self._reponses.pop(ident)[1]

    @pyqtSlot(int, str, bool)
    def repondreConflit(self, ident, choix, pourTous):
        if ident in self._reponses:
            self._reponses[ident][1] = (choix, pourTous)
            self._reponses[ident][0].set()

    @pyqtSlot(int)
    def annuler(self, ident):
        e = self._entree(ident)
        if e:
            e["tache"].annuler()
            if ident in self._reponses:
                self.repondreConflit(ident, "annuler", False)

    @pyqtSlot()
    def effacerTerminees(self):
        for i in reversed(range(len(self._taches))):
            if self._taches[i]["terminee"]:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self._taches[i]
                self.endRemoveRows()

    def _entree(self, ident):
        for e in self._taches:
            if e["ident"] == ident:
                return e
        return None

    def _ligne(self, ident):
        for i, e in enumerate(self._taches):
            if e["ident"] == ident:
                return i
        return -1

    def _surProgres(self, ident, fait, total, courant):
        i = self._ligne(ident)
        if i < 0:
            return
        e = self._taches[i]
        duree = time.monotonic() - e["debut"]
        if duree > 0.3:
            e["vitesse"] = fait / duree
        idx = self.index(i)
        self.dataChanged.emit(idx, idx)

    def _surFin(self, ident, ok):
        i = self._ligne(ident)
        if i < 0:
            return
        e = self._taches[i]
        e["terminee"] = True
        t = e["tache"]
        idx = self.index(i)
        self.dataChanged.emit(idx, idx)
        self.actifChange.emit()
        if t.erreurs:
            chemin, msg = t.erreurs[0]
            plus = f" (et {len(t.erreurs) - 1} autre(s))" if len(t.erreurs) > 1 else ""
            self.message.emit(f"« {os.path.basename(chemin)} » : {msg}{plus}")
        elif not ok:
            self.message.emit(f"{TITRES[t.type]} annulée")
        self.tacheTerminee.emit(t.type, t.resultats)
        # Les tâches réussies quittent le panneau d'elles-mêmes
        if ok and not t.erreurs:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2500, lambda: self._retirer(ident))

    def _retirer(self, ident):
        i = self._ligne(ident)
        if i >= 0 and self._taches[i]["terminee"]:
            self.beginRemoveRows(QModelIndex(), i, i)
            del self._taches[i]
            self.endRemoveRows()

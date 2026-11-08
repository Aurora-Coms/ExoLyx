"""Contrôleur principal : onglets, navigation, actions sur la sélection, presse-papiers,
glisser-déposer, lecteurs, étiquettes et réglages, exposés au QML."""

import grp
import os
import pwd
import shutil
import stat
import threading

from PyQt6.QtCore import (QMimeData, QObject, QPoint, QProcess, QTimer, QUrl, Qt, pyqtProperty,
                          pyqtSignal, pyqtSlot)
from PyQt6.QtGui import QColor, QDesktopServices, QDrag, QFont, QGuiApplication, QPainter, QPixmap

import apercu
import etiquettes
import lecteurs
import recents
from config import dossiers_xdg
from modele import ModeleDossier, entree_pour, format_date, format_taille
from operations import est_dans, meme_systeme, mesurer, nom_unique
from recherche import Recherche

ACCUEIL = "accueil:"
CORBEILLE = "corbeille:"
PARAMETRES = "parametres:"
PREFIXE_ETIQUETTE = "etiquette:"
RECHERCHE = "recherche:"

NOMS_XDG = {"bureau": "Bureau", "documents": "Documents", "telechargements": "Téléchargements",
            "images": "Images", "musique": "Musique", "videos": "Vidéos"}

TERMINAUX = [["konsole", "--workdir"], ["kgx", "--working-directory"], ["gnome-terminal", "--working-directory"],
             ["xfce4-terminal", "--working-directory"], ["alacritty", "--working-directory"], ["foot", "-D"]]


def maison():
    return os.path.expanduser("~")


def nom_affiche(chemin):
    if chemin == maison():
        return "Dossier personnel"
    if chemin == "/":
        return "Système"
    return os.path.basename(chemin.rstrip(os.sep)) or chemin


def permissions_texte(mode):
    bits = "rwxrwxrwx"
    return "".join(b if mode & (1 << (8 - i)) else "-" for i, b in enumerate(bits))


class Onglet(QObject):
    change = pyqtSignal()
    rechercheChange = pyqtSignal()

    def __init__(self, controleur, chemin):
        super().__init__(controleur)
        self.ctrl = controleur
        self.modele = ModeleDossier(self)
        self.modele._tri = controleur.config.get("tri")
        self.modele._decroissant = bool(controleur.config.get("triDecroissant"))
        self._chemin = ""
        self._historique = []
        self._position = -1
        self._recherche = None
        self._motif = ""
        self._racineRecherche = ""
        self._rechercheEnCours = False
        self._lotInterne.connect(self._surLot)
        self._finRechercheInterne.connect(self._surFinRecherche)
        self.aller(chemin)

    _lotInterne = pyqtSignal(object)
    _finRechercheInterne = pyqtSignal(bool)

    # --- propriétés ---
    @pyqtProperty(QObject, constant=True)
    def modeleFichiers(self):
        return self.modele

    @pyqtProperty(str, notify=change)
    def chemin(self):
        return self._chemin

    @pyqtProperty(str, notify=change)
    def mode(self):
        c = self._chemin
        if c == ACCUEIL:
            return "accueil"
        if c == CORBEILLE:
            return "corbeille"
        if c == PARAMETRES:
            return "parametres"
        if c.startswith(PREFIXE_ETIQUETTE):
            return "etiquette"
        if c == RECHERCHE:
            return "recherche"
        return "dossier"

    @pyqtProperty(str, notify=change)
    def titre(self):
        m = self.mode
        if m == "accueil":
            return "Accueil"
        if m == "corbeille":
            return "Corbeille"
        if m == "parametres":
            return "Paramètres"
        if m == "etiquette":
            return self._chemin[len(PREFIXE_ETIQUETTE):]
        if m == "recherche":
            return f"« {self._motif} »"
        return nom_affiche(self._chemin)

    @pyqtProperty(str, notify=change)
    def icone(self):
        return {"accueil": "accueil", "corbeille": "supprimer", "parametres": "parametres",
                "etiquette": "etiquette", "recherche": "recherche"}.get(self.mode, "dossier")

    @pyqtProperty(bool, notify=change)
    def peutReculer(self):
        return self._position > 0

    @pyqtProperty(bool, notify=change)
    def peutAvancer(self):
        return self._position < len(self._historique) - 1

    @pyqtProperty(bool, notify=change)
    def peutMonter(self):
        return self.mode == "dossier" and self._chemin != "/" or self.mode == "recherche"

    @pyqtProperty("QVariantList", notify=change)
    def segments(self):
        """Fil d'Ariane : [{nom, chemin}] ; le dossier personnel sert de racine quand on est dedans."""
        m = self.mode
        if m == "recherche":
            base = Onglet._segments_de(self._racineRecherche)
            return base + [{"nom": f"Recherche « {self._motif} »", "chemin": RECHERCHE}]
        if m != "dossier":
            return [{"nom": self.titre, "chemin": self._chemin}]
        return Onglet._segments_de(self._chemin)

    @staticmethod
    def _segments_de(chemin):
        h = maison()
        if chemin == h or chemin.startswith(h + os.sep):
            segs = [{"nom": "Dossier personnel", "chemin": h}]
            reste = chemin[len(h):].strip(os.sep)
            base = h
        else:
            segs = [{"nom": "Système", "chemin": "/"}]
            reste = chemin.strip(os.sep)
            base = ""
        for morceau in [x for x in reste.split(os.sep) if x]:
            base = base + os.sep + morceau
            segs.append({"nom": morceau, "chemin": base})
        return segs

    @pyqtProperty(str, notify=change)
    def cheminTexte(self):
        if self.mode == "dossier":
            return self._chemin
        if self.mode == "recherche":
            return self._racineRecherche
        return ""

    @pyqtProperty(str, notify=change)
    def dossierCourant(self):
        """Dossier réel où créer/coller (vide si la vue n'en est pas un)."""
        return self._chemin if self.mode == "dossier" else ""

    @pyqtProperty(bool, notify=rechercheChange)
    def rechercheEnCours(self):
        return self._rechercheEnCours

    @pyqtProperty(str, notify=rechercheChange)
    def motif(self):
        return self._motif

    # --- navigation ---
    def aller(self, chemin, historique=True):
        self.annulerRecherche()
        if not self._charger(chemin):
            return False
        if historique:
            del self._historique[self._position + 1:]
            if not self._historique or self._historique[-1] != chemin:
                self._historique.append(chemin)
            self._position = len(self._historique) - 1
        self.change.emit()
        return True

    def _charger(self, chemin):
        precedent = self._chemin
        self._chemin = chemin
        try:
            self.recharger()
        except OSError as e:
            self._chemin = precedent
            self.ctrl.message.emit(f"Impossible d’ouvrir « {nom_affiche(chemin)} » : {e.strerror or e}")
            return False
        if self.mode == "dossier" and precedent and precedent.startswith(chemin + os.sep):
            # en remontant, on sélectionne le dossier d'où l'on vient
            enfant = chemin.rstrip(os.sep) + os.sep + precedent[len(chemin):].strip(os.sep).split(os.sep)[0]
            self.modele.selectionner_chemins([enfant])
        return True

    def recharger(self):
        m = self.mode
        caches = self.ctrl.config.get("caches")
        self.modele._caches = caches
        if m == "dossier":
            self.modele.charger(self._chemin, caches)
        elif m == "corbeille":
            entrees = []
            for el in self.ctrl.corbeille.lister():
                e = entree_pour(el["chemin"], el["nom"])
                if e:
                    e["origine"] = el["origine"]
                    e["dateSuppression"] = el["date"]
                    entrees.append(e)
            self.modele.definir_entrees(entrees)
        elif m == "etiquette":
            nom = self._chemin[len(PREFIXE_ETIQUETTE):]
            self.modele.definir_entrees([e for e in (entree_pour(c) for c in self.ctrl.index.fichiers(nom)) if e])
        elif m == "recherche":
            pass
        else:
            self.modele.definir_entrees([])

    @pyqtSlot()
    def reculer(self):
        if self._position > 0:
            self._position -= 1
            if not self._aller_historique():
                self._position += 1

    @pyqtSlot()
    def avancer(self):
        if self._position < len(self._historique) - 1:
            self._position += 1
            if not self._aller_historique():
                self._position -= 1

    def _aller_historique(self):
        cible = self._historique[self._position]
        if cible == RECHERCHE:
            cible = self._racineRecherche or maison()
        self.annulerRecherche()
        ok = self._charger(cible)
        self.change.emit()
        return ok

    @pyqtSlot()
    def monter(self):
        if self.mode == "recherche":
            self.aller(self._racineRecherche or maison())
        elif self.mode == "dossier" and self._chemin != "/":
            self.aller(os.path.dirname(self._chemin.rstrip(os.sep)) or "/")

    # --- recherche ---
    def rechercher(self, motif):
        motif = motif.strip()
        if not motif:
            if self.mode == "recherche":
                self.annulerRecherche()
                self.aller(self._racineRecherche or maison())
            return
        if self.mode != "recherche":
            self._racineRecherche = self._chemin if self.mode == "dossier" else maison()
        self.annulerRecherche()
        self._motif = motif
        self._chemin = RECHERCHE
        if not self._historique or self._historique[self._position] != RECHERCHE:
            del self._historique[self._position + 1:]
            self._historique.append(RECHERCHE)
            self._position = len(self._historique) - 1
        self.modele.definir_entrees([])
        self._rechercheEnCours = True
        caches = self.ctrl.config.get("caches")
        signal_lot = self._lotInterne
        signal_fin = self._finRechercheInterne

        def lot(chemins):
            entrees = [e for e in (entree_pour(c) for c in chemins) if e]
            signal_lot.emit((recherche_ref[0], entrees))

        def fin(annulee):
            signal_fin.emit(annulee)

        recherche_ref = [None]
        self._recherche = Recherche(self._racineRecherche, motif, lot, fin, caches)
        recherche_ref[0] = self._recherche
        self._recherche.demarrer()
        self.change.emit()
        self.rechercheChange.emit()

    def _surLot(self, donnees):
        source, entrees = donnees
        if source is self._recherche and self.mode == "recherche":
            self.modele.ajouter_entrees(entrees)

    def _surFinRecherche(self, annulee):
        if not annulee:
            self._rechercheEnCours = False
            self.rechercheChange.emit()

    @pyqtSlot()
    def annulerRecherche(self):
        if self._recherche is not None:
            self._recherche.annuler()
            self._recherche = None
        if self._rechercheEnCours:
            self._rechercheEnCours = False
            self.rechercheChange.emit()


class Controleur(QObject):
    message = pyqtSignal(str, arguments=["texte"])
    ongletsChange = pyqtSignal()
    courantChange = pyqtSignal()
    lecteursChange = pyqtSignal()
    epinglesChange = pyqtSignal()
    etiquettesChange = pyqtSignal()
    recentsChange = pyqtSignal()
    reglagesChange = pyqtSignal()
    pressePapiersChange = pyqtSignal()
    tailleCalculee = pyqtSignal(str, str, str, arguments=["chemin", "taille", "contenu"])
    _tailleInterne = pyqtSignal(str, str, str)
    renommerDemande = pyqtSignal()

    def __init__(self, config, theme, corbeille, index, operations, parent=None):
        super().__init__(parent)
        self.config = config
        self.theme = theme
        self.corbeille = corbeille
        self.index = index
        self.operations = operations
        self._onglets = []
        self._courant = 0
        self._lecteurs = []
        self._recents = []
        self._tailleInterne.connect(self.tailleCalculee)
        self._lecteursInterne.connect(self._recevoir_lecteurs)
        self.index.change.connect(self._surIndex)
        self.operations.tacheTerminee.connect(self._surOperation)
        self.operations.message.connect(self.message)
        presse = QGuiApplication.clipboard()
        if presse is not None:
            presse.dataChanged.connect(self.pressePapiersChange)
        self._minuterieLecteurs = QTimer(self, interval=4000)
        self._minuterieLecteurs.timeout.connect(self.actualiserLecteurs)
        self._minuterieLecteurs.start()
        self.actualiserLecteurs()
        self.actualiserRecents()
        self.nouvelOnglet(ACCUEIL)

    # --- onglets ---
    @pyqtProperty("QVariantList", notify=ongletsChange)
    def onglets(self):
        return list(self._onglets)

    @pyqtProperty(int, notify=courantChange)
    def courant(self):
        return self._courant

    @pyqtProperty(QObject, notify=courantChange)
    def onglet(self):
        return self._onglets[self._courant] if self._onglets else None

    def _o(self):
        return self._onglets[self._courant]

    @pyqtSlot()
    @pyqtSlot(str)
    def nouvelOnglet(self, chemin=""):
        cible = chemin or (self._o().chemin if self._onglets and self._o().mode == "dossier" else ACCUEIL)
        o = Onglet(self, cible)
        if not o.chemin:
            o.aller(ACCUEIL)
        self._onglets.insert(self._courant + 1 if self._onglets else 0, o)
        self.ongletsChange.emit()
        self.activerOnglet(self._onglets.index(o))

    @pyqtSlot(int)
    def fermerOnglet(self, i):
        if not 0 <= i < len(self._onglets):
            return
        if len(self._onglets) == 1:
            QGuiApplication.quit()
            return
        o = self._onglets.pop(i)
        o.annulerRecherche()
        if self._courant >= len(self._onglets) or self._courant > i:
            self._courant = max(0, self._courant - 1)
        self.ongletsChange.emit()
        self.courantChange.emit()
        o.deleteLater()

    @pyqtSlot(int)
    def activerOnglet(self, i):
        if 0 <= i < len(self._onglets):
            self._courant = i
            self.courantChange.emit()

    @pyqtSlot(int, int)
    def deplacerOnglet(self, de, vers):
        if 0 <= de < len(self._onglets) and 0 <= vers < len(self._onglets) and de != vers:
            o = self._onglets.pop(de)
            self._onglets.insert(vers, o)
            self._courant = vers
            self.ongletsChange.emit()
            self.courantChange.emit()

    # --- navigation ---
    @pyqtSlot(str)
    def naviguer(self, chemin):
        chemin = chemin.strip()
        if chemin.startswith("file://"):
            chemin = QUrl(chemin).toLocalFile()
        if chemin.startswith("~"):
            chemin = os.path.expanduser(chemin)
        if chemin not in (ACCUEIL, CORBEILLE, PARAMETRES) and not chemin.startswith(PREFIXE_ETIQUETTE):
            chemin = os.path.abspath(chemin)
            if not os.path.isdir(chemin):
                if os.path.exists(chemin):
                    # un fichier : on ouvre son dossier en le sélectionnant
                    if self._o().aller(os.path.dirname(chemin)):
                        self._o().modele.selectionner_chemins([chemin])
                    return
                self.message.emit(f"« {chemin} » est introuvable")
                return
        if chemin == ACCUEIL:
            self.actualiserRecents()
        self._o().aller(chemin)

    @pyqtSlot(str)
    def ouvrirChemin(self, chemin):
        if os.path.isdir(chemin):
            self.naviguer(chemin)
        else:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(chemin)):
                self.message.emit(f"Aucune application pour ouvrir « {os.path.basename(chemin)} »")

    @pyqtSlot()
    def ouvrirSelection(self):
        o = self._o()
        sel = o.modele.selection()
        if o.mode == "corbeille":
            return
        dossiers = [c for c in sel if os.path.isdir(c)]
        fichiers = [c for c in sel if not os.path.isdir(c)]
        for f in fichiers[:20]:
            self.ouvrirChemin(f)
        if dossiers:
            self.naviguer(dossiers[0])
            for d in dossiers[1:8]:
                self.nouvelOnglet(d)

    @pyqtSlot(str)
    def ouvrirDossierParent(self, chemin):
        self.naviguer(chemin)  # un fichier : son dossier s'ouvre avec lui sélectionné

    @pyqtSlot(str)
    def rechercher(self, motif):
        self._o().rechercher(motif)

    @pyqtSlot()
    def rafraichir(self):
        o = self._o()
        if o.mode == "recherche":
            o.rechercher(o.motif)
        else:
            try:
                o.recharger()
            except OSError:
                pass
        if o.mode == "accueil":
            self.actualiserRecents()
        self.actualiserLecteurs()

    def _rafraichir_tous(self):
        for o in self._onglets:
            if o.mode in ("corbeille", "etiquette"):
                try:
                    o.recharger()
                except OSError:
                    pass
            elif o.mode == "dossier":
                o.modele.rafraichir()
                if not os.path.isdir(o.chemin):
                    o.aller(maison())
            elif o.mode == "recherche":
                o.modele.rafraichir()

    # --- création, renommage ---
    @pyqtSlot(str, result=str)
    def nomParDefaut(self, genre):
        d = self._o().dossierCourant or maison()
        return nom_unique(d, "Nouveau dossier" if genre == "dossier" else "Nouveau fichier.txt")

    def _valider_nom(self, nom):
        if not nom or nom in (".", ".."):
            return "Le nom ne peut pas être vide."
        if "/" in nom:
            return "Le nom ne peut pas contenir « / »."
        if len(nom.encode("utf-8")) > 255:
            return "Le nom est trop long."
        return ""

    @pyqtSlot(str, str, result=str)
    def creer(self, genre, nom):
        """Crée un dossier ou un fichier vide ; renvoie un message d'erreur ou ""."""
        nom = nom.strip()
        erreur = self._valider_nom(nom)
        if erreur:
            return erreur
        d = self._o().dossierCourant
        if not d:
            return "Impossible de créer un élément ici."
        chemin = os.path.join(d, nom)
        if os.path.lexists(chemin):
            return f"« {nom} » existe déjà."
        try:
            if genre == "dossier":
                os.mkdir(chemin)
            else:
                with open(chemin, "x"):
                    pass
        except OSError as e:
            return e.strerror or str(e)
        self._o().modele.charger(d)
        self._o().modele.selectionner_chemins([chemin])
        return ""

    @pyqtSlot(str, str, result=str)
    def renommer(self, chemin, nouveau):
        nouveau = nouveau.strip()
        erreur = self._valider_nom(nouveau)
        if erreur:
            return erreur
        if nouveau == os.path.basename(chemin):
            return ""
        cible = os.path.join(os.path.dirname(chemin), nouveau)
        if os.path.lexists(cible) and os.path.realpath(cible) != os.path.realpath(chemin):
            return f"« {nouveau} » existe déjà."
        try:
            os.rename(chemin, cible)
        except OSError as e:
            return e.strerror or str(e)
        self.index.renommer(chemin, cible)
        o = self._o()
        o.modele.rafraichir() if o.mode != "dossier" else o.modele.charger(o.chemin)
        o.modele.selectionner_chemins([cible])
        self._mettre_a_jour_epingles(chemin, cible)
        return ""

    @pyqtSlot()
    def demanderRenommage(self):
        if self._o().modele.nbSelection == 1 and self._o().mode in ("dossier", "recherche", "etiquette"):
            self.renommerDemande.emit()

    # --- presse-papiers ---
    def _mime(self, chemins, couper):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(c) for c in chemins])
        mime.setData("application/x-kde-cutselection", b"1" if couper else b"0")
        lignes = "\n".join(["cut" if couper else "copy"] + [QUrl.fromLocalFile(c).toString() for c in chemins])
        mime.setData("x-special/gnome-copied-files", lignes.encode("utf-8"))
        mime.setText("\n".join(chemins))
        return mime

    @pyqtSlot()
    def copier(self):
        self._vers_presse_papiers(False)

    @pyqtSlot()
    def couper(self):
        self._vers_presse_papiers(True)

    def _vers_presse_papiers(self, couper):
        sel = self._o().modele.selection()
        if not sel or self._o().mode == "corbeille":
            return
        QGuiApplication.clipboard().setMimeData(self._mime(sel, couper))
        n = len(sel)
        quoi = f"« {os.path.basename(sel[0])} »" if n == 1 else f"{n} éléments"
        self.message.emit(f"{quoi} {'coupé' if couper else 'copié'}{'s' if n > 1 else ''}")

    def _lire_presse_papiers(self):
        mime = QGuiApplication.clipboard().mimeData()
        if mime is None:
            return [], False
        chemins = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
        couper = bytes(mime.data("application/x-kde-cutselection")).strip() == b"1"
        gnome = bytes(mime.data("x-special/gnome-copied-files"))
        if gnome.startswith(b"cut"):
            couper = True
        if not chemins and gnome:
            lignes = gnome.decode("utf-8", "replace").splitlines()[1:]
            chemins = [QUrl(x).toLocalFile() for x in lignes if x.startswith("file://")]
        return chemins, couper

    @pyqtProperty(bool, notify=pressePapiersChange)
    def peutColler(self):
        return bool(self._lire_presse_papiers()[0])

    @pyqtSlot()
    @pyqtSlot(str)
    def coller(self, destination=""):
        dest = destination or self._o().dossierCourant
        if not dest:
            self.message.emit("Impossible de coller ici.")
            return
        chemins, couper = self._lire_presse_papiers()
        chemins = [c for c in chemins if os.path.lexists(c)]
        if not chemins:
            return
        self.operations.lancer("deplacer" if couper else "copier", chemins, dest)
        if couper:
            QGuiApplication.clipboard().clear()

    # --- suppression, corbeille ---
    @pyqtSlot()
    def mettreALaCorbeille(self):
        o = self._o()
        sel = o.modele.selection()
        if not sel:
            return
        if o.mode == "corbeille":
            return
        self.operations.lancer("corbeille", sel)

    @pyqtSlot()
    def supprimerDefinitivement(self):
        o = self._o()
        sel = o.modele.selection()
        if not sel:
            return
        if o.mode == "corbeille":
            for c in sel:
                try:
                    self.corbeille.supprimer(c)
                except OSError as e:
                    self.message.emit(e.strerror or str(e))
            o.recharger()
            return
        self.operations.lancer("supprimer", sel)

    @pyqtSlot()
    def restaurer(self):
        o = self._o()
        restaures = []
        for c in o.modele.selection():
            try:
                cible = self.corbeille.restaurer(c)
                restaures.append(cible)
                etq = etiquettes.lire(cible)
                if etq:
                    self.index.mettre_a_jour(cible, etq)
            except OSError as e:
                self.message.emit(e.strerror or str(e))
        if restaures:
            n = len(restaures)
            self.message.emit(f"« {os.path.basename(restaures[0])} » restauré" if n == 1 else f"{n} éléments restaurés")
        self._rafraichir_tous()

    @pyqtSlot()
    def viderCorbeille(self):
        self.corbeille.vider()
        self.message.emit("La corbeille a été vidée")
        self._rafraichir_tous()
        self.ongletsChange.emit()

    @pyqtProperty(bool, notify=ongletsChange)
    def corbeilleVide(self):
        return self.corbeille.est_vide()

    def _surOperation(self, type_, resultats):
        self._rafraichir_tous()
        if type_ in ("deplacer", "corbeille", "supprimer"):
            self.index.demarrer()
        if type_ in ("copier", "deplacer") and resultats:
            o = self._o()
            if o.mode == "dossier" and all(os.path.dirname(r) == o.chemin for r in resultats):
                o.modele.selectionner_chemins(resultats)
        self.ongletsChange.emit()  # état de la corbeille

    # --- terminal ---
    @pyqtSlot()
    @pyqtSlot(str)
    def ouvrirTerminal(self, chemin=""):
        d = chemin or self._o().dossierCourant or maison()
        for commande in TERMINAUX:
            if shutil.which(commande[0]):
                if QProcess.startDetached(commande[0], commande[1:] + [d], d)[0]:
                    return
        self.message.emit("Aucun terminal trouvé (installez Konsole)")

    # --- propriétés ---
    @pyqtSlot(result="QVariantMap")
    def proprietesSelection(self):
        o = self._o()
        sel = o.modele.selection() or ([o.chemin] if o.mode == "dossier" else [])
        if not sel:
            return {}
        if len(sel) > 1:
            entrees = [entree_pour(c) for c in sel]
            entrees = [e for e in entrees if e]
            nd = sum(1 for e in entrees if e["dossier"])
            self._calculer_taille_async("*", sel)
            communes = set(entrees[0]["etiquettes"]) if entrees else set()
            for e in entrees[1:]:
                communes &= set(e["etiquettes"])
            return {"multiple": True, "nom": f"{len(sel)} éléments", "chemins": sel,
                    "type": f"{nd} dossier(s), {len(entrees) - nd} fichier(s)",
                    "emplacement": os.path.dirname(sel[0]), "taille": "Calcul…",
                    "etiquettes": sorted(communes), "categorie": "fichier", "dossier": False}
        c = sel[0]
        e = entree_pour(c)
        if e is None:
            return {}
        try:
            st = os.lstat(c)
            cible = os.stat(c) if e["lien"] else st
        except OSError:
            return {}
        try:
            proprietaire = pwd.getpwuid(cible.st_uid).pw_name
        except KeyError:
            proprietaire = str(cible.st_uid)
        try:
            groupe = grp.getgrgid(cible.st_gid).gr_name
        except KeyError:
            groupe = str(cible.st_gid)
        d = {
            "multiple": False, "nom": e["nom"], "chemins": [c], "chemin": c, "type": e["type"], "mime": e["mime"],
            "categorie": e["categorie"], "dossier": e["dossier"], "miniature": e["miniature"],
            "emplacement": os.path.dirname(c), "modifie": format_date(cible.st_mtime),
            "accede": format_date(cible.st_atime),
            "permissions": permissions_texte(stat.S_IMODE(cible.st_mode)),
            "proprietaire": f"{proprietaire} ({groupe})", "etiquettes": e["etiquettes"],
            "lien": os.readlink(c) if e["lien"] else "",
            "taille": "Calcul…" if e["dossier"] else
            f"{format_taille(e['taille'])} ({format(e['taille'], ',').replace(',', chr(0x202f))} octets)",
            "date": e["date"],
        }
        if e["dossier"]:
            self._calculer_taille_async(c, [c])
        return d

    def _calculer_taille_async(self, cle, chemins):
        def travail():
            try:
                octets, nombre = mesurer(chemins)
            except Exception:
                return
            nombre -= sum(1 for c in chemins if os.path.isdir(c))
            self._tailleInterne.emit(cle, format_taille(octets), f"{nombre} élément{'s' if nombre > 1 else ''}")
        threading.Thread(target=travail, daemon=True).start()

    # --- étiquettes ---
    def _surIndex(self):
        self.etiquettesChange.emit()
        for o in self._onglets:
            if o.mode == "etiquette":
                o.recharger()

    def _attribuer_couleurs(self, noms):
        """Donne à chaque nouvelle étiquette la couleur la moins utilisée, puis la mémorise."""
        couleurs = dict(self.config.get("couleursEtiquettes"))
        nouvelles = [n for n in noms if n not in couleurs]
        if not nouvelles:
            return
        for n in nouvelles:
            usage = {c: 0 for c in etiquettes.COULEURS}
            for c in couleurs.values():
                if c in usage:
                    usage[c] += 1
            couleurs[n] = min(etiquettes.COULEURS, key=lambda c: (usage[c], etiquettes.COULEURS.index(c)))
        self.config.set("couleursEtiquettes", couleurs)

    @pyqtProperty("QVariantList", notify=etiquettesChange)
    def etiquettes(self):
        connues = dict(self.index.toutes())
        self._attribuer_couleurs(sorted(connues, key=str.casefold))
        for nom in self.config.get("couleursEtiquettes"):
            connues.setdefault(nom, 0)
        return [{"nom": n, "nombre": connues[n], "couleur": self.couleurEtiquette(n)}
                for n in sorted(connues, key=str.casefold)]

    @pyqtSlot(str, result=str)
    def couleurEtiquette(self, nom):
        return self.config.get("couleursEtiquettes").get(nom) or etiquettes.couleur_par_defaut(nom)

    @pyqtSlot(str, str)
    def definirCouleurEtiquette(self, nom, jeton):
        couleurs = dict(self.config.get("couleursEtiquettes"))
        couleurs[nom] = jeton
        self.config.set("couleursEtiquettes", couleurs)
        self.etiquettesChange.emit()

    @pyqtSlot(list, str, bool, result=str)
    def basculerEtiquette(self, chemins, nom, ajouter):
        """Ajoute ou retire une étiquette sur des chemins ; renvoie une erreur ou ""."""
        nom = nom.replace(",", " ").strip()
        if not nom:
            return "Nom d’étiquette vide."
        erreur = ""
        for c in chemins:
            try:
                liste = etiquettes.ajouter(c, nom) if ajouter else etiquettes.retirer(c, nom)
                self.index.mettre_a_jour(c, liste)
            except OSError as e:
                erreur = f"Ce système de fichiers ne gère pas les étiquettes ({e.strerror or e})."
        if ajouter:
            self._attribuer_couleurs([nom])
        for o in self._onglets:
            for c in chemins:
                o.modele.maj_etiquettes(c)
        self.etiquettesChange.emit()
        return erreur

    @pyqtSlot(str, bool, result=str)
    def etiquetterSelection(self, nom, ajouter):
        return self.basculerEtiquette(self._o().modele.selection(), nom, ajouter)

    @pyqtSlot(result="QVariantList")
    def etiquettesCommunes(self):
        sel = self._o().modele.entrees_selectionnees()
        if not sel:
            return []
        communes = set(sel[0]["etiquettes"])
        for e in sel[1:]:
            communes &= set(e["etiquettes"])
        return sorted(communes)

    @pyqtSlot(str)
    def oublierEtiquette(self, nom):
        """Retire l'étiquette de tous les fichiers connus et de la liste."""
        self.basculerEtiquette(self.index.fichiers(nom), nom, False)
        couleurs = dict(self.config.get("couleursEtiquettes"))
        couleurs.pop(nom, None)
        self.config.set("couleursEtiquettes", couleurs)
        self.etiquettesChange.emit()

    # --- épinglés, accès rapide ---
    @pyqtProperty("QVariantList", notify=epinglesChange)
    def epingles(self):
        xdg = {c: k for k, c in dossiers_xdg()}
        resultat = []
        for c in self.config.get("epingles"):
            if os.path.isdir(c):
                cle = xdg.get(c, "")
                resultat.append({"nom": NOMS_XDG.get(cle) or nom_affiche(c), "chemin": c, "embleme": cle})
        return resultat

    @pyqtProperty("QVariantList", notify=epinglesChange)
    def accesRapide(self):
        """Accueil : dossier personnel + dossiers XDG + épinglés (sans doublon)."""
        vus = set()
        resultat = [{"nom": "Dossier personnel", "chemin": maison(), "embleme": "accueil"}]
        vus.add(maison())
        for cle, c in dossiers_xdg():
            if c not in vus:
                vus.add(c)
                resultat.append({"nom": NOMS_XDG[cle], "chemin": c, "embleme": cle})
        for e in self.epingles:
            if e["chemin"] not in vus:
                vus.add(e["chemin"])
                resultat.append(e)
        return resultat

    @pyqtSlot(str, result=bool)
    def estEpingle(self, chemin):
        return chemin in self.config.get("epingles")

    @pyqtSlot(str)
    def epingler(self, chemin):
        liste = list(self.config.get("epingles"))
        if chemin and os.path.isdir(chemin) and chemin not in liste:
            liste.append(chemin)
            self.config.set("epingles", liste)
            self.epinglesChange.emit()
            self.message.emit(f"« {nom_affiche(chemin)} » épinglé")

    @pyqtSlot(str)
    def desepingler(self, chemin):
        liste = [c for c in self.config.get("epingles") if c != chemin]
        self.config.set("epingles", liste)
        self.epinglesChange.emit()

    @pyqtSlot(int, int)
    def deplacerEpingle(self, de, vers):
        liste = list(self.config.get("epingles"))
        if 0 <= de < len(liste) and 0 <= vers < len(liste):
            liste.insert(vers, liste.pop(de))
            self.config.set("epingles", liste)
            self.epinglesChange.emit()

    def _mettre_a_jour_epingles(self, ancien, nouveau):
        liste = [nouveau + c[len(ancien):] if c == ancien or c.startswith(ancien + os.sep) else c
                 for c in self.config.get("epingles")]
        if liste != self.config.get("epingles"):
            self.config.set("epingles", liste)
            self.epinglesChange.emit()

    # --- récents ---
    @pyqtSlot()
    def actualiserRecents(self):
        liste = []
        for chemin, quand in recents.lire(12):
            e = entree_pour(chemin)
            if e:
                e["dateTexte"] = format_date(quand)
                e["dossierParent"] = os.path.dirname(chemin)
                liste.append(e)
        self._recents = liste
        self.recentsChange.emit()

    @pyqtProperty("QVariantList", notify=recentsChange)
    def recents(self):
        return self._recents

    # --- lecteurs ---
    @pyqtSlot()
    def actualiserLecteurs(self):
        def travail():
            liste = lecteurs.lister()
            self._lecteursInterne.emit(liste)
        threading.Thread(target=travail, daemon=True).start()

    _lecteursInterne = pyqtSignal(object)

    def _recevoir_lecteurs(self, liste):
        for l in liste:
            l["totalTexte"] = format_taille(l["total"]) if l["total"] else ""
            l["libreTexte"] = format_taille(l["libre"]) if l["montage"] else ""
            l["ratio"] = (l["utilise"] / l["total"]) if l["total"] and l["montage"] else 0.0
        if liste != self._lecteurs:
            self._lecteurs = liste
            self.lecteursChange.emit()

    @pyqtProperty("QVariantList", notify=lecteursChange)
    def lecteurs(self):
        return self._lecteurs

    @pyqtSlot(str, str)
    def ouvrirLecteur(self, peripherique, montage):
        if montage:
            self.naviguer(montage)
            return
        processus = QProcess(self)

        def fini(code, _statut):
            sortie = bytes(processus.readAllStandardOutput()).decode("utf-8", "replace")
            erreur = bytes(processus.readAllStandardError()).decode("utf-8", "replace").strip()
            processus.deleteLater()
            point = lecteurs.analyser_sortie_montage(sortie)
            if code == 0 and point:
                self.actualiserLecteurs()
                self.naviguer(point)
            else:
                self.message.emit(f"Montage impossible : {erreur.splitlines()[-1] if erreur else 'udisksctl a échoué'}")

        processus.finished.connect(fini)
        processus.errorOccurred.connect(lambda _e: self.message.emit("udisksctl est introuvable"))
        processus.start("udisksctl", ["mount", "--no-user-interaction", "-b", peripherique])

    @pyqtSlot(str)
    def ejecterLecteur(self, peripherique):
        for o in self._onglets:
            for l in self._lecteurs:
                if l["peripherique"] == peripherique and l["montage"] and o.mode == "dossier" \
                        and est_dans(o.chemin, l["montage"]):
                    o.aller(maison())
        processus = QProcess(self)

        def fini(code, _statut):
            erreur = bytes(processus.readAllStandardError()).decode("utf-8", "replace").strip()
            processus.deleteLater()
            if code == 0:
                self.message.emit("Le lecteur peut être retiré en toute sécurité")
            else:
                self.message.emit(f"Démontage impossible : {erreur.splitlines()[-1] if erreur else 'erreur'}")
            self.actualiserLecteurs()

        processus.finished.connect(fini)
        processus.start("udisksctl", ["unmount", "--no-user-interaction", "-b", peripherique])

    # --- glisser-déposer ---
    @pyqtSlot()
    def glisserSelection(self):
        """Démarre un glisser système avec la sélection (text/uri-list)."""
        o = self._o()
        sel = o.modele.selection()
        if not sel:
            return
        drag = QDrag(self)
        drag.setMimeData(self._mime(sel, False))
        drag.setPixmap(self._vignette_glisser(sel))
        drag.setHotSpot(QPoint(-12, -12))
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction | Qt.DropAction.LinkAction,
                  Qt.DropAction.MoveAction)
        self._rafraichir_tous()

    def _vignette_glisser(self, sel):
        ratio = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1.0
        texte = os.path.basename(sel[0]) if len(sel) == 1 else f"{len(sel)} éléments"
        police = QFont("Inter", 10)
        police.setWeight(QFont.Weight.DemiBold)
        from PyQt6.QtGui import QFontMetrics
        largeur = min(QFontMetrics(police).horizontalAdvance(texte), 260) + 28
        pix = QPixmap(int(largeur * ratio), int(30 * ratio))
        pix.setDevicePixelRatio(ratio)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(self.theme.couleur("accent")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, largeur, 30, 8, 8)
        p.setPen(QColor(self.theme.surAccent))
        p.setFont(police)
        p.drawText(14, 0, largeur - 28, 30, Qt.AlignmentFlag.AlignVCenter, texte)
        p.end()
        return pix

    @pyqtSlot(list, str, result=int)
    def deposer(self, urls, cible):
        """Dépôt d'URL sur « cible » (dossier, ou corbeille:). Maj = déplacer, Ctrl = copier,
        sinon déplacer sur le même système de fichiers et copier ailleurs. Renvoie l'action Qt."""
        chemins = []
        for u in urls:
            u = QUrl(u) if not isinstance(u, QUrl) else u
            if u.isLocalFile():
                chemins.append(u.toLocalFile())
        chemins = [c for c in chemins if os.path.lexists(c)]
        if not chemins:
            return int(Qt.DropAction.IgnoreAction.value)
        if cible == CORBEILLE:
            self.operations.lancer("corbeille", chemins)
            return int(Qt.DropAction.MoveAction.value)
        if not cible or not os.path.isdir(cible):
            return int(Qt.DropAction.IgnoreAction.value)
        # rien à faire si l'on dépose un élément dans son propre dossier ou dans lui-même
        utiles = [c for c in chemins if os.path.dirname(c) != cible and not est_dans(cible, c)]
        action = self.action_depot(chemins, cible)
        if not utiles and action == "deplacer":
            return int(Qt.DropAction.IgnoreAction.value)
        if action == "copier":
            # copier sur place = dupliquer
            self.operations.lancer("copier", [c for c in chemins if not est_dans(cible, c)], cible)
            return int(Qt.DropAction.CopyAction.value)
        self.operations.lancer("deplacer", utiles, cible)
        return int(Qt.DropAction.MoveAction.value)

    @staticmethod
    def action_depot(chemins, cible, modificateurs=None):
        if modificateurs is None:
            modificateurs = QGuiApplication.queryKeyboardModifiers()
        if modificateurs & Qt.KeyboardModifier.ShiftModifier:
            return "deplacer"
        if modificateurs & Qt.KeyboardModifier.ControlModifier:
            return "copier"
        return "deplacer" if all(meme_systeme(c, cible) for c in chemins) else "copier"

    @pyqtSlot(list, result=bool)
    def epinglerUrls(self, urls):
        ok = False
        for u in urls:
            u = QUrl(u) if not isinstance(u, QUrl) else u
            if u.isLocalFile() and os.path.isdir(u.toLocalFile()):
                self.epingler(u.toLocalFile())
                ok = True
        return ok

    # --- aperçu ---
    @pyqtSlot(str, result="QVariantMap")
    def infosApercu(self, chemin):
        e = entree_pour(chemin)
        if e is None:
            return {"genre": "aucun"}
        d = {"nom": e["nom"], "chemin": chemin, "type": e["type"], "categorie": e["categorie"],
             "taille": "" if e["dossier"] else format_taille(e["taille"]), "date": format_date(e["date"]),
             "dossier": e["dossier"], "etiquettes": e["etiquettes"], "mtime": e["date"], "pages": 0,
             "dimensions": ""}
        if e["dossier"]:
            try:
                n = len([x for x in os.listdir(chemin) if self.config.get("caches") or not x.startswith(".")])
            except OSError:
                n = 0
            d.update(genre="dossier", contenu=f"{n} élément{'s' if n > 1 else ''}")
        elif e["categorie"] == "image" and e["miniature"]:
            from PyQt6.QtGui import QImageReader
            t = QImageReader(chemin).size()
            d.update(genre="image", dimensions=f"{t.width()} × {t.height()} px" if t.isValid() else "")
        elif e["categorie"] == "pdf" and apercu.pdf_disponible():
            d.update(genre="pdf", pages=apercu.nombre_pages_pdf(chemin))
        elif e["categorie"] == "video" and e["miniature"]:
            d.update(genre="image")
        elif e["categorie"] in ("texte", "code") or e["taille"] < 512 * 1024 and e["categorie"] == "fichier":
            t = apercu.texte(chemin)
            d.update(genre="texte" if t is not None else "aucun", texte=t or "")
        else:
            d.update(genre="aucun")
        return d

    # --- réglages ---
    def _reglage(self, cle, valeur):
        self.config.set(cle, valeur)
        self.reglagesChange.emit()

    @pyqtProperty(str, notify=reglagesChange)
    def vue(self):
        return self.config.get("vue")

    @vue.setter
    def vue(self, v):
        self._reglage("vue", v)

    @pyqtProperty(str, notify=reglagesChange)
    def tri(self):
        return self.config.get("tri")

    @tri.setter
    def tri(self, v):
        self._reglage("tri", v)
        self._appliquer_tri()

    @pyqtProperty(bool, notify=reglagesChange)
    def triDecroissant(self):
        return bool(self.config.get("triDecroissant"))

    @triDecroissant.setter
    def triDecroissant(self, v):
        self._reglage("triDecroissant", bool(v))
        self._appliquer_tri()

    def _appliquer_tri(self):
        for o in self._onglets:
            o.modele.definir_tri(self.config.get("tri"), bool(self.config.get("triDecroissant")))

    @pyqtProperty(bool, notify=reglagesChange)
    def caches(self):
        return bool(self.config.get("caches"))

    @caches.setter
    def caches(self, v):
        self._reglage("caches", bool(v))
        for o in self._onglets:
            if o.mode in ("dossier", "corbeille"):
                o.recharger()
        self.message.emit("Fichiers cachés affichés" if v else "Fichiers cachés masqués")

    @pyqtProperty(str, notify=reglagesChange)
    def modeTheme(self):
        return self.config.get("theme")

    @modeTheme.setter
    def modeTheme(self, v):
        self._reglage("theme", v)
        self.theme.definir_mode(v)

    @pyqtProperty(bool, notify=reglagesChange)
    def apercuVisible(self):
        return bool(self.config.get("apercu"))

    @apercuVisible.setter
    def apercuVisible(self, v):
        self._reglage("apercu", bool(v))

    @pyqtProperty(int, notify=reglagesChange)
    def tailleIcones(self):
        return int(self.config.get("tailleIcones"))

    @tailleIcones.setter
    def tailleIcones(self, v):
        self._reglage("tailleIcones", max(80, min(208, int(v))))

    @pyqtSlot()
    def viderCacheMiniatures(self):
        racine = apercu.dossier_miniatures()
        n = 0
        for sous in ("normal", "large", "x-large", "xx-large", os.path.join("fail", "exolyx-fichiers-1.0")):
            d = os.path.join(racine, sous)
            try:
                for f in os.listdir(d):
                    if f.endswith(".png"):
                        os.unlink(os.path.join(d, f))
                        n += 1
            except OSError:
                pass
        self.message.emit(f"{n} miniature{'s' if n > 1 else ''} supprimée{'s' if n > 1 else ''}")

    @pyqtProperty(str, constant=True)
    def dossierPersonnel(self):
        return maison()

    @pyqtSlot(str, result=str)
    def urlFichier(self, chemin):
        return QUrl.fromLocalFile(chemin).toString()

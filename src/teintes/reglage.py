# SPDX-License-Identifier: GPL-3.0-or-later
"""Fenêtre « Teintes dynamiques » (PyQt6 + QML)."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QGuiApplication, QIcon
from PyQt6.QtQml import QQmlApplicationEngine

import moteur

ICI = Path(__file__).resolve().parent
NOMS_TEINTES = [(15, "rouge"), (45, "orange"), (75, "ambre"), (105, "jaune-vert"), (140, "vert"),
                (175, "émeraude"), (205, "turquoise"), (235, "bleu"), (275, "indigo"), (305, "violet"),
                (335, "magenta"), (360, "rose")]


def nom_teinte(h):
    for borne, nom in NOMS_TEINTES:
        if h < borne:
            return nom
    return "rouge"


class Controleur(QObject):
    change = pyqtSignal()

    def __init__(self, simulation=False):
        super().__init__()
        self._simulation = simulation
        self._r = moteur.lire_reglages()
        self._image = moteur.fond_actuel()
        self._analyse = moteur.analyser(moteur.pixels_image(self._image)) if self._image else None
        self._application = QTimer(singleShot=True, interval=450)
        self._application.timeout.connect(self._appliquer)
        self._message = ""

    # ---- calcul ----------------------------------------------------------
    def _sombre(self):
        if self._analyse is None:
            return "Clair" not in moteur.schema_actuel()
        return moteur.est_sombre(self._analyse, self._r["mode"])

    def _palette(self):
        sombre = self._sombre()
        if self._analyse is None or not self._r["actif"]:
            p = dict(moteur.gc.PALETTES["ExoLyx" if sombre else "ExoLyxClair"])
        else:
            p = moteur.palette_dynamique(self._analyse, sombre, self._r["intensite"], self._r["source"])
        p["voile"] = "#33" + p["accent"].lstrip("#")
        return p

    def _modifie(self):
        moteur.ecrire_reglages(self._r)
        self._message = ""
        self.change.emit()
        self._application.start()

    def _appliquer(self):
        if self._simulation:
            self._message = "Simulation : rien n'est appliqué."
        elif not self._r["actif"]:
            moteur.retablir(self._sombre())
            self._message = "Couleurs ExoLyx d'origine rétablies."
        elif self._analyse:
            moteur.appliquer_palette(self._palette(), self._sombre())
            self._message = "Couleurs appliquées."
        self.change.emit()

    # ---- propriétés --------------------------------------------------------
    @pyqtProperty(bool, notify=change)
    def actif(self):
        return bool(self._r["actif"])

    @pyqtProperty(str, notify=change)
    def mode(self):
        return self._r["mode"]

    @pyqtProperty(int, notify=change)
    def intensite(self):
        return int(self._r["intensite"])

    @pyqtProperty(str, notify=change)
    def source(self):
        return self._r["source"]

    @pyqtProperty("QVariantMap", notify=change)
    def palette(self):
        return self._palette()

    @pyqtProperty(bool, notify=change)
    def sombre(self):
        return self._sombre()

    @pyqtProperty(str, notify=change)
    def fond(self):
        return QUrl.fromLocalFile(str(self._image)).toString() if self._image else ""

    @pyqtProperty(str, notify=change)
    def description(self):
        if not self._analyse:
            return "Aucun fond d'écran trouvé."
        if self._analyse["neutre"]:
            return "Fond neutre : couleurs grises, sans teinte."
        h = self._analyse["teinte_vive" if self._r["source"] == "vive" else "teinte"]
        ton = "sombre" if self._analyse["luminosite"] < 0.62 else "clair"
        return f"Teinte {nom_teinte(h)} · fond plutôt {ton}"

    @pyqtProperty(str, notify=change)
    def message(self):
        return self._message

    @pyqtProperty(str, constant=True)
    def logo(self):
        for p in (ICI / "images" / "logo.svg", ICI.parent / "branding" / "logo.svg"):
            if p.exists():
                return QUrl.fromLocalFile(str(p)).toString()
        return ""

    # ---- actions -----------------------------------------------------------
    @pyqtSlot(bool)
    def definirActif(self, v):
        self._r["actif"] = bool(v)
        self._modifie()

    @pyqtSlot(str)
    def definirMode(self, v):
        self._r["mode"] = v
        self._modifie()

    @pyqtSlot(int)
    def definirIntensite(self, v):
        if int(v) != self._r["intensite"]:
            self._r["intensite"] = int(v)
            self._modifie()

    @pyqtSlot(str)
    def definirSource(self, v):
        self._r["source"] = v
        self._modifie()

    @pyqtSlot()
    def relire(self):
        self._image = moteur.fond_actuel()
        self._analyse = moteur.analyser(moteur.pixels_image(self._image)) if self._image else None
        self.change.emit()

    @pyqtSlot()
    def changerFond(self):
        if shutil.which("systemsettings"):
            QProcess.startDetached("systemsettings", ["kcm_wallpaper"])

    @pyqtSlot()
    def reinitialiser(self):
        self._r = dict(moteur.REGLAGES_DEFAUT)
        self._modifie()


def main():
    simulation = os.environ.get("EXOLYX_SIMULATION") == "1"
    app = QGuiApplication(sys.argv)
    app.setApplicationName("exolyx-teintes")
    app.setApplicationDisplayName("Teintes dynamiques")
    app.setDesktopFileName("exolyx-teintes")
    app.setFont(QFont("Inter", 10))
    ctrl = Controleur(simulation)
    if ctrl.logo:
        app.setWindowIcon(QIcon(QUrl(ctrl.logo).toLocalFile()))
    moteur_qml = QQmlApplicationEngine()
    moteur_qml.rootContext().setContextProperty("ctrl", ctrl)
    moteur_qml.load(QUrl.fromLocalFile(str(ICI / "qml" / "Main.qml")))
    if not moteur_qml.rootObjects():
        return 1
    # relit le fond quand la fenêtre reprend le focus (l'utilisateur a pu en changer)
    fen = moteur_qml.rootObjects()[0]
    fen.activeChanged.connect(lambda: fen.property("active") and ctrl.relire())
    code = app.exec()
    del moteur_qml  # détruit le QML avant le contrôleur (évite des erreurs à la fermeture)
    return code

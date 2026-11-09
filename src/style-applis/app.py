# SPDX-License-Identifier: GPL-3.0-or-later
"""Fenêtre « Style des applications » (PyQt6 + QML)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QSize, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QGuiApplication, QIcon
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtQuick import QQuickImageProvider

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import logique as L  # noqa: E402


class Icones(QQuickImageProvider):
    """image://icone/<nom> : icône du thème actif."""
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Pixmap)

    def requestPixmap(self, nom, demandee):
        t = demandee if demandee.isValid() and demandee.width() > 0 else QSize(32, 32)
        pm = QIcon.fromTheme(nom, QIcon.fromTheme("application-x-executable")).pixmap(t)
        return pm, pm.size()


class Controleur(QObject):
    change = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._enregistre = L.lire_etat()
        self._e = copy.deepcopy(self._enregistre)
        self._message = ""

    @pyqtProperty(str, notify=change)
    def style(self):
        return self._e["style"]

    @pyqtProperty("QVariantList", notify=change)
    def applis(self):
        return [{"id": a["id"], "nom": a["nom"], "icone": a["icone"], "coche": self._e["applis"][a["id"]]} for a in L.APPLIS]

    @pyqtProperty(bool, notify=change)
    def modifie(self):
        return self._e != self._enregistre

    @pyqtProperty(bool, notify=change)
    def parDefaut(self):
        return self._e == L.etat_par_defaut()

    @pyqtProperty(str, notify=change)
    def message(self):
        return self._message

    @pyqtSlot(str)
    def choisirStyle(self, s):
        if s in (L.ARDOISE, L.ORIGINE):
            self._e["style"] = s
            self._message = ""
            self.change.emit()

    @pyqtSlot(str)
    def basculer(self, appli_id):
        if appli_id in self._e["applis"]:
            self._e["applis"][appli_id] = not self._e["applis"][appli_id]
            self._message = ""
            self.change.emit()

    @pyqtSlot()
    def retablir(self):
        self._e = L.etat_par_defaut()
        self._message = ""
        self.change.emit()

    @pyqtSlot()
    def appliquer(self):
        try:
            L.appliquer(self._e)
            L.ecrire_etat(self._e)
            self._enregistre = copy.deepcopy(self._e)
            self._message = "Appliqué. Les logiciels déjà ouverts changeront à leur prochain lancement."
        except OSError as err:
            self._message = f"Impossible d'enregistrer les réglages : {err.strerror}."
        self.change.emit()


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("exolyx-style-applis")
    app.setApplicationDisplayName("Style des applications")
    app.setDesktopFileName("exolyx-style-applis")
    app.setWindowIcon(QIcon.fromTheme("preferences-desktop-theme"))
    moteur = QQmlApplicationEngine()
    moteur.addImageProvider("icone", Icones())
    ctrl = Controleur()
    moteur.rootContext().setContextProperty("ctrl", ctrl)
    moteur.load(QUrl.fromLocalFile(str(ICI / "qml" / "Main.qml")))
    if not moteur.rootObjects():
        sys.exit(1)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

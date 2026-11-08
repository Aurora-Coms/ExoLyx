#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rend le diaporama show.qml hors écran et enregistre une capture par diapositive.

Usage : QT_QPA_PLATFORM=offscreen python3 capturer-diaporama.py <dossier> [largeur hauteur]
Sort en erreur (code 1) si le QML produit des avertissements.
"""
import sys
from pathlib import Path
from PyQt6.QtCore import QUrl, QTimer, QtMsgType, qInstallMessageHandler
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQuick import QQuickView

QML = Path(__file__).resolve().parent.parent / "branding" / "exolyx" / "show.qml"
erreurs = []


def gestionnaire(type_, contexte, message):
    if type_ != QtMsgType.QtDebugMsg:
        erreurs.append(message)
    print(message, file=sys.stderr)


def main():
    sortie = Path(sys.argv[1])
    l, h = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (820, 460)
    qInstallMessageHandler(gestionnaire)
    app = QGuiApplication(sys.argv)
    vue = QQuickView()
    vue.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    vue.resize(l, h)
    vue.setSource(QUrl.fromLocalFile(str(QML)))
    if vue.status() != QQuickView.Status.Ready:
        print("échec de chargement", [e.toString() for e in vue.errors()])
        return 1
    vue.show()
    racine = vue.rootObject()
    racine.setProperty("actif", False)
    n = racine.property("nombre")
    etat = {"i": 0}

    def suivante():
        i = etat["i"]
        if i > 0:
            vue.grabWindow().save(str(sortie / f"calamares-diapo-{i}.png"))
        if i >= n:
            app.quit()
            return
        racine.setProperty("courant", i)
        etat["i"] = i + 1
        QTimer.singleShot(900, suivante)

    QTimer.singleShot(200, suivante)
    app.exec()
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())

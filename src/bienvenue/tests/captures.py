#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Captures hors écran de chaque étape de l'appli de bienvenue.

Usage : QT_QPA_PLATFORM=offscreen python3 tests/captures.py <dossier_sortie>
Variables utiles : EXOLYX_DOSSIER_ICONES (thèmes d'icônes générés),
EXOLYX_DOSSIER_FONDS (src/wallpapers). Le helper tourne en --simulation.
Code de sortie 1 si le QML émet un avertissement ou une erreur.
"""
import os
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp())
os.environ["EXOLYX_SIMULATION"] = "1"

from PyQt6.QtCore import QObject, QTimer, QUrl, QtMsgType, qInstallMessageHandler  # noqa: E402
from PyQt6.QtGui import QFont, QGuiApplication  # noqa: E402
from PyQt6 import sip  # noqa: E402
from PyQt6.QtQml import QQmlApplicationEngine  # noqa: E402
from PyQt6.QtQuick import QQuickWindow  # noqa: E402

import bienvenue  # noqa: E402
import logique  # noqa: E402

problemes = []


def gestionnaire(type_, _ctx, message):
    print(message, file=sys.stderr)
    if type_ != QtMsgType.QtDebugMsg:
        problemes.append(message)


def main():
    sortie = Path(sys.argv[1])
    sortie.mkdir(parents=True, exist_ok=True)
    qInstallMessageHandler(gestionnaire)
    app = QGuiApplication(sys.argv[:1])
    app.setFont(QFont("Inter", 10))
    cartes = logique.analyser_lspci(
        "00:02.0 VGA compatible controller [0300]: Intel Corporation UHD Graphics 630 [8086:3e92]\n"
        "01:00.0 VGA compatible controller [0300]: NVIDIA Corporation TU106 [GeForce RTX 2060] [10de:1f08] (rev a1)\n")

    scenarios = []
    for live in (False, True):
        ctrl = bienvenue.Controleur(live=live, simulation=True, cartes=cartes, virt="none")
        moteur = QQmlApplicationEngine()
        moteur.rootContext().setContextProperty("ctrl", ctrl)
        moteur.load(QUrl.fromLocalFile(str(ICI.parent / "qml" / "Main.qml")))
        if not moteur.rootObjects():
            print("échec du chargement QML")
            return 1
        scenarios.append((ctrl, moteur, sip.cast(moteur.rootObjects()[0], QQuickWindow)))

    (c, _m, f), (cl, _ml, fl) = scenarios
    fl.setVisible(False)
    def deplier():
        """Journal déplié pour la capture d'installation."""
        c.journalDeplie = True

    pages = [
        (lambda: c.allerA(0), "bienvenue-1-accueil"),
        (lambda: c.allerA(1), "bienvenue-2-apparence-sombre"),
        (lambda: c.choisirTheme(False), "bienvenue-2-apparence-clair"),
        (lambda: (c.choisirTheme(True), c.choisirIcones("Relief"), c.allerA(2)), "bienvenue-3-pilotes"),
        (lambda: (c.allerA(3), [c.basculerAppli(i) for i in ("libreoffice", "vlc", "steam")]), "bienvenue-4-applis"),
        (lambda: (c.installerApplis(), deplier()), "bienvenue-4-applis-en-cours"),
        (lambda: None, "bienvenue-4-applis-installation"),
        (lambda: c.allerA(4), "bienvenue-5-termine"),
        (lambda: (f.setVisible(False), fl.setVisible(True), cl.allerA(0)), "bienvenue-live-1-accueil"),
        (lambda: cl.allerA(2), "bienvenue-live-3-termine"),
    ]
    etat = {"i": 0, "attente": None}

    def fenetre_active():
        return fl if fl.isVisible() else f

    def pas():
        i = etat["i"]
        if etat["attente"]:
            nom = etat["attente"]
            fenetre_active().grabWindow().save(str(sortie / f"{nom}.png"))
            print("capture", nom)
            etat["attente"] = None
        if i >= len(pages):
            app.quit()
            return
        action, nom = pages[i]
        action()
        etat["i"] = i + 1
        etat["attente"] = nom
        # l'installation simulée dure ~2 s : on attend sa fin
        delai = {"bienvenue-4-applis-en-cours": 1000, "bienvenue-4-applis-installation": 2200}.get(nom, 500)
        QTimer.singleShot(delai, pas)


    QTimer.singleShot(400, pas)
    app.exec()
    if problemes:
        print(f"{len(problemes)} avertissement(s) QML")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

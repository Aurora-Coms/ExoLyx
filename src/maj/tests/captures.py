#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Captures hors écran de la fenêtre de mises à jour (simulation, rien n'est modifié).

Usage : QT_QPA_PLATFORM=offscreen python3 tests/captures.py <dossier_sortie>
Code 1 si le QML émet un avertissement.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
os.environ["EXOLYX_SIMULATION"] = "1"
os.environ.setdefault("EXOLYX_SNAPPER_SORTIE", """ # │ Type   │ Pré # │ Date                       │ Utilisateur │ Nettoyage │ Description         │ Données utilisateur
───┼────────┼───────┼────────────────────────────┼─────────────┼───────────┼─────────────────────┼────────────────────
0  │ single │       │                            │ root        │           │ current             │
41 │ single │       │ ven. 08 nov. 2026 08:00:01 │ root        │ timeline  │ timeline            │
42 │ pre    │       │ ven. 08 nov. 2026 09:43:12 │ root        │ number    │ pacman -Syu         │
43 │ post   │    42 │ ven. 08 nov. 2026 09:45:40 │ root        │ number    │ firefox linux mesa  │""")

from PyQt6 import sip  # noqa: E402
from PyQt6.QtCore import QObject, QTimer, QUrl, QtMsgType, qInstallMessageHandler  # noqa: E402
from PyQt6.QtGui import QFont  # noqa: E402
from PyQt6.QtQml import QQmlApplicationEngine  # noqa: E402
from PyQt6.QtQuick import QQuickWindow  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

import maj  # noqa: E402

problemes = []


def gestionnaire(type_, _ctx, message):
    print(message, file=sys.stderr)
    if type_ != QtMsgType.QtDebugMsg:
        problemes.append(message)


def fenetre(ctrl):
    moteur = QQmlApplicationEngine()
    moteur.rootContext().setContextProperty("ctrl", ctrl)
    moteur.load(QUrl.fromLocalFile(str(ICI.parent / "qml" / "Main.qml")))
    if not moteur.rootObjects():
        raise SystemExit("échec du chargement QML")
    f = sip.cast(moteur.rootObjects()[0], QQuickWindow)
    return moteur, f


def main():
    sortie = Path(sys.argv[1])
    qInstallMessageHandler(gestionnaire)
    app = QApplication(sys.argv[:1])
    app.setFont(QFont("Inter", 10))
    fixture = json.loads((ICI / "fixture-maj.json").read_text(encoding="utf-8"))

    # thème sombre
    os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()
    c = maj.Controleur(simulation=True)
    m, f = fenetre(c)
    # thème clair
    d = tempfile.mkdtemp()
    Path(d, "kdeglobals").write_text("[General]\nColorScheme=ExoLyxClair\n")
    os.environ["XDG_CONFIG_HOME"] = d
    cc = maj.Controleur(simulation=True)
    mc, fc = fenetre(cc)

    etapes = [
        (lambda: (f.show(), c.charger(fixture)), f, "maj-1-liste"),
        (lambda: (c.__setattr__("journalDeplie", True), c.toutMettreAJour()), f, None),
        (lambda: None, f, "maj-2-en-cours"),
        (lambda: c.__setattr__("journalDeplie", False), f, "maj-3-termine-redemarrage"),
        (lambda: (c.chargerInstantanes(), ouvrir_popup(f)), f, "maj-4-instantanes"),
        (lambda: (f.hide(), fc.show(), cc.charger({**fixture, "pacman": [], "flatpak": []})), fc, "maj-5-a-jour-clair"),
        (lambda: cc.charger(fixture), fc, "maj-6-liste-clair"),
    ]

    def ouvrir_popup(fen):
        """Le Popup n'est pas un QQuickItem : on l'ouvre par son objectName."""
        fen.findChild(QObject, "fenetreInstantanes").setProperty("visible", True)

    delais = {"maj-2-en-cours": 1100, "maj-3-termine-redemarrage": 2400}
    etat = {"i": 0, "attente": None}

    def pas():
        if etat["attente"]:
            fen, nom = etat["attente"]
            fen.grabWindow().save(str(sortie / f"{nom}.png"))
            print("capture", nom)
            etat["attente"] = None
        i = etat["i"]
        if i >= len(etapes):
            app.quit()
            return
        action, fen, nom = etapes[i]
        action()
        etat["i"] = i + 1
        if nom:
            etat["attente"] = (fen, nom)
        QTimer.singleShot(delais.get(nom, 500) if nom else 50, pas)

    QTimer.singleShot(300, pas)
    app.exec()
    if problemes:
        print(f"{len(problemes)} avertissement(s) QML")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

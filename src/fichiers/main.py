#!/usr/bin/env python3
"""Fichiers — l'explorateur de fichiers d'ExoLyx (Python 3 + PyQt6 + QML)."""

import os
import signal
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PyQt6.QtCore import QUrl  # noqa: E402
from PyQt6.QtGui import QFont, QGuiApplication, QIcon  # noqa: E402
from PyQt6.QtQml import QQmlApplicationEngine  # noqa: E402

import apercu  # noqa: E402
import icones  # noqa: E402
from config import Config, Theme  # noqa: E402
from controleur import Controleur  # noqa: E402
from corbeille import Corbeille  # noqa: E402
from etiquettes import IndexEtiquettes  # noqa: E402
from operations import GestionnaireOperations  # noqa: E402


def chemin_logo():
    """Logo installé à côté de l'appli, sinon celui du dépôt (src/branding)."""
    for c in (os.path.join(ICI, "logo.svg"), os.path.join(ICI, "..", "branding", "logo.svg")):
        if os.path.exists(c):
            return os.path.abspath(c)
    return ""


def creer_application(argv, demarrer_index=True):
    """Construit l'application ; renvoie (app, moteur, contrôleur). Sert aussi aux captures."""
    app = QGuiApplication.instance() or QGuiApplication(argv)
    app.setApplicationName("exolyx-fichiers")
    app.setApplicationDisplayName("Fichiers")
    app.setOrganizationName("ExoLyx")
    app.setDesktopFileName("exolyx-fichiers")
    app.setWindowIcon(QIcon.fromTheme("system-file-manager"))
    police = QFont("Inter")
    police.setPointSizeF(10)
    app.setFont(police)

    config = Config()
    theme = Theme(config.get("theme"), app)
    corbeille = Corbeille()
    index = IndexEtiquettes(parent=app)
    operations = GestionnaireOperations(corbeille, app)
    controleur = Controleur(config, theme, corbeille, index, operations, app)

    chemins = [a for a in argv[1:] if not a.startswith("-")]
    if chemins:
        controleur.naviguer(chemins[0])
        for c in chemins[1:]:
            controleur.nouvelOnglet(QUrl(c).toLocalFile() if c.startswith("file:") else os.path.abspath(c))

    moteur = QQmlApplicationEngine()
    moteur.addImageProvider("icone", icones.FournisseurIcones())
    moteur.addImageProvider("miniature", apercu.FournisseurMiniatures())
    moteur.addImageProvider("apercu", apercu.FournisseurApercu())
    contexte = moteur.rootContext()
    contexte.setContextProperty("controleur", controleur)
    contexte.setContextProperty("theme", theme)
    contexte.setContextProperty("operations", operations)
    contexte.setContextProperty("indexEtiquettes", index)
    contexte.setContextProperty("cheminLogo", QUrl.fromLocalFile(chemin_logo()).toString())
    moteur.load(QUrl.fromLocalFile(os.path.join(ICI, "qml", "Main.qml")))
    if demarrer_index:
        index.demarrer()
    app.aboutToQuit.connect(index.arreter)
    return app, moteur, controleur


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app, moteur, _ = creer_application(sys.argv)
    if not moteur.rootObjects():
        sys.exit(1)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

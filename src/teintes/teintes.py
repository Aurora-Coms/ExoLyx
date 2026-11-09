#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Teintes dynamiques ExoLyx.

    exolyx-teintes              ouvre le réglage « Teintes dynamiques »
    exolyx-teintes service      suit le fond d'écran et réapplique les couleurs (session)
    exolyx-teintes appliquer [--image FICHIER]
    exolyx-teintes analyser FICHIER
    exolyx-teintes retablir     revient au vert ExoLyx d'origine
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import moteur  # noqa: E402


def service():
    from PyQt6.QtCore import QCoreApplication, QFileSystemWatcher, QTimer

    app = QCoreApplication(sys.argv)
    surveillant = QFileSystemWatcher()
    minuterie = QTimer(singleShot=True, interval=700)
    dernier = {"cle": None}

    def surveiller():
        # Plasma et notre réglage réécrivent leurs fichiers (remplacement atomique) :
        # on surveille aussi les dossiers et on réarme les fichiers à chaque fois.
        for chemin in (moteur.APPLETSRC, moteur.FICHIER_REGLAGES):
            for p in (chemin, chemin.parent):
                if p.exists() and str(p) not in surveillant.files() + surveillant.directories():
                    surveillant.addPath(str(p))

    def mettre_a_jour():
        surveiller()
        r = moteur.lire_reglages()
        image = moteur.fond_actuel()
        cle = json.dumps([str(image), r], sort_keys=True)
        if cle == dernier["cle"]:
            return
        dernier["cle"] = cle
        if r["actif"] and image:
            print("teintes :", image, "->", moteur.mettre_a_jour(image), flush=True)

    minuterie.timeout.connect(mettre_a_jour)
    surveillant.fileChanged.connect(lambda _: minuterie.start())
    surveillant.directoryChanged.connect(lambda _: minuterie.start())
    surveiller()
    QTimer.singleShot(4000, mettre_a_jour)  # laisse Plasma démarrer
    return app.exec()


def main():
    ap = argparse.ArgumentParser(prog="exolyx-teintes", description="Teintes dynamiques ExoLyx")
    sous = ap.add_subparsers(dest="cmd")
    sous.add_parser("service")
    a = sous.add_parser("appliquer")
    a.add_argument("--image")
    a = sous.add_parser("analyser")
    a.add_argument("image")
    sous.add_parser("retablir")
    args = ap.parse_args()

    if args.cmd == "service":
        return service()
    if args.cmd == "appliquer":
        print(moteur.mettre_a_jour(args.image) or "inactif ou aucun fond trouvé")
        return 0
    if args.cmd == "analyser":
        a = moteur.analyser(moteur.pixels_image(args.image))
        r = moteur.lire_reglages()
        s = moteur.est_sombre(a, r["mode"])
        print(json.dumps({"analyse": a, "sombre": s,
                          "palette": moteur.palette_dynamique(a, s, r["intensite"], r["source"])},
                         indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "retablir":
        moteur.retablir("Clair" not in moteur.schema_actuel())
        return 0
    import reglage
    return reglage.main()


if __name__ == "__main__":
    sys.exit(main())

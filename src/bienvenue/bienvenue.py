#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bienvenue dans ExoLyx — assistant de premier démarrage (PyQt6 + QML).

Options :
    --demarrage    lancement automatique de session : quitte aussitôt si
                   l'assistant a déjà été terminé (~/.config/exolyx/bienvenue.json)
    --etape N      ouvre directement l'étape N (0 = Bienvenue)
Variables d'environnement (développement) :
    EXOLYX_LIVE=1|0         force le mode live
    EXOLYX_SIMULATION=1     le helper est lancé sans pkexec en mode --simulation
                            et les commandes d'apparence sont seulement journalisées
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from PyQt6.QtCore import (QObject, QProcess, QUrl, pyqtProperty, pyqtSignal,  # noqa: E402
                          pyqtSlot)
from PyQt6.QtGui import QDesktopServices, QFont, QGuiApplication, QIcon  # noqa: E402
from PyQt6.QtQml import QQmlApplicationEngine  # noqa: E402

import logique  # noqa: E402

RE_ETAPE = re.compile(r"^@@ETAPE (\d+) (\d+) (.*)$")
RE_PROGRES = re.compile(r"^@@PROGRES (\d+)$")
RE_FIN = re.compile(r"^@@FIN (\d+)$")
MESSAGES_FIN = {
    0: "Installation terminée.",
    2: "Requête refusée par le helper.",
    3: "Droits administrateur requis.",
    4: "Une autre installation est en cours. Réessayez dans un instant.",
    5: "L'installation a échoué. Consultez le journal.",
    126: "Authentification annulée.",
    127: "Authentification refusée.",
}


def url_fichier(chemin: str) -> str:
    return QUrl.fromLocalFile(chemin).toString() if chemin else ""


class Controleur(QObject):
    sombreChange = pyqtSignal()
    etapeChange = pyqtSignal()
    selectionChange = pyqtSignal()
    styleChange = pyqtSignal()
    tacheChange = pyqtSignal()
    journalChange = pyqtSignal()
    demarrageChange = pyqtSignal()
    deplieChange = pyqtSignal()

    def __init__(self, live: bool, simulation: bool, cartes=None, virt=None):
        super().__init__()
        self._live = live
        self._simulation = simulation
        self._sombre = logique.theme_sombre()
        self._etape = 0
        self._style = "Duo"
        etat = logique.lire_etat()
        self._afficher_demarrage = bool(etat.get("afficherAuDemarrage", False))
        self._etapes = (["Bienvenue", "Apparence", "Terminé"] if live else
                        ["Bienvenue", "Apparence", "Pilotes", "Applications", "Terminé"])
        # matériel
        self._cartes = logique.detecter_cartes() if cartes is None else cartes
        self._virt = logique.detecter_virtualisation() if virt is None else virt
        pilotes, self._remarques = logique.pilotes_proposes(self._cartes, self._virt)
        self._pilotes = pilotes
        self._pilotes_coches = {p.id for p in pilotes if p.recommande}
        self._applis_cochees: set[str] = set()
        # tâche en cours
        self._proc: QProcess | None = None
        self._occupe = False
        self._progression = 0.0
        self._libelle = ""
        self._resultat = ""
        self._message = ""
        self._journal: list[str] = []
        self._tampon = ""
        self._file_cmds: list[list[str]] = []
        self._installes: set[str] = set()
        self._journal_deplie = False

    # ---- propriétés générales -------------------------------------------
    @pyqtProperty(bool, constant=True)
    def live(self):
        return self._live

    @pyqtProperty(bool, constant=True)
    def simulation(self):
        return self._simulation

    @pyqtProperty(str, constant=True)
    def logo(self):
        return url_fichier(logique.chemin_logo())

    @pyqtProperty(list, constant=True)
    def etapes(self):
        return self._etapes

    @pyqtProperty(int, notify=etapeChange)
    def etape(self):
        return self._etape

    @pyqtProperty(str, notify=etapeChange)
    def nomEtape(self):
        return self._etapes[self._etape]

    @pyqtProperty(bool, notify=sombreChange)
    def sombre(self):
        return self._sombre

    @pyqtProperty("QVariantMap", notify=sombreChange)
    def palette(self):
        return logique.PALETTES[self._sombre]

    @pyqtProperty(bool, notify=demarrageChange)
    def afficherAuDemarrage(self):
        return self._afficher_demarrage

    @afficherAuDemarrage.setter
    def afficherAuDemarrage(self, v):
        if v != self._afficher_demarrage:
            self._afficher_demarrage = v
            self.demarrageChange.emit()

    # ---- apparence ----------------------------------------------------------
    @pyqtProperty(str, notify=styleChange)
    def styleIcones(self):
        return self._style

    @pyqtProperty(list, constant=True)
    def stylesIcones(self):
        return [{"nom": s, "description": logique.DESCRIPTIONS_ICONES[s]}
                for s in logique.STYLES_ICONES]

    @pyqtProperty("QVariantMap", notify=sombreChange)
    def apercus(self):
        return {s: [url_fichier(p) for p in
                    logique.apercu_icones(logique.theme_icones(s, self._sombre))]
                for s in logique.STYLES_ICONES}

    @pyqtProperty("QVariantMap", constant=True)
    def fonds(self):
        return {"sombre": url_fichier(logique.trouver_fond(True)["image"]),
                "clair": url_fichier(logique.trouver_fond(False)["image"])}

    @pyqtSlot(bool)
    def choisirTheme(self, sombre: bool):
        if sombre != self._sombre:
            self._sombre = sombre
            self.sombreChange.emit()
        self._executer_utilisateur(logique.commandes_apparence(sombre, self._style),
                                   "Thème " + ("sombre" if sombre else "clair"))

    @pyqtSlot(str)
    def choisirIcones(self, style: str):
        if style not in logique.STYLES_ICONES:
            return
        self._style = style
        self.styleChange.emit()
        self._executer_utilisateur(logique.commandes_icones(style, self._sombre),
                                   f"Icônes {style}")

    def _executer_utilisateur(self, cmds: list[list[str]], libelle: str):
        """Commandes sans privilèges, enchaînées en arrière-plan."""
        self._ajouter_journal(f"— {libelle}")
        for c in cmds:
            if self._simulation or not shutil.which(c[0]) and not os.path.exists(c[0]):
                self._ajouter_journal(("[simulation] " if self._simulation else "[absent] ")
                                      + " ".join(c))
                continue
            self._file_cmds.append(c)
        self._suivante_utilisateur()

    def _suivante_utilisateur(self):
        if not self._file_cmds or getattr(self, "_proc_util", None):
            return
        cmd = self._file_cmds.pop(0)
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._proc_util = p
        self._ajouter_journal("$ " + " ".join(cmd))

        def fini(code, _statut, p=p):
            sortie = bytes(p.readAll()).decode(errors="replace").strip()
            if sortie:
                self._ajouter_journal(sortie)
            if code:
                self._ajouter_journal(f"(code {code})")
            self._proc_util = None
            p.deleteLater()
            self._suivante_utilisateur()
        p.finished.connect(fini)
        p.start(cmd[0], cmd[1:])

    # ---- pilotes --------------------------------------------------------------
    @pyqtProperty(list, notify=selectionChange)
    def pilotes(self):
        return [{"id": p.id, "nom": p.nom, "description": p.description,
                 "paquets": " ".join(p.paquets), "coche": p.id in self._pilotes_coches,
                 "installe": p.id in self._installes}
                for p in self._pilotes]

    @pyqtProperty(list, constant=True)
    def remarques(self):
        return self._remarques

    @pyqtProperty(list, constant=True)
    def materiel(self):
        lignes = [f"{c.nom} ({c.fabricant.upper() if c.fabricant != 'autre' else 'autre'})"
                  for c in self._cartes]
        if self._virt not in ("none", ""):
            lignes.append(f"Machine virtuelle : {self._virt}")
        return lignes or ["Aucune carte graphique identifiée"]

    @pyqtSlot(str)
    def basculerPilote(self, id_: str):
        self._pilotes_coches ^= {id_}
        self.selectionChange.emit()

    @pyqtSlot()
    def installerPilotes(self):
        paquets = [p for pil in self._pilotes if pil.id in self._pilotes_coches
                   for p in pil.paquets]
        if paquets:
            self._lancer_helper(logique.jetons_installation([], paquets),
                                {p.id for p in self._pilotes if p.id in self._pilotes_coches})

    # ---- applications --------------------------------------------------------
    @pyqtProperty(list, notify=selectionChange)
    def applis(self):
        return [{"id": a.id, "nom": a.nom, "description": a.description,
                 "source": "Flathub" if a.source == "flatpak" else "Dépôts",
                 "couleur": a.couleur, "coche": a.id in self._applis_cochees,
                 "installe": a.id in self._installes}
                for a in logique.CATALOGUE]

    @pyqtProperty(int, notify=selectionChange)
    def nombreApplis(self):
        return len(self._applis_cochees)

    @pyqtSlot(str)
    def basculerAppli(self, id_: str):
        self._applis_cochees ^= {id_}
        self.selectionChange.emit()

    @pyqtSlot()
    def installerApplis(self):
        ids = [a.id for a in logique.CATALOGUE if a.id in self._applis_cochees]
        if ids:
            self._lancer_helper(logique.jetons_installation(ids), set(ids))

    # ---- tâche root (helper via pkexec) ----------------------------------------
    @pyqtProperty(bool, notify=tacheChange)
    def occupe(self):
        return self._occupe

    @pyqtProperty(float, notify=tacheChange)
    def progression(self):
        return self._progression

    @pyqtProperty(str, notify=tacheChange)
    def libelle(self):
        return self._libelle

    @pyqtProperty(str, notify=tacheChange)
    def resultat(self):
        return self._resultat

    @pyqtProperty(str, notify=tacheChange)
    def message(self):
        return self._message

    @pyqtProperty(bool, notify=deplieChange)
    def journalDeplie(self):
        return self._journal_deplie

    @journalDeplie.setter
    def journalDeplie(self, v):
        if v != self._journal_deplie:
            self._journal_deplie = v
            self.deplieChange.emit()

    @pyqtProperty(str, notify=journalChange)
    def journal(self):
        return "\n".join(self._journal)

    def _ajouter_journal(self, texte: str):
        self._journal.extend(texte.splitlines() or [""])
        del self._journal[:-2000]
        self.journalChange.emit()

    def _lancer_helper(self, jetons: list[str], cibles: set[str]):
        if self._occupe:
            return
        if self._simulation:
            prog = sys.executable
            args = [str(ICI / "helper" / "exolyx-helper"), "installer", "--simulation", *jetons]
        else:
            prog, args = "pkexec", [logique.HELPER, "installer", *jetons]
        self._cibles = cibles
        self._occupe, self._progression, self._resultat = True, 0.0, ""
        self._libelle, self._message = "Demande d'autorisation…", ""
        self.tacheChange.emit()
        self._ajouter_journal(f"— {datetime.now():%H:%M:%S} {prog} {' '.join(args)}")
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self._lire_helper)
        p.finished.connect(self._fin_helper)
        p.errorOccurred.connect(self._erreur_helper)
        self._proc = p
        p.start(prog, args)

    def _lire_helper(self):
        self._tampon += bytes(self._proc.readAllStandardOutput()).decode(errors="replace")
        *lignes, self._tampon = self._tampon.split("\n")
        for ligne in lignes:
            self.traiter_ligne(ligne)

    def traiter_ligne(self, ligne: str):
        if m := RE_ETAPE.match(ligne):
            self._libelle = f"Étape {m.group(1)}/{m.group(2)} — {m.group(3)}"
            self.tacheChange.emit()
            self._ajouter_journal(f"▶ Étape {m.group(1)}/{m.group(2)} : {m.group(3)}")
        elif m := RE_PROGRES.match(ligne):
            self._progression = max(self._progression, min(int(m.group(1)), 100) / 100)
            self.tacheChange.emit()
        elif RE_FIN.match(ligne):
            pass
        else:
            self._ajouter_journal(ligne)

    def _fin_helper(self, code: int, _statut=None):
        if self._tampon:
            self.traiter_ligne(self._tampon)
            self._tampon = ""
        self._occupe = False
        self._resultat = "ok" if code == 0 else "erreur"
        self._message = MESSAGES_FIN.get(code, f"Échec (code {code}).")
        self._libelle = self._message
        if code == 0:
            self._progression = 1.0
            self._installes |= self._cibles
            self._pilotes_coches -= self._cibles
            self._applis_cochees -= self._cibles
            self.selectionChange.emit()
        self.tacheChange.emit()
        self._proc.deleteLater()
        self._proc = None

    def _erreur_helper(self, erreur):
        if erreur == QProcess.ProcessError.FailedToStart:
            self._ajouter_journal("Impossible de lancer pkexec.")
            self._occupe, self._resultat = False, "erreur"
            self._message = self._libelle = "Impossible de lancer l'outil d'installation."
            self.tacheChange.emit()

    # ---- navigation ----------------------------------------------------------
    @pyqtSlot(int)
    def allerA(self, i: int):
        if 0 <= i < len(self._etapes) and i != self._etape:
            self._etape = i
            self.etapeChange.emit()

    @pyqtSlot()
    def suivant(self):
        self.allerA(self._etape + 1)

    @pyqtSlot()
    def precedent(self):
        self.allerA(self._etape - 1)

    @pyqtSlot()
    def lancerInstallateur(self):
        self._ajouter_journal("Lancement de l'installateur…")
        if self._simulation:
            return
        QProcess.startDetached(logique.INSTALLATEUR, [])

    @pyqtSlot(str)
    def ouvrirLien(self, url: str):
        cible = {"aide": logique.URL_AIDE, "depot": logique.URL_DEPOT}.get(url, "")
        if cible:
            QDesktopServices.openUrl(QUrl(cible))

    @pyqtSlot()
    def terminer(self):
        if not self._live:
            logique.ecrire_etat({
                "termine": True,
                "afficherAuDemarrage": self._afficher_demarrage,
                "date": datetime.now().isoformat(timespec="seconds"),
                "version": 1,
            })
        QGuiApplication.quit()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="exolyx-bienvenue")
    parser.add_argument("--demarrage", action="store_true")
    parser.add_argument("--etape", type=int, default=0)
    args, reste = parser.parse_known_args(argv)
    live = logique.mode_live()
    if args.demarrage and not logique.doit_afficher_au_demarrage(live=live):
        return 0
    app = QGuiApplication([sys.argv[0], *reste])
    app.setApplicationName("exolyx-bienvenue")
    app.setApplicationDisplayName("Bienvenue dans ExoLyx")
    app.setDesktopFileName("exolyx-bienvenue")
    app.setFont(QFont("Inter", 10))
    if logique.chemin_logo():
        app.setWindowIcon(QIcon(logique.chemin_logo()))
    ctrl = Controleur(live, os.environ.get("EXOLYX_SIMULATION") == "1")
    ctrl.allerA(args.etape)
    moteur = QQmlApplicationEngine()
    moteur.rootContext().setContextProperty("ctrl", ctrl)
    moteur.load(QUrl.fromLocalFile(str(ICI / "qml" / "Main.qml")))
    if not moteur.rootObjects():
        return 1
    app._ctrl, app._moteur = ctrl, moteur  # garder les références
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

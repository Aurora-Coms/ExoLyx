#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Mises à jour ExoLyx — mises à jour en un clic (PyQt6 + QML).

    exolyx-maj              ouvre la fenêtre (et l'icône de notification s'il y a des mises à jour)
    exolyx-maj --verifier   vérification silencieuse (service systemd utilisateur) ;
                            s'il y a des mises à jour, démarre « exolyx-maj --zone »
    exolyx-maj --zone       icône dans la zone de notification + notification de bureau

Développement : EXOLYX_SIMULATION=1 (helper en --simulation, rien n'est modifié),
EXOLYX_MAJ_FIXTURE=<fichier.json> (résultat de vérification simulé).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

import logique_maj as lm  # noqa: E402


def chemin_socket() -> str:
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/exolyx-{os.getuid()}"
    os.makedirs(base, mode=0o700, exist_ok=True)
    return os.path.join(base, "exolyx-maj.sock")


def envoyer_instance(message: str) -> bool:
    """Transmet un message à une instance déjà lancée. Faux s'il n'y en a pas."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(chemin_socket())
            s.sendall(message.encode() + b"\n")
        return True
    except OSError:
        return False


def resultat_verification() -> dict:
    fixture = os.environ.get("EXOLYX_MAJ_FIXTURE")
    if fixture:
        return json.loads(Path(fixture).read_text(encoding="utf-8"))
    return lm.verifier()


def mode_verifier() -> int:
    """Appelé par exolyx-maj.service (minuteur). Aucune interface."""
    if lm.mode_live():
        return 0
    res = resultat_verification()
    lm.ecrire_cache(res)
    n = lm.nombre(res)
    print(f"{n} mise(s) à jour disponible(s)" + (f" — {res['erreur']}" if res.get("erreur") else ""))
    if n == 0:
        return 0
    if envoyer_instance("rafraichir"):
        return 0
    # Unité séparée : survit à la fin du service oneshot.
    exe = shutil.which("exolyx-maj")
    cmd = [exe, "--zone"] if exe else [sys.executable, str(Path(__file__).resolve()), "--zone"]
    if shutil.which("systemd-run"):
        r = subprocess.run(["systemd-run", "--user", "--collect", "--quiet",
                            "--unit=exolyx-maj-zone", *cmd],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0:
            return 0
    subprocess.Popen(cmd, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
from PyQt6.QtCore import (QObject, QProcess, QUrl, pyqtProperty, pyqtSignal,  # noqa: E402
                          pyqtSlot)
from PyQt6.QtGui import QAction, QFont, QIcon  # noqa: E402
from PyQt6.QtNetwork import QLocalServer  # noqa: E402
from PyQt6 import sip  # noqa: E402
from PyQt6.QtQml import QQmlApplicationEngine  # noqa: E402
from PyQt6.QtQuick import QQuickWindow  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon  # noqa: E402

PALETTES = {
    True: {"accent": "#A8D479", "accentClair": "#BDD479", "accentFroid": "#8DD479",
           "fond": "#0D1310", "surface": "#141C17", "surfaceHaute": "#1C2620",
           "bordure": "#2A362E", "texte": "#E6EFE1", "texteDoux": "#97A893",
           "erreur": "#E5766B", "attention": "#E8C26A", "info": "#79C2D4",
           "surAccent": "#0D1310", "accentVoile": "#24A8D479", "attentionVoile": "#22E8C26A",
           "infoVoile": "#1A79C2D4", "journal": "#0A0F0C"},
    False: {"accent": "#5E9B2E", "accentClair": "#7DB547", "accentFroid": "#4E8F3A",
            "fond": "#F4F8F1", "surface": "#FFFFFF", "surfaceHaute": "#E9F0E4",
            "bordure": "#D3DECB", "texte": "#16201A", "texteDoux": "#5B6B57",
            "erreur": "#C2453A", "attention": "#A87A12", "info": "#2F7F94",
            "surAccent": "#FFFFFF", "accentVoile": "#265E9B2E", "attentionVoile": "#22A87A12",
            "infoVoile": "#1A2F7F94", "journal": "#F9FBF7"},
}
MESSAGES_FIN = {
    2: "Requête refusée par l'outil de mise à jour.",
    3: "Droits administrateur requis.",
    4: "Une autre installation est en cours. Réessayez dans un instant.",
    126: "Authentification annulée.",
    127: "Authentification refusée.",
}


def theme_sombre() -> bool:
    chemin = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                          "kdeglobals")
    try:
        groupe = None
        for ligne in Path(chemin).read_text(encoding="utf-8", errors="replace").splitlines():
            ligne = ligne.strip()
            if ligne.startswith("["):
                groupe = ligne
            elif groupe == "[General]" and ligne.startswith("ColorScheme="):
                return "Clair" not in ligne
    except OSError:
        pass
    return True


class Controleur(QObject):
    etatChange = pyqtSignal()
    tacheChange = pyqtSignal()
    journalChange = pyqtSignal()
    instantanesChange = pyqtSignal()
    afficherDemande = pyqtSignal()
    _resultatPret = pyqtSignal(dict)

    def __init__(self, simulation: bool):
        super().__init__()
        self._simulation = simulation
        self._sombre = theme_sombre()
        self._etat = "verification"
        self._res: dict = {}
        self._occupe = False
        self._progression = 0.0
        self._libelle = ""
        self._message = ""
        self._journal: list[str] = []
        self._deplie = False
        self._redemarrage: list[str] = []
        self._instantanes = ""
        self._tampon = ""
        self._suivi: lm.ProgressionPacman | None = None
        self._resultatPret.connect(self._appliquer_resultat)

    # ---- propriétés -----------------------------------------------------
    @pyqtProperty(bool, constant=True)
    def simulation(self):
        return self._simulation

    @pyqtProperty("QVariantMap", constant=True)
    def palette(self):
        return PALETTES[self._sombre]

    @pyqtProperty(bool, constant=True)
    def sombre(self):
        return self._sombre

    @pyqtProperty(str, constant=True)
    def logo(self):
        return QUrl.fromLocalFile(lm.chemin_logo()).toString() if lm.chemin_logo() else ""

    @pyqtProperty(str, notify=etatChange)
    def etat(self):
        """verification | disponible | ajour | erreur | termine"""
        return self._etat

    @pyqtProperty(list, notify=etatChange)
    def majs(self):
        lignes = []
        for src in ("pacman", "flatpak"):
            for m in self._res.get(src, []):
                lignes.append({
                    "nom": m["nom"], "ancienne": m["ancienne"], "nouvelle": m["nouvelle"],
                    "taille": lm.formater_taille(m.get("taille", 0)),
                    "section": "Système" if src == "pacman" else "Applications Flatpak",
                    "redemarrage": bool(m.get("redemarrage")),
                })
        return lignes

    @pyqtProperty(int, notify=etatChange)
    def nombre(self):
        return lm.nombre(self._res)

    @pyqtProperty(str, notify=etatChange)
    def resume(self):
        n = self.nombre
        if self._etat == "verification":
            return "Recherche des mises à jour…"
        if self._etat == "erreur":
            return self._res.get("erreur") or "La vérification a échoué."
        if self._etat == "termine":
            return "Mise à jour terminée."
        if n == 0:
            return "Votre système est à jour."
        total = sum(m.get("taille", 0) for s in ("pacman", "flatpak") for m in self._res.get(s, []))
        txt = f"{n} mise{'s' if n > 1 else ''} à jour disponible{'s' if n > 1 else ''}"
        return txt + (f" · {lm.formater_taille(total)} à télécharger" if total else "")

    @pyqtProperty(str, notify=etatChange)
    def derniereVerification(self):
        d = self._res.get("date")
        try:
            return "Dernière vérification : " + datetime.fromisoformat(d).strftime("%d/%m/%Y à %H:%M")
        except (TypeError, ValueError):
            return ""

    @pyqtProperty(bool, notify=etatChange)
    def redemarrageRequis(self):
        return bool(self._redemarrage)

    @pyqtProperty(str, notify=etatChange)
    def paquetsRedemarrage(self):
        return ", ".join(self._redemarrage)

    @pyqtProperty(bool, notify=etatChange)
    def redemarrageAnnonce(self):
        """Une mise à jour en attente nécessitera un redémarrage."""
        return any(m.get("redemarrage") for m in self._res.get("pacman", []))

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
    def message(self):
        return self._message

    @pyqtProperty(str, notify=journalChange)
    def journal(self):
        return "\n".join(self._journal)

    @pyqtProperty(bool, notify=journalChange)
    def journalDeplie(self):
        return self._deplie

    @journalDeplie.setter
    def journalDeplie(self, v):
        self._deplie = bool(v)
        self.journalChange.emit()

    @pyqtProperty(str, notify=instantanesChange)
    def instantanes(self):
        return self._instantanes

    def _journaliser(self, texte: str):
        self._journal.extend(texte.splitlines() or [""])
        del self._journal[:-3000]
        self.journalChange.emit()

    # ---- vérification ---------------------------------------------------------
    @pyqtSlot()
    def verifier(self):
        if self._occupe:
            return
        self._etat = "verification"
        self.etatChange.emit()

        def travail():
            try:
                res = resultat_verification()
            except Exception as e:  # noqa: BLE001 — affiché à l'utilisateur
                res = {"pacman": [], "flatpak": [], "erreur": str(e)}
            self._resultatPret.emit(res)
        threading.Thread(target=travail, daemon=True).start()

    def charger(self, res: dict):
        """Applique un résultat (cache, fixture ou vérification)."""
        self._appliquer_resultat(res)

    def _appliquer_resultat(self, res: dict):
        self._res = res
        if not self._simulation:
            lm.ecrire_cache(res)
        if res.get("erreur") and lm.nombre(res) == 0:
            self._etat = "erreur"
        else:
            self._etat = "disponible" if lm.nombre(res) else "ajour"
        self.etatChange.emit()

    # ---- mise à jour --------------------------------------------------------
    @pyqtSlot()
    def toutMettreAJour(self):
        if self._occupe or self.nombre == 0:
            return
        self._occupe, self._progression, self._message = True, 0.0, ""
        self._a_redemarrer = [m["nom"] for m in self._res.get("pacman", []) if m.get("redemarrage")]
        self._suivi = lm.ProgressionPacman()
        self.tacheChange.emit()
        if self._res.get("pacman"):
            self._libelle = "Demande d'autorisation…"
            self.tacheChange.emit()
            if self._simulation:
                prog, args = sys.executable, [str(ICI / "helper" / "exolyx-maj-helper"),
                                              "mettre-a-jour", "--simulation"]
            else:
                prog, args = "pkexec", [lm.HELPER, "mettre-a-jour"]
            self._lancer(prog, args, self._fin_pacman)
        else:
            self._lancer_flatpak()

    def _poids_pacman(self) -> float:
        return 0.85 if self._res.get("flatpak") else 1.0

    def _lancer(self, prog, args, fin):
        self._journaliser(f"— {datetime.now():%H:%M:%S} {prog} {' '.join(args)}")
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self._lire(p))
        p.finished.connect(lambda code, _s: fin(code, p))
        p.errorOccurred.connect(lambda e: e == QProcess.ProcessError.FailedToStart and fin(127, p))
        self._proc = p
        p.start(prog, args)

    def _lire(self, p: QProcess):
        self._tampon += bytes(p.readAllStandardOutput()).decode(errors="replace")
        *lignes, self._tampon = self._tampon.split("\n")
        for l in lignes:
            self.traiter_ligne(l)

    def traiter_ligne(self, ligne: str):
        if ligne.startswith("@@FIN"):
            return
        self._journaliser(ligne)
        if self._suivi:
            avant = self._suivi.valeur
            v = self._suivi.lire(ligne)
            if v != avant or self._suivi.texte != self._libelle:
                self._progression = max(self._progression, v * self._poids_pacman())
                self._libelle = self._suivi.texte
                self.tacheChange.emit()

    def _fin_pacman(self, code: int, p: QProcess):
        if self._tampon:
            self.traiter_ligne(self._tampon)
            self._tampon = ""
        p.deleteLater()
        if code != 0:
            self._terminer(False, MESSAGES_FIN.get(
                code, f"La mise à jour a échoué (code {code}). Consultez le journal."))
            return
        self._progression = self._poids_pacman()
        self.tacheChange.emit()
        if self._res.get("flatpak"):
            self._lancer_flatpak()
        else:
            self._terminer(True)

    def _lancer_flatpak(self):
        self._libelle = "Mise à jour des applications Flatpak…"
        self.tacheChange.emit()
        if self._simulation:
            self._journaliser("[simulation] flatpak update -y --noninteractive")
            self._terminer(True)
            return
        self._suivi = None
        self._lancer("flatpak", ["update", "-y", "--noninteractive"],
                     lambda code, p: (p.deleteLater(), self._terminer(
                         code == 0, "" if code == 0 else "La mise à jour Flatpak a échoué.")))

    def _terminer(self, ok: bool, message: str = ""):
        self._occupe = False
        if ok:
            self._progression = 1.0
            self._redemarrage = list(self._a_redemarrer)
            if not self._simulation and not self._redemarrage and lm.noyau_remplace():
                self._redemarrage = ["noyau"]
            self._message = "Mise à jour terminée." + (
                " Un redémarrage est nécessaire." if self._redemarrage else "")
            self._libelle = self._message
            self._res = {**self._res, "pacman": [], "flatpak": [],
                         "date": datetime.now().isoformat(timespec="seconds")}
            if not self._simulation:
                lm.ecrire_cache(self._res)
            self._etat = "termine"
        else:
            self._message = self._libelle = message
            self._deplie = True
            self.journalChange.emit()
        self.tacheChange.emit()
        self.etatChange.emit()

    @pyqtSlot()
    def redemarrer(self):
        if self._simulation:
            self._journaliser("[simulation] redémarrage")
            return
        for cmd in (["qdbus6", "org.kde.LogoutPrompt", "/LogoutPrompt", "promptReboot"],
                    ["systemctl", "reboot"]):
            if shutil.which(cmd[0]) and QProcess.execute(cmd[0], cmd[1:]) == 0:
                return

    # ---- instantanés ---------------------------------------------------------
    @pyqtSlot()
    def chargerInstantanes(self):
        if self._simulation or not shutil.which("snapper"):
            self._instantanes = os.environ.get("EXOLYX_SNAPPER_SORTIE") or (
                "snapper n'est pas disponible sur ce système." if not self._simulation else "")
            self.instantanesChange.emit()
            return
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def fini(code, _s):
            sortie = bytes(p.readAll()).decode(errors="replace").strip()
            self._instantanes = sortie if code == 0 else (
                "Impossible de lister les instantanés.\n" + sortie)
            self.instantanesChange.emit()
            p.deleteLater()
        p.finished.connect(fini)
        p.start("snapper", ["list"])

    @pyqtSlot()
    def afficher(self):
        self.afficherDemande.emit()


class Application:
    """Fenêtre QML + icône de zone de notification + instance unique."""

    def __init__(self, zone: bool):
        self.app = QApplication(sys.argv[:1])
        self.app.setApplicationName("exolyx-maj")
        self.app.setApplicationDisplayName("Mises à jour")
        self.app.setDesktopFileName("exolyx-maj")
        self.app.setFont(QFont("Inter", 10))
        self.icone = QIcon(lm.chemin_logo()) if lm.chemin_logo() else QIcon.fromTheme("system-software-update")
        self.app.setWindowIcon(self.icone)
        self.app.setQuitOnLastWindowClosed(False)
        self.zone = zone
        self.ctrl = Controleur(os.environ.get("EXOLYX_SIMULATION") == "1")
        self.ctrl.afficherDemande.connect(self.afficher)
        self.ctrl.etatChange.connect(self._maj_zone)
        self.moteur: QQmlApplicationEngine | None = None
        self.notifie = -1
        self.serveur = QLocalServer()
        self.serveur.newConnection.connect(self._message_recu)
        if os.path.exists(chemin_socket()):
            QLocalServer.removeServer(chemin_socket())
        self.serveur.listen(chemin_socket())
        self.zone_icone = QSystemTrayIcon(self.icone)
        menu = QMenu()
        for texte, rappel in (("Afficher les mises à jour", self.afficher),
                              ("Vérifier maintenant", self.ctrl.verifier),
                              ("Quitter", self.app.quit)):
            a = QAction(texte, menu)
            a.triggered.connect(rappel)
            menu.addAction(a)
        self._menu = menu
        self.zone_icone.setContextMenu(menu)
        self.zone_icone.activated.connect(
            lambda r: r == QSystemTrayIcon.ActivationReason.Trigger and self.afficher())

    def fenetre(self):
        if self.moteur is None:
            self.moteur = QQmlApplicationEngine()
            self.moteur.rootContext().setContextProperty("ctrl", self.ctrl)
            self.moteur.load(QUrl.fromLocalFile(str(ICI / "qml" / "Main.qml")))
            if not self.moteur.rootObjects():
                raise SystemExit(1)
            self._fenetre = sip.cast(self.moteur.rootObjects()[0], QQuickWindow)
            self._fenetre.closing.connect(self._fermee)
        return self._fenetre

    def afficher(self):
        f = self.fenetre()
        f.show()
        f.raise_()
        f.requestActivate()

    def _fermee(self, *_):
        if not self.zone_icone.isVisible() and not self.ctrl.occupe:
            self.app.quit()

    def _message_recu(self):
        c = self.serveur.nextPendingConnection()

        def lire():
            msg = bytes(c.readAll()).decode(errors="replace").strip()
            if msg == "afficher":
                self.afficher()
            elif msg == "rafraichir":
                self.ctrl.charger(lm.lire_cache()) if lm.lire_cache() else self.ctrl.verifier()
            c.disconnectFromServer()
        c.readyRead.connect(lire)

    def _maj_zone(self):
        n = self.ctrl.nombre
        visible = n > 0 and QSystemTrayIcon.isSystemTrayAvailable()
        self.zone_icone.setToolTip(f"Mises à jour ExoLyx — {n} disponible{'s' if n > 1 else ''}")
        self.zone_icone.setVisible(visible)
        if n > 0 and self.zone and n != self.notifie:
            self.notifie = n
            self._notifier(n)
        if self.zone and n == 0 and self.ctrl.etat in ("ajour", "termine") and \
                (self.moteur is None or not self.fenetre().isVisible()):
            self.app.quit()

    def _notifier(self, n: int):
        if not shutil.which("notify-send"):
            if self.zone_icone.isVisible():
                self.zone_icone.showMessage("Mises à jour disponibles",
                                            f"{n} mise{'s' if n > 1 else ''} à jour pour ExoLyx.")
            return
        p = QProcess(self.app)
        args = ["--app-name=Mises à jour ExoLyx", "--icon=system-software-update",
                "--action=maj=Mettre à jour", "--wait",
                "Mises à jour disponibles",
                f"{n} mise{'s' if n > 1 else ''} à jour pour ExoLyx. "
                "Un instantané de sécurité sera créé automatiquement."]

        def fini(*_):
            if bytes(p.readAllStandardOutput()).decode().strip() == "maj":
                self.afficher()
            p.deleteLater()
        p.finished.connect(fini)
        p.start("notify-send", args)

    def executer(self) -> int:
        cache = lm.lire_cache()
        if self.zone and cache and lm.nombre(cache):
            self.ctrl.charger(cache)
        else:
            self.ctrl.verifier()
        if not self.zone:
            self.afficher()
        return self.app.exec()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="exolyx-maj", description="Mises à jour ExoLyx")
    parser.add_argument("--verifier", action="store_true", help="vérification silencieuse")
    parser.add_argument("--zone", action="store_true", help="icône de zone de notification")
    args = parser.parse_args(argv)
    if args.verifier:
        return mode_verifier()
    if envoyer_instance("rafraichir" if args.zone else "afficher"):
        return 0
    return Application(zone=args.zone).executer()


if __name__ == "__main__":
    sys.exit(main())

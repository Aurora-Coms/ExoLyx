#!/usr/bin/env python3
"""Banc de test du thème SDDM « exolyx » (sans SDDM).

Charge exolyx/Main.qml dans une QQuickView hors écran, avec des objets
factices injectés en contexte (sddm, userModel, sessionModel, config,
keyboard, primaryScreen), simule les interactions et enregistre des
captures pour chaque état :

    QT_QPA_PLATFORM=offscreen python3 src/sddm/tests/banc.py --sortie DOSSIER

Hors écran (offscreen), Qt Quick utilise le rendu logiciel : la mise en page
et l'absence d'erreurs QML sont vérifiées, mais MultiEffect (flou du fond,
masque circulaire de l'avatar) n'est pas dessiné. Pour des captures fidèles
(OpenGL via Mesa/llvmpipe) :

    QT_QPA_PLATFORM=xcb xvfb-run -a -s "-screen 0 2000x1200x24" \
        python3 src/sddm/tests/banc.py --sortie DOSSIER

Captures : sddm-<L>x<H>-{repos,actif,erreur,connexion,plusieurs}.png
Code de retour ≠ 0 si le QML émet le moindre avertissement ou erreur.
"""

import argparse
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import (QAbstractListModel, QByteArray, QModelIndex, QObject, Qt,
                          QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot, QSize)
from PyQt6.QtCore import QEvent, QPointF
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QGuiApplication, QImage, QPainter, QColor, QRadialGradient, QFont
from PyQt6.QtQml import QQmlPropertyMap
from PyQt6.QtQuick import QQuickView
from PyQt6.QtTest import QTest

ICI = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(os.path.dirname(ICI), "exolyx")


# ------------------------------------------------------------------ factices
class Sddm(QObject):
    loginFailed = pyqtSignal()
    loginSucceeded = pyqtSignal()
    informationMessage = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.reussite = False
        self.appels = []

    @pyqtProperty(str, constant=True)
    def hostName(self): return "exolyx-pc"

    @pyqtProperty(bool, constant=True)
    def canSuspend(self): return True

    @pyqtProperty(bool, constant=True)
    def canReboot(self): return True

    @pyqtProperty(bool, constant=True)
    def canPowerOff(self): return True

    @pyqtProperty(bool, constant=True)
    def canHibernate(self): return False

    @pyqtSlot(str, str, int)
    def login(self, utilisateur, mdp, session):
        self.appels.append((utilisateur, mdp, session))
        QTimer.singleShot(250, self.loginSucceeded.emit if self.reussite else self.loginFailed.emit)

    @pyqtSlot()
    def suspend(self): self.appels.append("suspend")

    @pyqtSlot()
    def reboot(self): self.appels.append("reboot")

    @pyqtSlot()
    def powerOff(self): self.appels.append("powerOff")


class Modele(QAbstractListModel):
    def __init__(self, roles, lignes, dernier=0):
        super().__init__()
        self._roles = roles
        self._lignes = lignes
        self._dernier = dernier

    def rowCount(self, parent=QModelIndex()):
        return len(self._lignes)

    def data(self, index, role):
        r = role - Qt.ItemDataRole.UserRole - 1
        if 0 <= r < len(self._roles) and index.isValid():
            return self._lignes[index.row()].get(self._roles[r], "")
        return None

    def roleNames(self):
        return {Qt.ItemDataRole.UserRole + 1 + i: QByteArray(n.encode()) for i, n in enumerate(self._roles)}

    @pyqtProperty(int, constant=True)
    def lastIndex(self): return self._dernier

    @pyqtProperty(int, constant=True)
    def count(self): return len(self._lignes)


class Disposition(QObject):
    def __init__(self, court, long):
        super().__init__()
        self._c, self._l = court, long

    @pyqtProperty(str, constant=True)
    def shortName(self): return self._c

    @pyqtProperty(str, constant=True)
    def longName(self): return self._l


class Clavier(QObject):
    capsLockChanged = pyqtSignal()
    currentLayoutChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._maj = False
        self._dispo = [Disposition("fr", "Français (AZERTY)"), Disposition("us", "Anglais (US)")]
        self._courante = 0

    @pyqtProperty(bool, notify=capsLockChanged)
    def capsLock(self): return self._maj

    @capsLock.setter
    def capsLock(self, v):
        self._maj = v
        self.capsLockChanged.emit()

    @pyqtProperty(bool, constant=True)
    def numLock(self): return True

    @pyqtProperty(list, constant=True)
    def layouts(self): return self._dispo

    @pyqtProperty(int, notify=currentLayoutChanged)
    def currentLayout(self): return self._courante

    @currentLayout.setter
    def currentLayout(self, v):
        self._courante = v
        self.currentLayoutChanged.emit()


class Ecran(QObject):
    def __init__(self, w, h):
        super().__init__()
        self._w, self._h = w, h

    @pyqtProperty(int, constant=True)
    def width(self): return self._w

    @pyqtProperty(int, constant=True)
    def height(self): return self._h


def avatar_factice(chemin):
    """Petite « photo » d'utilisateur pour tester le masque circulaire."""
    img = QImage(256, 256, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    g = QRadialGradient(90, 80, 220)
    g.setColorAt(0, QColor("#F2C9A0"))
    g.setColorAt(1, QColor("#5C7FA8"))
    p.fillRect(0, 0, 256, 256, g)
    p.setBrush(QColor("#3A2A20")); p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(78, 40, 100, 110)
    p.setBrush(QColor("#E8B48C"))
    p.drawEllipse(88, 62, 80, 92)
    p.setBrush(QColor("#2F5E8C"))
    p.drawEllipse(40, 170, 176, 150)
    p.end()
    img.save(chemin)


# ------------------------------------------------------------------ banc
_VIVANTS = []  # garde les factices en vie jusqu'à la fin (évite des erreurs à la destruction)


class Banc:
    def __init__(self, app, w, h, sortie, utilisateurs, maj=False):
        _VIVANTS.append(self)
        self.app, self.w, self.h, self.sortie = app, w, h, sortie
        self.messages = []
        self.view = QQuickView()
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.view.resize(w, h)
        moteur = self.view.engine()
        moteur.warnings.connect(lambda ws: self.messages.extend(x.toString() for x in ws))

        self.sddm = Sddm()
        self.clavier = Clavier()
        self.clavier.capsLock = maj
        self.config = QQmlPropertyMap()
        self.config.insert("background", "images/fond.png")
        self.config.insert("message", "Bienvenue sur ExoLyx")
        self.config.insert("police", "Inter")
        self.users = Modele(["name", "realName", "homeDir", "icon", "needsPassword"], utilisateurs)
        self.sessions = Modele(["name", "comment", "file"], [
            {"name": "Plasma (Wayland)", "file": "plasma.desktop"},
            {"name": "Plasma (X11)", "file": "plasmax11.desktop"},
        ])
        ctx = self.view.rootContext()
        for nom, obj in (("sddm", self.sddm), ("userModel", self.users), ("sessionModel", self.sessions),
                         ("config", self.config), ("keyboard", self.clavier),
                         ("primaryScreen", Ecran(w, h))):
            ctx.setContextProperty(nom, obj)
        self.view.setSource(QUrl.fromLocalFile(os.path.join(THEME, "Main.qml")))
        if self.view.status() != QQuickView.Status.Ready:
            for e in self.view.errors():
                self.messages.append(e.toString())
        self.view.show()
        self.view.requestActivate()
        QTest.qWait(200)
        self.racine = self.view.rootObject()
        if self.racine is not None:
            self.racine.forceActiveFocus()

    def attendre(self, ms):
        QTest.qWait(ms)

    def capture(self, nom):
        img = self.view.grabWindow()
        chemin = os.path.join(self.sortie, f"sddm-{self.w}x{self.h}-{nom}.png")
        img.save(chemin)
        print("  capture :", chemin)

    def _envoyer(self, k, texte=""):
        for t in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            QGuiApplication.sendEvent(self.view, QKeyEvent(t, k, Qt.KeyboardModifier.NoModifier, texte))
        self.app.processEvents()

    def taper(self, texte):
        for c in texte:
            k = Qt.Key(ord(c.upper())) if c.isascii() and c.isalnum() else Qt.Key.Key_unknown
            self._envoyer(k, c)

    def cliquer(self, x, y):
        pos = QPointF(x, y)
        for t in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            QGuiApplication.sendEvent(self.view, QMouseEvent(
                t, pos, self.view.mapToGlobal(pos), Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton if t == QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier))
        self.app.processEvents()

    def touche(self, k):
        self._envoyer(k)


def scenario(app, w, h, sortie, avatar):
    un = [{"name": "camille", "realName": "Camille Martin", "icon": avatar, "needsPassword": True}]
    b = Banc(app, w, h, sortie, un)
    if b.racine is None:
        return b.messages
    b.attendre(700)
    b.capture("repos")

    # activation par une touche : la lettre tapée va dans le champ
    b.taper("m")
    b.taper("otdepasse")
    b.attendre(900)
    b.capture("actif")
    assert b.racine.property("actif") is True, "le thème devrait être actif"

    # erreur : Entrée → échec → tremblement + message
    b.touche(Qt.Key.Key_Return)
    b.attendre(250 + 110)   # pendant le tremblement
    b.capture("erreur-secousse")
    b.attendre(700)
    b.capture("erreur")
    assert b.sddm.appels and b.sddm.appels[-1] == ("camille", "motdepasse", 0), b.sddm.appels
    assert b.racine.property("erreur") is True

    # connexion réussie : les orbites accélèrent
    b.sddm.reussite = True
    b.taper("bon")
    b.touche(Qt.Key.Key_Enter)
    b.attendre(700)
    b.capture("connexion")
    msgs = list(b.messages)
    b.view.close()

    # plusieurs utilisateurs, sans avatar, Verr. Maj. activée, menu des sessions ouvert
    plusieurs = [
        {"name": "camille", "realName": "Camille Martin", "icon": "", "needsPassword": True},
        {"name": "lea", "realName": "Léa Dubois", "icon": "/nexiste/pas.png", "needsPassword": True},
        {"name": "invite", "realName": "", "icon": "", "needsPassword": True},
    ]
    b2 = Banc(app, w, h, sortie, plusieurs, maj=True)
    b2.attendre(300)
    b2.cliquer(w / 2, h / 3)
    b2.attendre(800)
    b2.capture("plusieurs")
    # ouvre le menu des sessions (bouton en bas à gauche)
    s = b2.racine.property("s")
    b2.cliquer(80 * s, h - 55 * s)
    b2.attendre(400)
    b2.capture("sessions")
    msgs += b2.messages
    b2.view.close()
    return msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default=os.environ.get("TMPDIR", "/tmp"))
    ap.add_argument("--tailles", default="1920x1080,1366x768")
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)

    app = QGuiApplication(sys.argv)
    app.setFont(QFont("Inter"))
    avatar = os.path.join(a.sortie, "avatar-factice.png")
    avatar_factice(avatar)

    problemes = []
    for t in a.tailles.split(","):
        w, h = (int(x) for x in t.split("x"))
        print(f"== {w}×{h}")
        problemes += scenario(app, w, h, a.sortie, avatar)

    # l'avatar inexistant (/nexiste/pas.png) produit un avertissement attendu de Image
    problemes = [m for m in problemes if "/nexiste/pas.png" not in m]
    if problemes:
        print("\nAVERTISSEMENTS / ERREURS QML :")
        for m in problemes:
            print("  ", m)
        return 1
    print("\nAucune erreur QML.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

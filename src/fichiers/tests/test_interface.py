"""Chargement de l'interface QML hors écran : aucune erreur ni avertissement QML."""
import os
import shutil
import sys
import tempfile
import unittest

import aide  # noqa: F401


class TestInterface(unittest.TestCase):
    def test_chargement_sans_erreur(self):
        try:
            from PyQt6.QtQuick import QQuickWindow  # noqa: F401
        except ImportError as e:  # pragma: no cover
            self.skipTest(f"QtQuick indisponible : {e}")
        from PyQt6.QtCore import QEventLoop, QTimer, qInstallMessageHandler
        maison = tempfile.mkdtemp(prefix="fichiers-ui-")
        ancien = os.environ.get("HOME")
        env = {k: os.environ.pop(k, None) for k in ("XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME")}
        os.environ["HOME"] = maison
        for d in ("Documents", "Images", "Documents/Projets"):
            os.makedirs(os.path.join(maison, d))
        with open(os.path.join(maison, "Documents", "note.txt"), "w") as f:
            f.write("note")
        messages = []
        qInstallMessageHandler(lambda mode, ctx, msg: messages.append(msg))
        try:
            import main
            app, moteur, ctrl = main.creer_application(["exolyx-fichiers"], demarrer_index=False)
            self.assertTrue(moteur.rootObjects(), "Main.qml n'a pas pu être chargé")
            fen = moteur.rootObjects()[0]

            def attendre(ms=300):
                boucle = QEventLoop()
                QTimer.singleShot(ms, boucle.quit)
                boucle.exec()

            attendre()
            # parcours des différentes vues
            for vue in ("grille", "liste"):
                ctrl.vue = vue
                ctrl.naviguer(os.path.join(maison, "Documents"))
                attendre()
                ctrl.onglet.modele.toutSelectionner()
                ctrl.apercuVisible = True
                attendre()
            for cible in ("corbeille:", "parametres:", "accueil:"):
                ctrl.naviguer(cible)
                attendre()
            ctrl.nouvelOnglet(os.path.join(maison, "Images"))
            ctrl.naviguer(maison)
            ctrl.rechercher("note")
            attendre(600)
            self.assertEqual(ctrl.onglet.modele.count, 1)
            self.assertEqual(len(ctrl.onglets), 2)
            ctrl.modeTheme = "clair"
            attendre()
            image = fen.grabWindow()
            self.assertFalse(image.isNull())
            problemes = [m for m in messages if ".qml" in m or "QML" in m or "Error" in m]
            self.assertEqual(problemes, [])
        finally:
            qInstallMessageHandler(None)
            os.environ["HOME"] = ancien or ""
            for k, v in env.items():
                if v is not None:
                    os.environ[k] = v
            shutil.rmtree(maison, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

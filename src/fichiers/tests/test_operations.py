import os
import threading
import unittest
from unittest import mock

from aide import TestAvecDossier, xattr_disponible

import etiquettes
import operations
from operations import IGNORER, REMPLACER, RENOMMER, Tache, nom_unique, separer_extension


class TestNomUnique(TestAvecDossier):
    def test_libre(self):
        self.assertEqual(nom_unique(self.tmp, "a.txt"), "a.txt")

    def test_numerotation(self):
        self.ecrire("a.txt")
        self.assertEqual(nom_unique(self.tmp, "a.txt"), "a (2).txt")
        self.ecrire("a (2).txt")
        self.assertEqual(nom_unique(self.tmp, "a.txt"), "a (3).txt")

    def test_suite_d_un_nom_numerote(self):
        self.ecrire("photo (4).png")
        self.assertEqual(nom_unique(self.tmp, "photo (4).png"), "photo (5).png")

    def test_extension_double_et_cache(self):
        self.ecrire("sauvegarde.tar.gz")
        self.ecrire(".bashrc")
        self.ecrire("Dossier/x")
        self.assertEqual(nom_unique(self.tmp, "sauvegarde.tar.gz"), "sauvegarde (2).tar.gz")
        self.assertEqual(nom_unique(self.tmp, ".bashrc"), ".bashrc (2)")
        self.assertEqual(nom_unique(self.tmp, "Dossier"), "Dossier (2)")
        self.assertEqual(separer_extension("archive.TAR.GZ"), ("archive", ".TAR.GZ"))


class TestCopieDeplacement(TestAvecDossier):
    def setUp(self):
        super().setUp()
        self.src = os.path.join(self.tmp, "src")
        self.dst = os.path.join(self.tmp, "dst")
        os.makedirs(self.src)
        os.makedirs(self.dst)

    def test_copie_simple_avec_progression(self):
        f = self.ecrire("src/gros.bin", os.urandom(3 * 1024 * 1024 + 17))
        d = self.ecrire("src/dossier/sous/a.txt", "A")
        os.symlink("a.txt", os.path.join(self.src, "dossier", "sous", "lien"))
        etapes = []
        t = Tache("copier", [f, os.path.dirname(os.path.dirname(d))], self.dst,
                  progression=lambda fait, total, c: etapes.append((fait, total)))
        self.assertTrue(t.executer())
        self.assertEqual(os.path.getsize(os.path.join(self.dst, "gros.bin")), 3 * 1024 * 1024 + 17)
        self.assertEqual(self.lire(os.path.join(self.dst, "dossier", "sous", "a.txt")), "A")
        self.assertEqual(os.readlink(os.path.join(self.dst, "dossier", "sous", "lien")), "a.txt")
        self.assertTrue(os.path.exists(f), "la source d'une copie reste en place")
        self.assertEqual(etapes[-1][0], etapes[-1][1])
        self.assertEqual(t.total, 3 * 1024 * 1024 + 18)
        self.assertFalse([n for n in os.listdir(self.dst) if n.endswith(".exolyx-partiel")])

    def test_copie_sur_place_duplique(self):
        f = self.ecrire("src/note.txt", "n")
        t = Tache("copier", [f], self.src)
        t.executer()
        self.assertEqual(sorted(os.listdir(self.src)), ["note (2).txt", "note.txt"])

    def test_conflit_renommer(self):
        f = self.ecrire("src/a.txt", "nouveau")
        self.ecrire("dst/a.txt", "ancien")
        Tache("copier", [f], self.dst, politique=RENOMMER).executer()
        self.assertEqual(self.lire(os.path.join(self.dst, "a.txt")), "ancien")
        self.assertEqual(self.lire(os.path.join(self.dst, "a (2).txt")), "nouveau")

    def test_conflit_ignorer(self):
        f = self.ecrire("src/a.txt", "nouveau")
        self.ecrire("dst/a.txt", "ancien")
        t = Tache("copier", [f], self.dst, politique=IGNORER)
        t.executer()
        self.assertEqual(self.lire(os.path.join(self.dst, "a.txt")), "ancien")
        self.assertEqual(os.listdir(self.dst), ["a.txt"])
        self.assertEqual(t.fait, t.total)

    def test_conflit_remplacer_et_fusion_de_dossiers(self):
        self.ecrire("src/D/a.txt", "nouveau")
        self.ecrire("src/D/b.txt", "b")
        self.ecrire("dst/D/a.txt", "ancien")
        self.ecrire("dst/D/garde.txt", "g")
        Tache("copier", [os.path.join(self.src, "D")], self.dst, politique=REMPLACER).executer()
        self.assertEqual(sorted(os.listdir(os.path.join(self.dst, "D"))), ["a.txt", "b.txt", "garde.txt"])
        self.assertEqual(self.lire(os.path.join(self.dst, "D", "a.txt")), "nouveau")

    def test_conflit_demande_avec_pour_tous(self):
        for n in ("a", "b", "c"):
            self.ecrire(f"src/{n}.txt", "nouveau")
            self.ecrire(f"dst/{n}.txt", "ancien")
        questions = []

        def demander(src, dst):
            questions.append(os.path.basename(src))
            return IGNORER, True   # « faire de même pour les suivants »

        t = Tache("copier", [os.path.join(self.src, n + ".txt") for n in "abc"], self.dst, conflit=demander)
        t.executer()
        self.assertEqual(questions, ["a.txt"], "une seule question grâce à « pour tous »")
        for n in "abc":
            self.assertEqual(self.lire(os.path.join(self.dst, n + ".txt")), "ancien")

    def test_conflit_annuler(self):
        self.ecrire("src/a.txt", "nouveau")
        self.ecrire("src/b.txt", "b")
        self.ecrire("dst/a.txt", "ancien")
        t = Tache("copier", [os.path.join(self.src, "a.txt"), os.path.join(self.src, "b.txt")], self.dst,
                  conflit=lambda s, d: ("annuler", False))
        self.assertFalse(t.executer())
        self.assertFalse(os.path.exists(os.path.join(self.dst, "b.txt")))

    def test_dossier_dans_lui_meme(self):
        self.ecrire("src/D/a.txt")
        d = os.path.join(self.src, "D")
        os.makedirs(os.path.join(d, "sous"))
        t = Tache("copier", [d], os.path.join(d, "sous"))
        t.executer()
        self.assertEqual(len(t.erreurs), 1)
        self.assertFalse(os.path.exists(os.path.join(d, "sous", "D")))

    def test_deplacement_meme_systeme(self):
        f = self.ecrire("src/a.txt", "a")
        self.ecrire("src/D/b.txt", "b")
        t = Tache("deplacer", [f, os.path.join(self.src, "D")], self.dst)
        self.assertTrue(t.executer())
        self.assertEqual(os.listdir(self.src), [])
        self.assertEqual(sorted(os.listdir(self.dst)), ["D", "a.txt"])
        self.assertEqual(t.total, 0, "un renommage ne compte pas d'octets")

    def test_deplacement_avec_conflit(self):
        f = self.ecrire("src/a.txt", "nouveau")
        self.ecrire("dst/a.txt", "ancien")
        Tache("deplacer", [f], self.dst, politique=RENOMMER).executer()
        self.assertFalse(os.path.exists(f))
        self.assertEqual(self.lire(os.path.join(self.dst, "a (2).txt")), "nouveau")

    def test_deplacement_entre_systemes_garde_les_ignores(self):
        # simule un autre système de fichiers : copie puis suppression élément par élément
        self.ecrire("src/D/a.txt", "nouveau")
        self.ecrire("src/D/b.txt", "b")
        self.ecrire("dst/D/a.txt", "ancien")
        # dossier en conflit : fusion ; fichier en conflit : ignoré
        choix = lambda s, d: (REMPLACER if os.path.isdir(s) else IGNORER, False)  # noqa: E731
        with mock.patch.object(operations, "meme_systeme", return_value=False):
            t = Tache("deplacer", [os.path.join(self.src, "D")], self.dst, conflit=choix)
            t.executer()
        self.assertEqual(self.lire(os.path.join(self.dst, "D", "a.txt")), "ancien")
        self.assertEqual(self.lire(os.path.join(self.dst, "D", "b.txt")), "b")
        self.assertEqual(os.listdir(os.path.join(self.src, "D")), ["a.txt"], "l'élément ignoré reste à la source")
        self.assertEqual(t.fait, t.total)

    def test_dossier_ignore_en_entier(self):
        self.ecrire("src/D/a.txt", "nouveau")
        self.ecrire("dst/D/b.txt", "b")
        Tache("copier", [os.path.join(self.src, "D")], self.dst, politique=IGNORER).executer()
        self.assertEqual(os.listdir(os.path.join(self.dst, "D")), ["b.txt"])

    def test_annulation(self):
        f = self.ecrire("src/gros.bin", os.urandom(4 * 1024 * 1024))
        t = Tache("copier", [f], self.dst)
        # annule dès le premier bloc copié
        t._progres = lambda force=False: t.annuler() if t.fait > 0 else None
        self.assertFalse(t.executer())
        self.assertEqual(os.listdir(self.dst), [], "pas de fichier partiel laissé derrière")

    def test_suppression_definitive(self):
        self.ecrire("src/D/a.txt")
        self.ecrire("src/D/E/b.txt")
        f = self.ecrire("src/c.txt")
        t = Tache("supprimer", [os.path.join(self.src, "D"), f])
        self.assertTrue(t.executer())
        self.assertEqual(os.listdir(self.src), [])
        self.assertEqual(t.fait, 5)

    def test_copie_conserve_les_etiquettes(self):
        if not xattr_disponible(self.tmp):
            self.skipTest("pas d'attributs étendus ici")
        f = self.ecrire("src/a.txt")
        etiquettes.ecrire(f, ["Travail"])
        Tache("copier", [f], self.dst).executer()
        self.assertEqual(etiquettes.lire(os.path.join(self.dst, "a.txt")), ["Travail"])

    def test_gestionnaire_qt(self):
        """Le gestionnaire exécute la tâche dans un thread et relaie le conflit à l'interface."""
        from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer
        app = QCoreApplication.instance() or QCoreApplication([])
        self.ecrire("src/a.txt", "nouveau")
        self.ecrire("dst/a.txt", "ancien")
        g = operations.GestionnaireOperations(corbeille=None)
        fini = []
        g.conflitDemande.connect(lambda ident, s, d: g.repondreConflit(ident, "renommer", False))
        g.tacheTerminee.connect(lambda type_, res: fini.append(res))
        g.lancer("copier", [os.path.join(self.src, "a.txt")], self.dst)
        boucle = QEventLoop()
        g.tacheTerminee.connect(lambda *_: boucle.quit())
        QTimer.singleShot(5000, boucle.quit)
        if not fini:
            boucle.exec()
        self.assertEqual(fini, [[os.path.join(self.dst, "a (2).txt")]])
        self.assertEqual(g.rowCount(), 1)
        self.assertFalse(g.actif)
        del app


if __name__ == "__main__":
    unittest.main()

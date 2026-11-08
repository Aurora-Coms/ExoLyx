import os
import threading
import unittest

from aide import TestAvecDossier

from recherche import Recherche, correspondance, normaliser, rechercher


class TestRecherche(TestAvecDossier):
    def setUp(self):
        super().setUp()
        self.racine = os.path.join(self.tmp, "r")
        for c in ("Été 2026/photo plage.jpg", "Été 2026/notes.txt", "projets/exolyx/README.md",
                  "projets/exolyx/src/fichiers.py", ".cache/plage-cachee.txt", "Plage.png"):
            self.ecrire("r/" + c)

    def noms(self, motif, **kw):
        return sorted(os.path.relpath(c, self.racine) for c in rechercher(self.racine, motif, **kw))

    def test_sous_chaine_insensible_casse_et_accents(self):
        self.assertEqual(self.noms("plage"), ["Plage.png", "Été 2026/photo plage.jpg"])
        self.assertEqual(self.noms("ete"), ["Été 2026"])
        self.assertEqual(normaliser("ÉtÉ"), "ete")

    def test_plusieurs_mots(self):
        self.assertEqual(self.noms("photo jpg"), ["Été 2026/photo plage.jpg"])

    def test_jokers(self):
        self.assertEqual(self.noms("*.py"), ["projets/exolyx/src/fichiers.py"])
        self.assertTrue(correspondance("readme.??")("README.md"))

    def test_caches(self):
        self.assertNotIn(".cache/plage-cachee.txt", self.noms("plage"))
        self.assertIn(".cache/plage-cachee.txt", self.noms("plage", caches=True))

    def test_dossiers_trouves_aussi(self):
        self.assertEqual(self.noms("exolyx"), ["projets/exolyx"])

    def test_motif_vide(self):
        self.assertEqual(self.noms("  "), [])

    def test_limite_et_annulation(self):
        for i in range(50):
            self.ecrire(f"r/lot/f{i}.txt")
        self.assertEqual(len(list(rechercher(self.racine, ".txt", limite=10))), 10)
        annule = threading.Event()
        gen = rechercher(self.racine, ".txt", annule=annule)
        next(gen)
        annule.set()
        self.assertEqual(list(gen), [])

    def test_liens_symboliques_non_suivis(self):
        os.symlink(self.racine, os.path.join(self.racine, "boucle"))
        self.assertEqual(self.noms("README"), ["projets/exolyx/README.md"])

    def test_thread(self):
        lots, fin = [], threading.Event()
        etat = {}
        r = Recherche(self.racine, "plage", lots.extend, lambda annulee: (etat.update(a=annulee), fin.set()))
        r.demarrer()
        self.assertTrue(fin.wait(5))
        self.assertFalse(etat["a"])
        self.assertEqual(len(lots), 2)


if __name__ == "__main__":
    unittest.main()

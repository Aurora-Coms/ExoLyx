import os
import unittest

from aide import TestAvecDossier, xattr_disponible

import etiquettes
from corbeille import Corbeille


class TestCorbeille(TestAvecDossier):
    def setUp(self):
        super().setUp()
        self.corb = Corbeille(os.path.join(self.tmp, "data", "Trash"), montages=False)

    def test_jeter_cree_files_et_trashinfo(self):
        f = self.ecrire("docs/mon fichier é.txt", "contenu")
        cible = self.corb.jeter(f)
        self.assertFalse(os.path.exists(f))
        self.assertEqual(cible, os.path.join(self.corb.principal, "files", "mon fichier é.txt"))
        info = os.path.join(self.corb.principal, "info", "mon fichier é.txt.trashinfo")
        texte = self.lire(info)
        self.assertTrue(texte.startswith("[Trash Info]\n"))
        self.assertIn("Path=" + f.replace(" ", "%20").replace("é", "%C3%A9"), texte)
        self.assertRegex(texte, r"DeletionDate=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d")
        self.assertEqual(oct(os.stat(os.path.join(self.corb.principal, "info")).st_mode & 0o777), "0o700")

    def test_noms_identiques(self):
        a = self.ecrire("x/a.txt", "1")
        self.corb.jeter(a)
        b = self.ecrire("y/a.txt", "2")
        self.corb.jeter(b)
        noms = sorted(os.listdir(os.path.join(self.corb.principal, "files")))
        self.assertEqual(noms, ["a.2.txt", "a.txt"])
        origines = sorted(e["origine"] for e in self.corb.lister())
        self.assertEqual(origines, sorted([a, b]))

    def test_lister_et_restaurer(self):
        d = self.ecrire("docs/D/b.txt", "b")
        dossier = os.path.dirname(d)
        self.corb.jeter(dossier)
        elements = self.corb.lister()
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["nom"], "D")
        self.assertEqual(elements[0]["origine"], dossier)
        restaure = self.corb.restaurer(elements[0]["chemin"])
        self.assertEqual(restaure, dossier)
        self.assertEqual(self.lire(d), "b")
        self.assertEqual(self.corb.lister(), [])
        self.assertTrue(self.corb.est_vide())

    def test_restaurer_quand_le_nom_est_pris(self):
        f = self.ecrire("docs/a.txt", "ancien")
        self.corb.jeter(f)
        self.ecrire("docs/a.txt", "nouveau")
        restaure = self.corb.restaurer(self.corb.lister()[0]["chemin"])
        self.assertEqual(os.path.basename(restaure), "a (2).txt")
        self.assertEqual(self.lire(restaure), "ancien")
        self.assertEqual(self.lire(f), "nouveau")

    def test_restaurer_dossier_d_origine_disparu(self):
        f = self.ecrire("docs/sous/a.txt", "a")
        self.corb.jeter(f)
        os.rmdir(os.path.dirname(f))
        restaure = self.corb.restaurer(self.corb.lister()[0]["chemin"])
        self.assertEqual(restaure, f)

    def test_etiquettes_conservees(self):
        if not xattr_disponible(self.tmp):
            self.skipTest("pas d'attributs étendus ici")
        f = self.ecrire("docs/a.txt", "a")
        etiquettes.ecrire(f, ["Travail", "Important"])
        cible = self.corb.jeter(f)
        self.assertEqual(etiquettes.lire(cible), ["Travail", "Important"])
        self.assertEqual(self.corb.lister()[0]["etiquettes"], ["Travail", "Important"])
        restaure = self.corb.restaurer(cible)
        self.assertEqual(etiquettes.lire(restaure), ["Travail", "Important"])

    def test_etiquettes_reprises_du_trashinfo(self):
        """Si l'attribut s'est perdu en route, le .trashinfo sert de copie de secours."""
        if not xattr_disponible(self.tmp):
            self.skipTest("pas d'attributs étendus ici")
        f = self.ecrire("docs/a.txt", "a")
        etiquettes.ecrire(f, ["Vacances"])
        cible = self.corb.jeter(f)
        os.removexattr(cible, etiquettes.ATTRIBUT)
        restaure = self.corb.restaurer(cible)
        self.assertEqual(etiquettes.lire(restaure), ["Vacances"])

    def test_supprimer_et_vider(self):
        for n in ("a", "b", "c"):
            self.corb.jeter(self.ecrire(f"docs/{n}.txt"))
        self.corb.jeter(os.path.dirname(self.ecrire("docs/D/x.txt")))
        premier = self.corb.lister()[0]["chemin"]
        self.corb.supprimer(premier)
        self.assertEqual(len(self.corb.lister()), 3)
        self.corb.vider()
        self.assertEqual(self.corb.lister(), [])
        self.assertEqual(os.listdir(os.path.join(self.corb.principal, "files")), [])
        self.assertEqual(os.listdir(os.path.join(self.corb.principal, "info")), [])

    def test_trashinfo_orphelin_ignore(self):
        os.makedirs(os.path.join(self.corb.principal, "info"), exist_ok=True)
        with open(os.path.join(self.corb.principal, "info", "fantome.trashinfo"), "w") as f:
            f.write("[Trash Info]\nPath=/nulle/part\nDeletionDate=2026-01-01T10:00:00\n")
        self.assertEqual(self.corb.lister(), [])


if __name__ == "__main__":
    unittest.main()

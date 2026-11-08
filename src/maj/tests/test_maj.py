# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests de la logique des mises à jour et de la liste blanche du helper.

Lancer : python3 -m unittest discover -s src/maj/tests
"""
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(RACINE))

import logique_maj as lm  # noqa: E402

HELPER = RACINE / "helper" / "exolyx-maj-helper"
_chargeur = importlib.machinery.SourceFileLoader("exolyx_maj_helper", str(HELPER))
_spec = importlib.util.spec_from_loader("exolyx_maj_helper", _chargeur)
helper = importlib.util.module_from_spec(_spec)
_chargeur.exec_module(helper)

CHECKUPDATES = """\
firefox 132.0.2-1 -> 133.0-1
linux 6.12.3.arch1-1 -> 6.12.4.arch1-1
mesa 1:24.2.8-1 -> 1:24.3.1-1
nvidia-utils 565.57.01-2 -> 565.77-1
systemd 256.8-1 -> 257-1
linux-firmware 20241111.b5885ec5-1 -> 20241210.c2c5b4dd-1
python 3.12.7-1 -> 3.12.8-1 [ignored]
ligne parasite sans flèche
"""

PACMAN_SI = """\
Repository      : extra
Name            : firefox
Version         : 133.0-1
Download Size   : 67.00 MiB
Installed Size  : 248.95 MiB

Repository      : core
Name            : linux
Version         : 6.12.4.arch1-1
Download Size   : 136.02 MiB

Repository      : extra
Name            : mesa
Download Size   : 9930.50 KiB
"""

FLATPAK_MAJ = "com.spotify.Client\t1.2.50.335\tstable\t186.0 MB\norg.freedesktop.Platform\t\t24.08\t95,1 MB\n"
FLATPAK_LISTE = "com.spotify.Client\t1.2.48.405\norg.freedesktop.Platform\t\n"


class TestAnalyse(unittest.TestCase):
    def test_checkupdates(self):
        maj = lm.analyser_checkupdates(CHECKUPDATES)
        self.assertEqual([m.nom for m in maj],
                         ["firefox", "linux", "mesa", "nvidia-utils", "systemd", "linux-firmware"])
        self.assertEqual((maj[2].ancienne, maj[2].nouvelle), ("1:24.2.8-1", "1:24.3.1-1"))
        self.assertTrue(all(m.source == "pacman" for m in maj))

    def test_checkupdates_vide(self):
        self.assertEqual(lm.analyser_checkupdates(""), [])

    def test_redemarrage(self):
        maj = {m.nom: m.redemarrage for m in lm.analyser_checkupdates(CHECKUPDATES)}
        self.assertEqual(maj, {"firefox": False, "linux": True, "mesa": True, "nvidia-utils": True,
                               "systemd": True, "linux-firmware": False})
        for nom in ("linux-lts", "linux-zen", "nvidia-open", "lib32-mesa", "systemd-libs"):
            self.assertTrue(lm.necessite_redemarrage(nom), nom)
        for nom in ("linux-api-headers", "mesa-utils", "systemd-ui", "python-linux"):
            self.assertFalse(lm.necessite_redemarrage(nom), nom)

    def test_noyau_remplace(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "6.12.3-arch1-1"))
            self.assertFalse(lm.noyau_remplace("6.12.3-arch1-1", d))
            self.assertTrue(lm.noyau_remplace("6.12.2-arch1-1", d))

    def test_pacman_si(self):
        t = lm.analyser_pacman_si(PACMAN_SI)
        self.assertEqual(t["firefox"], 67 * 1024 ** 2)
        self.assertEqual(t["linux"], int(136.02 * 1024 ** 2))
        self.assertEqual(t["mesa"], int(9930.5 * 1024))

    def test_tailles(self):
        self.assertEqual(lm.convertir_taille("830 bytes"), 830)
        self.assertEqual(lm.convertir_taille("1,5 GB"), 1_500_000_000)
        self.assertEqual(lm.convertir_taille("n/a"), 0)
        self.assertEqual(lm.formater_taille(0), "—")
        self.assertEqual(lm.formater_taille(67 * 1024 ** 2), "67,0 Mo")
        self.assertEqual(lm.formater_taille(512), "512 o")

    def test_flatpak(self):
        maj = lm.analyser_flatpak(FLATPAK_MAJ, FLATPAK_LISTE)
        self.assertEqual(len(maj), 2)
        self.assertEqual((maj[0].nom, maj[0].ancienne, maj[0].nouvelle),
                         ("com.spotify.Client", "1.2.48.405", "1.2.50.335"))
        self.assertEqual(maj[0].taille, 186_000_000)
        self.assertEqual((maj[1].ancienne, maj[1].nouvelle), ("—", "24.08"))
        self.assertEqual(maj[1].taille, 95_100_000)
        self.assertTrue(all(m.source == "flatpak" for m in maj))

    def test_flatpak_entete_ignoree(self):
        self.assertEqual(lm.analyser_flatpak("Application\tVersion\tBranch\tDownload\n"), [])


class TestVerification(unittest.TestCase):
    def test_codes_checkupdates(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"XDG_CACHE_HOME": d}):
            with mock.patch.object(lm, "_executer", return_value=(2, "")):
                self.assertEqual(lm.verifier_pacman(), ([], ""))
            with mock.patch.object(lm, "_executer", return_value=(1, "")):
                maj, err = lm.verifier_pacman()
                self.assertEqual(maj, [])
                self.assertTrue(err)
            reponses = iter([(0, CHECKUPDATES), (0, PACMAN_SI)])
            with mock.patch.object(lm, "_executer", side_effect=lambda *a, **k: next(reponses)) as ex:
                maj, err = lm.verifier_pacman()
                self.assertEqual(err, "")
                self.assertEqual(maj[0].taille, 67 * 1024 ** 2)
                # checkupdates utilise une base dédiée, que pacman -Si réutilise
                env = ex.call_args_list[0].args[1]
                self.assertTrue(env["CHECKUPDATES_DB"].endswith("exolyx/checkup-db"))
                self.assertIn(env["CHECKUPDATES_DB"], ex.call_args_list[1].args[0])

    def test_cache(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "exolyx" / "maj.json"
            self.assertEqual(lm.lire_cache(f), {})
            res = {"date": "2026-11-08T10:00:00", "pacman": [{"nom": "linux"}], "flatpak": [], "erreur": ""}
            lm.ecrire_cache(res, f)
            self.assertEqual(lm.lire_cache(f), res)
            self.assertEqual(lm.nombre(res), 1)
            f.write_text("corrompu")
            self.assertEqual(lm.lire_cache(f), {})


class TestProgression(unittest.TestCase):
    def test_sortie_simulee_complete(self):
        suivi = lm.ProgressionPacman()
        valeurs = [suivi.lire(l) for l in helper.SIMULATION.splitlines()]
        self.assertEqual(valeurs, sorted(valeurs), "la progression doit être monotone")
        self.assertEqual(suivi.total, 3)
        self.assertEqual(suivi.telecharges, 3)
        self.assertAlmostEqual(valeurs[-1], 1.0)
        self.assertGreaterEqual(max(v for v, l in zip(valeurs, helper.SIMULATION.splitlines())
                                    if "upgrading linux" in l), 0.7)

    def test_rien_a_faire(self):
        suivi = lm.ProgressionPacman()
        suivi.lire(" there is nothing to do")
        self.assertEqual(suivi.valeur, 1.0)

    def test_liste_verbeuse(self):
        suivi = lm.ProgressionPacman()
        suivi.lire("Package (12)   Old Version  New Version  Net Change  Download Size")
        self.assertEqual(suivi.total, 12)


class TestHelper(unittest.TestCase):
    def test_accepte(self):
        self.assertEqual(helper.valider(["mettre-a-jour"]), ("mettre-a-jour", False))
        self.assertEqual(helper.valider(["mettre-a-jour", "--simulation"]), ("mettre-a-jour", True))

    def test_refuse(self):
        for argv in ([], ["installer", "vlc"], ["mettre-a-jour", "vlc"],
                     ["mettre-a-jour", "--noconfirm"], ["sh", "-c", "id"],
                     ["mettre-a-jour", "mettre-a-jour"], ["--simulation"]):
            with self.assertRaises(ValueError, msg=argv):
                helper.valider(argv)
            tampon = io.StringIO()
            with redirect_stdout(tampon):
                self.assertEqual(helper.main(argv), 2)
            self.assertIn("@@FIN 2", tampon.getvalue())

    def test_commande_fixe(self):
        self.assertEqual(helper.COMMANDE, ["pacman", "-Syu", "--noconfirm", "--noprogressbar"])

    def test_simulation_bout_en_bout(self):
        r = subprocess.run([sys.executable, str(HELPER), "mettre-a-jour", "--simulation"],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.strip().endswith("@@FIN 0"))


class TestFixture(unittest.TestCase):
    def test_fixture_coherente(self):
        d = json.loads((ICI / "fixture-maj.json").read_text(encoding="utf-8"))
        for m in d["pacman"]:
            self.assertEqual(m["redemarrage"], lm.necessite_redemarrage(m["nom"]), m["nom"])


if __name__ == "__main__":
    unittest.main()

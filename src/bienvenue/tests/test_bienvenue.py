# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests de la logique de l'appli de bienvenue et de la liste blanche du helper.

Lancer : python3 -m unittest discover -s src/bienvenue/tests
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

import logique  # noqa: E402

HELPER = RACINE / "helper" / "exolyx-helper"


def charger_helper():
    chargeur = importlib.machinery.SourceFileLoader("exolyx_helper", str(HELPER))
    spec = importlib.util.spec_from_loader("exolyx_helper", chargeur)
    module = importlib.util.module_from_spec(spec)
    chargeur.exec_module(module)
    return module


helper = charger_helper()

LSPCI = """\
00:00.0 Host bridge [0600]: Intel Corporation 8th Gen Core Processor Host Bridge/DRAM Registers [8086:3ec2] (rev 07)
00:02.0 VGA compatible controller [0300]: Intel Corporation CoffeeLake-S GT2 [UHD Graphics 630] [8086:3e92]
01:00.0 VGA compatible controller [0300]: NVIDIA Corporation TU106 [GeForce RTX 2060 Rev. A] [10de:1f08] (rev a1)
01:00.1 Audio device [0403]: NVIDIA Corporation TU106 High Definition Audio Controller [10de:10f9] (rev a1)
"""
LSPCI_ANCIENNE = "01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GK107 [GeForce GTX 650] [10de:0fc6] (rev a1)\n"
LSPCI_3D = "02:00.0 3D controller [0302]: NVIDIA Corporation GA107M [GeForce RTX 3050 Mobile] [10de:25a2] (rev a1)\n"
LSPCI_VBOX = "00:02.0 VGA compatible controller [0300]: VMware SVGA II Adapter [15ad:0405]\n"


class TestLspci(unittest.TestCase):
    def test_cartes_detectees(self):
        cartes = logique.analyser_lspci(LSPCI)
        self.assertEqual([c.fabricant for c in cartes], ["intel", "nvidia"])
        self.assertEqual(cartes[1].nom, "GeForce RTX 2060 Rev. A")
        self.assertEqual(cartes[1].id_peripherique, 0x1F08)
        self.assertTrue(cartes[1].nvidia_open_compatible)
        self.assertFalse(cartes[0].nvidia_open_compatible)

    def test_audio_ignore(self):
        self.assertEqual(len(logique.analyser_lspci(LSPCI)), 2)

    def test_controleur_3d_portable(self):
        cartes = logique.analyser_lspci(LSPCI_3D)
        self.assertEqual(cartes[0].fabricant, "nvidia")
        pilotes, _ = logique.pilotes_proposes(cartes, "none")
        self.assertEqual(pilotes[0].paquets, ["nvidia-open", "nvidia-utils", "nvidia-settings"])

    def test_nvidia_ancienne_pas_de_pilote(self):
        pilotes, remarques = logique.pilotes_proposes(logique.analyser_lspci(LSPCI_ANCIENNE), "none")
        self.assertEqual(pilotes, [])
        self.assertIn("nouveau", remarques[0])

    def test_virtualbox(self):
        pilotes, _ = logique.pilotes_proposes(logique.analyser_lspci(LSPCI_VBOX), "oracle")
        self.assertEqual([p.id for p in pilotes], ["virtualbox"])
        self.assertEqual(pilotes[0].paquets, ["virtualbox-guest-utils"])

    def test_autre_virtualisation(self):
        pilotes, remarques = logique.pilotes_proposes([], "kvm")
        self.assertEqual(pilotes, [])
        self.assertTrue(remarques)

    def test_sortie_vide(self):
        self.assertEqual(logique.analyser_lspci(""), [])
        self.assertEqual(logique.pilotes_proposes([], "none"), ([], []))


class TestPersistance(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.fichier = Path(self.dossier.name) / "exolyx" / "bienvenue.json"

    def tearDown(self):
        self.dossier.cleanup()

    def test_premier_lancement(self):
        self.assertEqual(logique.lire_etat(self.fichier), {})
        self.assertTrue(logique.doit_afficher_au_demarrage(self.fichier, live=False))

    def test_termine_ne_se_rouvre_pas(self):
        logique.ecrire_etat({"termine": True, "afficherAuDemarrage": False}, self.fichier)
        self.assertEqual(json.loads(self.fichier.read_text())["termine"], True)
        self.assertFalse(logique.doit_afficher_au_demarrage(self.fichier, live=False))

    def test_termine_mais_reaffichage_demande(self):
        logique.ecrire_etat({"termine": True, "afficherAuDemarrage": True}, self.fichier)
        self.assertTrue(logique.doit_afficher_au_demarrage(self.fichier, live=False))

    def test_live_toujours_affiche(self):
        logique.ecrire_etat({"termine": True}, self.fichier)
        self.assertTrue(logique.doit_afficher_au_demarrage(self.fichier, live=True))

    def test_fichier_corrompu(self):
        self.fichier.parent.mkdir(parents=True)
        self.fichier.write_text("{pas du json")
        self.assertEqual(logique.lire_etat(self.fichier), {})
        self.assertTrue(logique.doit_afficher_au_demarrage(self.fichier, live=False))

    def test_chemin_xdg(self):
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self.dossier.name}):
            self.assertEqual(logique.fichier_etat(), self.fichier)


class TestTheme(unittest.TestCase):
    def ecrire(self, contenu):
        f = tempfile.NamedTemporaryFile("w", delete=False, suffix="kdeglobals")
        f.write(contenu)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_clair(self):
        self.assertFalse(logique.theme_sombre(self.ecrire("[General]\nColorScheme=ExoLyxClair\n")))

    def test_sombre(self):
        self.assertTrue(logique.theme_sombre(self.ecrire("[General]\nColorScheme=ExoLyx\n")))

    def test_autre_groupe_ignore(self):
        self.assertTrue(logique.theme_sombre(self.ecrire("[Autre]\nColorScheme=ExoLyxClair\n[General]\n")))

    def test_absent(self):
        self.assertTrue(logique.theme_sombre("/nexiste/pas"))

    def test_noms(self):
        self.assertEqual(logique.theme_icones("Trait", True), "ExoLyx-Trait")
        self.assertEqual(logique.theme_icones("Relief", False), "ExoLyx-Relief-Clair")
        self.assertEqual(logique.schema_couleurs(False), "ExoLyxClair")
        self.assertEqual(logique.look_and_feel(True), "org.exolyx.sombre")
        with self.assertRaises(ValueError):
            logique.theme_icones("Arc-en-ciel", True)

    def test_commandes_apparence_ordre(self):
        cmds = logique.commandes_apparence(False, "Duo", fond=False)
        self.assertEqual(cmds[0], ["plasma-apply-lookandfeel", "-a", "org.exolyx.clair"])
        self.assertEqual(cmds[1], ["plasma-apply-colorscheme", "ExoLyxClair"])
        self.assertEqual(cmds[2][-1], "ExoLyx-Duo-Clair")


class TestCatalogue(unittest.TestCase):
    def test_catalogue_dans_liste_blanche(self):
        for a in logique.CATALOGUE:
            for p in a.paquets:
                autorises = helper.PACMAN_AUTORISES if a.source == "pacman" else helper.FLATPAK_AUTORISES
                self.assertIn(p, autorises, f"{a.nom} : {p}")

    def test_pilotes_dans_liste_blanche(self):
        cartes = logique.analyser_lspci(LSPCI)
        for virt in ("none", "oracle"):
            for pil in logique.pilotes_proposes(cartes, virt)[0]:
                for p in pil.paquets:
                    self.assertIn(p, helper.PACMAN_AUTORISES)

    def test_jetons(self):
        self.assertEqual(
            logique.jetons_installation(["libreoffice", "steam"], ["nvidia-open"]),
            ["pacman:nvidia-open", "pacman:libreoffice-fresh", "pacman:libreoffice-fresh-fr",
             "flatpak:com.valvesoftware.Steam"])
        # tous les jetons du catalogue complet sont acceptés par le helper
        tout = logique.jetons_installation([a.id for a in logique.CATALOGUE])
        helper.valider(["installer", *tout])


class TestListeBlanche(unittest.TestCase):
    def refuse(self, argv):
        with self.assertRaises(helper.Refus):
            helper.valider(argv)

    def test_accepte(self):
        action, sim, pac, fp = helper.valider(
            ["installer", "pacman:vlc", "flatpak:com.spotify.Client", "pacman:vlc"])
        self.assertEqual((action, sim, pac, fp), ("installer", False, ["vlc"], ["com.spotify.Client"]))

    def test_simulation(self):
        self.assertTrue(helper.valider(["installer", "--simulation", "pacman:gimp"])[1])

    def test_actions_refusees(self):
        self.refuse([])
        self.refuse(["supprimer", "pacman:vlc"])
        self.refuse(["sh", "-c", "id"])
        self.refuse(["installer"])

    def test_paquets_refuses(self):
        self.refuse(["installer", "pacman:linux"])
        self.refuse(["installer", "pacman:vlc;rm -rf /"])
        self.refuse(["installer", "pacman:--overwrite=*"])
        self.refuse(["installer", "pacman:VLC"])
        self.refuse(["installer", "vlc"])
        self.refuse(["installer", "aur:yay"])
        self.refuse(["installer", "flatpak:org.evil.App"])
        self.refuse(["installer", "flatpak:com.spotify.Client", "--option"])
        self.refuse(["installer", "pacman:vlc", "--noconfirm"])
        self.refuse(["installer"] + ["pacman:vlc"] * 40)

    def test_main_refus_code_2(self):
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            code = helper.main(["installer", "pacman:sudo"])
        self.assertEqual(code, 2)
        self.assertIn("@@FIN 2", tampon.getvalue())

    def test_pas_root_code_3(self):
        if os.geteuid() == 0:
            self.skipTest("lancé en root")
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            self.assertEqual(helper.main(["installer", "pacman:vlc"]), 3)

    def test_simulation_bout_en_bout(self):
        sortie = subprocess.run(
            [sys.executable, str(HELPER), "installer", "--simulation", "pacman:vlc",
             "flatpak:com.spotify.Client"], capture_output=True, text=True, timeout=30)
        self.assertEqual(sortie.returncode, 0, sortie.stdout)
        self.assertIn("@@ETAPE 1 2", sortie.stdout)
        self.assertIn("@@PROGRES 100", sortie.stdout)
        self.assertTrue(sortie.stdout.strip().endswith("@@FIN 0"))


class TestApercus(unittest.TestCase):
    def test_apercu_icones_et_fonds(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "ExoLyx-Trait" / "scalable" / "places"
            base.mkdir(parents=True)
            (base / "folder.svg").write_text("<svg/>")
            images = Path(d) / "ExoLyx-Clair" / "contents" / "images"
            images.mkdir(parents=True)
            for n in ("1920x1080.png", "3840x2160.png"):
                (images / n).write_bytes(b"")
            with mock.patch.dict(os.environ, {"EXOLYX_DOSSIER_ICONES": d, "EXOLYX_DOSSIER_FONDS": d}):
                self.assertEqual(len(logique.apercu_icones("ExoLyx-Trait")), 1)
                self.assertEqual(logique.apercu_icones("ExoLyx-Duo"), [])
                f = logique.trouver_fond(False)
                self.assertTrue(f["image"].endswith("1920x1080.png"))
                self.assertEqual(logique.trouver_fond(True), {"paquet": "", "image": ""})


if __name__ == "__main__":
    unittest.main()

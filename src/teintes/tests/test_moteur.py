# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests du moteur des teintes dynamiques (sans Qt ni Plasma)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import moteur as m  # noqa: E402


def contraste(a, b):
    def lum(h):
        r, g, bb = (m._lin(c) for c in m.hex_rgb(h))
        return 0.2126 * r + 0.7152 * g + 0.0722 * bb
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class Couleurs(unittest.TestCase):
    def test_aller_retour_oklch(self):
        for h in ("#A8D479", "#0D1310", "#FF7E6B", "#3C82C8", "#FFFFFF", "#000000"):
            self.assertEqual(m.oklch_hex(*m.rgb_oklch(m.hex_rgb(h))).upper(), h)

    def test_gamut(self):
        # une saturation impossible est ramenée dans le sRGB
        self.assertRegex(m.oklch_hex(0.7, 0.5, 260), r"^#[0-9A-F]{6}$")


class Analyse(unittest.TestCase):
    def test_teinte_rouge(self):
        a = m.analyser([(0.85, 0.2, 0.15)] * 500 + [(0.05, 0.05, 0.05)] * 500)
        self.assertFalse(a["neutre"])
        self.assertTrue(a["teinte"] < 45 or a["teinte"] > 350, a["teinte"])
        self.assertLess(a["luminosite"], 0.62)

    def test_teinte_bleue_claire(self):
        a = m.analyser([(0.8, 0.88, 0.98)] * 800 + [(0.2, 0.45, 0.85)] * 200)
        self.assertTrue(220 < a["teinte"] < 280, a["teinte"])
        self.assertTrue(m.est_sombre(a, "sombre"))
        self.assertFalse(m.est_sombre(a, "auto"))

    def test_fond_gris_neutre(self):
        a = m.analyser([(v, v, v) for v in (0.1, 0.3, 0.5, 0.7)] * 200)
        self.assertTrue(a["neutre"])

    def test_vive_contre_dominante(self):
        # beaucoup de beige peu saturé, un peu de violet très vif
        a = m.analyser([(0.85, 0.78, 0.65)] * 900 + [(0.6, 0.1, 0.95)] * 100)
        self.assertTrue(50 < a["teinte"] < 100, a["teinte"])
        self.assertTrue(280 < a["teinte_vive"] < 330, a["teinte_vive"])


class Palette(unittest.TestCase):
    def test_contrastes_lisibles(self):
        for pixels in ([(0.85, 0.2, 0.15)] * 100, [(0.2, 0.45, 0.85)] * 100, [(0.5, 0.5, 0.5)] * 100):
            a = m.analyser(pixels)
            for sombre in (True, False):
                for it in (0, 50, 100):
                    p = m.palette_dynamique(a, sombre, it)
                    self.assertGreater(contraste(p["texte"], p["fond"]), 7, (sombre, it))
                    self.assertGreater(contraste(p["surAccent"], p["accent"]), 3, (sombre, it, p["accent"]))
                    self.assertGreater(contraste(p["doux"], p["fond"]), 3.5, (sombre, it))

    def test_teinte_suivie(self):
        a = m.analyser([(0.2, 0.45, 0.85)] * 100)
        _, c, h = m.rgb_oklch(m.hex_rgb(m.palette_dynamique(a, True)["accent"]))
        self.assertGreater(c, 0.05)
        self.assertTrue(220 < h < 290, h)

    def test_schema_kde(self):
        a = m.analyser([(0.85, 0.2, 0.15)] * 100)
        texte = m.gc.schema("ExoLyxTeinteA", m.palette_dynamique(a, True))
        for section in ("[Colors:Window]", "[Colors:Selection]", "[General]", "[WM]"):
            self.assertIn(section, texte)
        self.assertNotIn("#", texte)  # couleurs écrites en r,g,b


class Systeme(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.anciens = (m.CONFIG, m.DONNEES, m.FICHIER_REGLAGES, m.APPLETSRC)
        m.CONFIG, m.DONNEES = t / "config", t / "data"
        m.FICHIER_REGLAGES = m.CONFIG / "exolyx" / "teintes.json"
        m.APPLETSRC = m.CONFIG / "plasma-org.kde.plasma.desktop-appletsrc"
        m.CONFIG.mkdir(parents=True)
        self.t = t

    def tearDown(self):
        m.CONFIG, m.DONNEES, m.FICHIER_REGLAGES, m.APPLETSRC = self.anciens
        self.tmp.cleanup()

    def test_fond_actuel_paquet(self):
        img = self.t / "fonds" / "ExoLyx-01" / "contents" / "images"
        img.mkdir(parents=True)
        (img / "1920x1080.png").write_bytes(b"x")
        (img / "3840x2160.jpg").write_bytes(b"x")
        m.APPLETSRC.write_text(
            "[Containments][7][General]\nfoo=1\n\n"
            f"[Containments][7][Wallpaper][org.kde.image][General]\nImage=file://{img.parent.parent}/\n",
            encoding="utf-8")
        self.assertEqual(m.fond_actuel().name, "3840x2160.jpg")

    def test_reglages(self):
        self.assertEqual(m.lire_reglages(), m.REGLAGES_DEFAUT)
        m.ecrire_reglages(dict(m.REGLAGES_DEFAUT, intensite=80))
        self.assertEqual(m.lire_reglages()["intensite"], 80)

    def test_noms_alternes(self):
        a = m.analyser([(0.2, 0.45, 0.85)] * 100)
        p = m.palette_dynamique(a, False)
        cle1 = m.appliquer_palette(p, False, executer=False)
        (m.CONFIG / "kdeglobals").write_text(f"[General]\nColorScheme={cle1}\n", encoding="utf-8")
        cle2 = m.appliquer_palette(p, False, executer=False)
        self.assertNotEqual(cle1, cle2)
        self.assertIn("Clair", cle1)  # convention des applis ExoLyx
        restants = sorted(f.name for f in (m.DONNEES / "color-schemes").glob("*.colors"))
        self.assertEqual(restants, [f"{cle2}.colors"])

    def test_inactif(self):
        m.ecrire_reglages(dict(m.REGLAGES_DEFAUT, actif=False))
        self.assertIsNone(m.mettre_a_jour(executer=False))


if __name__ == "__main__":
    unittest.main()

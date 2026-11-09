import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import logique as L


class Tests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_defaut_ardoise_partout(self):
        e = L.lire_etat(self.d / "absent.json")
        self.assertEqual(e["style"], "ardoise")
        self.assertTrue(all(e["applis"].values()))
        self.assertEqual(len(e["applis"]), 10)

    def test_etat_corrompu(self):
        f = self.d / "e.json"; f.write_text("{pas du json")
        self.assertEqual(L.lire_etat(f), L.etat_par_defaut())

    def test_aller_retour(self):
        f = self.d / "e.json"
        e = L.etat_par_defaut(); e["style"] = "origine"; e["applis"]["kate"] = False
        L.ecrire_etat(e, f)
        self.assertEqual(L.lire_etat(f), e)

    def test_style_par_appli(self):
        e = L.etat_par_defaut(); e["applis"]["okular"] = False
        self.assertEqual(L.style_de(e, "okular"), "origine")
        self.assertEqual(L.style_de(e, "kate"), "ardoise")
        e["style"] = "origine"
        self.assertEqual(L.style_de(e, "kate"), "origine")

    def test_regler_preserve_le_reste(self):
        f = self.d / "katerc"
        f.write_text("[General]\nShow Statusbar=true\n\n[UiSettings]\nColorScheme=Breeze\nAutre=1\n\n[Fin]\nx=y\n")
        L.regler(f, "UiSettings", "ColorScheme", "Ardoise")
        L.regler(f, "KTextEditor Renderer", "Color Theme", "Ardoise")
        L.regler(f, "UiSettings", "Nouveau", "oui")
        t = f.read_text()
        self.assertIn("ColorScheme=Ardoise", t); self.assertNotIn("Breeze", t)
        self.assertIn("Show Statusbar=true", t); self.assertIn("[Fin]\nx=y", t)
        self.assertEqual(L.lire(f, "UiSettings", "Nouveau"), "oui")
        self.assertEqual(L.lire(f, "UiSettings", "Autre"), "1")
        self.assertEqual(L.lire(f, "KTextEditor Renderer", "Color Theme"), "Ardoise")
        self.assertEqual(t.count("[UiSettings]"), 1)

    def test_appliquer_origine_puis_ardoise(self):
        e = L.etat_par_defaut(); e["style"] = "origine"
        L.appliquer(e, self.d)
        self.assertEqual(L.lire(self.d / "okularrc", "UiSettings", "ColorScheme"), "Default")
        self.assertEqual(L.lire(self.d / "konsolerc", "Desktop Entry", "DefaultProfile"), "ExoLyx.profile")
        self.assertTrue((self.d / "exolyx" / "firefox-origine").exists())
        e["style"] = "ardoise"; e["applis"]["gwenview"] = False
        L.appliquer(e, self.d)
        self.assertEqual(L.lire(self.d / "okularrc", "UiSettings", "ColorScheme"), "Ardoise")
        self.assertEqual(L.lire(self.d / "gwenviewrc", "UiSettings", "ColorScheme"), "Default")
        self.assertEqual(L.lire(self.d / "konsolerc", "UiSettings", "WindowColorScheme"), "Ardoise")
        self.assertEqual(L.lire(self.d / "katerc", "KTextEditor Renderer", "Color Theme"), "Ardoise")
        self.assertFalse((self.d / "exolyx" / "firefox-origine").exists())


if __name__ == "__main__":
    unittest.main()

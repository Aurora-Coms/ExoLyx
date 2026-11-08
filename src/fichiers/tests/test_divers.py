import hashlib
import os
import time
import unittest
from datetime import datetime

from aide import TestAvecDossier, xattr_disponible

import etiquettes
import recents
from config import Config, theme_systeme_clair
from modele import categorie_mime, format_date, format_taille


class TestFormats(unittest.TestCase):
    def test_taille(self):
        nb = " "
        self.assertEqual(format_taille(0), f"0{nb}o")
        self.assertEqual(format_taille(1536), f"1,5{nb}Ko")
        self.assertEqual(format_taille(1024 ** 2), f"1{nb}Mo")
        self.assertEqual(format_taille(250 * 1024 ** 3), f"250{nb}Go")

    def test_date(self):
        maintenant = datetime(2026, 11, 8, 15, 0).timestamp()
        self.assertEqual(format_date(datetime(2026, 11, 8, 9, 5).timestamp(), maintenant), "Aujourd’hui, 09:05")
        self.assertEqual(format_date(datetime(2026, 11, 7, 23, 59).timestamp(), maintenant), "Hier, 23:59")
        self.assertEqual(format_date(datetime(2026, 2, 3, 8, 0).timestamp(), maintenant), "3 févr., 08:00")
        self.assertEqual(format_date(datetime(2024, 8, 15).timestamp(), maintenant), "15 août 2024")
        self.assertEqual(format_date(0), "")

    def test_categories(self):
        self.assertEqual(categorie_mime("image/png"), "image")
        self.assertEqual(categorie_mime("application/pdf"), "pdf")
        self.assertEqual(categorie_mime("application/x-compressed-tar"), "archive")
        self.assertEqual(categorie_mime("text/x-python"), "code")
        self.assertEqual(categorie_mime("text/plain"), "texte")
        self.assertEqual(categorie_mime("application/vnd.oasis.opendocument.spreadsheet"), "tableur")
        self.assertEqual(categorie_mime("application/vnd.efi.iso"), "disque")
        self.assertEqual(categorie_mime("application/octet-stream"), "fichier")


class TestEtiquettes(TestAvecDossier):
    def setUp(self):
        super().setUp()
        if not xattr_disponible(self.tmp):
            self.skipTest("pas d'attributs étendus ici")

    def test_lire_ecrire(self):
        f = self.ecrire("a.txt")
        self.assertEqual(etiquettes.lire(f), [])
        self.assertEqual(etiquettes.ecrire(f, ["Travail", " Important ", "Travail", "a,b"]), ["Travail", "Important", "a b"])
        self.assertEqual(os.getxattr(f, "user.xdg.tags"), b"Travail,Important,a b")
        etiquettes.ajouter(f, "Urgent")
        etiquettes.retirer(f, "Travail")
        self.assertEqual(etiquettes.lire(f), ["Important", "a b", "Urgent"])
        etiquettes.ecrire(f, [])
        self.assertEqual(etiquettes.lire(f), [])
        self.assertNotIn("user.xdg.tags", os.listxattr(f))

    def test_parcours(self):
        a = self.ecrire("maison/Documents/a.txt")
        b = self.ecrire("maison/Images/vacances/b.png")
        self.ecrire("maison/.cache/c.txt")
        etiquettes.ecrire(a, ["Travail"])
        etiquettes.ecrire(b, ["Vacances", "Travail"])
        etiquettes.ecrire(os.path.join(self.tmp, "maison/.cache/c.txt"), ["Caché"])
        trouve = dict(etiquettes.parcourir(os.path.join(self.tmp, "maison")))
        self.assertEqual(trouve, {a: ["Travail"], b: ["Vacances", "Travail"]})

    def test_index_qt(self):
        from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer
        app = QCoreApplication.instance() or QCoreApplication([])
        a = self.ecrire("maison/a.txt")
        etiquettes.ecrire(a, ["Travail"])
        index = etiquettes.IndexEtiquettes(os.path.join(self.tmp, "maison"))
        boucle = QEventLoop()
        index.change.connect(boucle.quit)
        QTimer.singleShot(5000, boucle.quit)
        index.demarrer()
        boucle.exec()
        self.assertEqual(index.toutes(), [("Travail", 1)])
        self.assertEqual(index.fichiers("Travail"), [a])
        index.renommer(a, a + ".bak")
        self.assertEqual(index.fichiers("Travail"), [])   # n'existe pas réellement
        self.assertTrue(os.path.exists(etiquettes.chemin_cache()))
        del app


class TestRecents(unittest.TestCase):
    XBEL = """<?xml version="1.0" encoding="UTF-8"?>
<xbel version="1.0" xmlns:bookmark="http://www.freedesktop.org/standards/desktop-bookmarks">
  <bookmark href="file:///home/moi/Documents/rapport%20final.pdf" added="2026-11-01T10:00:00.123456Z"
            modified="2026-11-05T10:00:00Z" visited="2026-11-01T10:00:00Z"/>
  <bookmark href="file:///home/moi/Images/lac.png" added="2026-11-06T08:00:00.1Z"
            modified="2026-11-06T08:00:00.1Z" visited="2026-11-06T08:00:00.1Z"/>
  <bookmark href="https://exemple.org/page" added="2026-11-07T08:00:00Z" modified="2026-11-07T08:00:00Z"/>
  <bookmark href="file:///home/moi/disparu.txt" added="2026-11-07T08:00:00Z" modified="2026-11-07T08:00:00Z"/>
</xbel>"""

    def test_analyse(self):
        existe = {"/home/moi/Documents/rapport final.pdf", "/home/moi/Images/lac.png"}.__contains__
        resultat = recents.analyser(self.XBEL, existe=existe)
        self.assertEqual([c for c, _ in resultat], ["/home/moi/Images/lac.png", "/home/moi/Documents/rapport final.pdf"])
        self.assertAlmostEqual(resultat[1][1], datetime.fromisoformat("2026-11-05T10:00:00+00:00").timestamp())

    def test_xml_invalide(self):
        self.assertEqual(recents.analyser("<xbel"), [])


class TestConfig(TestAvecDossier):
    def test_theme_kdeglobals(self):
        k = self.ecrire("kdeglobals", "[General]\nColorScheme=ExoLyxClair\n")
        self.assertTrue(theme_systeme_clair(k))
        k = self.ecrire("kdeglobals", "[General]\nColorScheme=ExoLyx\n")
        self.assertFalse(theme_systeme_clair(k))
        self.assertFalse(theme_systeme_clair(os.path.join(self.tmp, "absent")))

    def test_persistance(self):
        c = Config(os.path.join(self.tmp, "config", "exolyx", "fichiers.json"))
        self.assertIsInstance(c.get("epingles"), list)
        c.set("epingles", ["/tmp"])
        c.set("vue", "liste")
        c2 = Config(c.chemin)
        self.assertEqual(c2.get("epingles"), ["/tmp"])
        self.assertEqual(c2.get("vue"), "liste")


class TestMiniatures(TestAvecDossier):
    def test_cache_freedesktop(self):
        from PyQt6.QtGui import QGuiApplication, QImage, QColor
        app = QGuiApplication.instance() or QGuiApplication([])
        import apercu
        chemin = os.path.join(self.tmp, "photo é.png")
        image = QImage(800, 400, QImage.Format.Format_RGB32)
        image.fill(QColor("#A8D479"))
        image.save(chemin)
        mini = apercu.miniature(chemin, 256)
        self.assertEqual((mini.width(), mini.height()), (256, 128))
        uri = "file://" + chemin.replace(" ", "%20").replace("é", "%C3%A9")
        self.assertEqual(apercu.uri_de(chemin), uri)
        attendu = os.path.join(os.environ["XDG_CACHE_HOME"], "thumbnails", "large",
                               hashlib.md5(uri.encode()).hexdigest() + ".png")
        self.assertTrue(os.path.exists(attendu))
        enregistree = QImage(attendu)
        self.assertEqual(enregistree.text("Thumb::URI"), uri)
        self.assertEqual(enregistree.text("Thumb::MTime"), str(int(os.stat(chemin).st_mtime)))
        self.assertEqual(oct(os.stat(attendu).st_mode & 0o777), "0o600")
        # une miniature périmée est régénérée
        os.utime(chemin, (time.time() + 100, time.time() + 100))
        apercu.miniature(chemin, 256)
        self.assertEqual(QImage(attendu).text("Thumb::MTime"), str(int(os.stat(chemin).st_mtime)))
        # petite taille -> dossier « normal »
        apercu.miniature(chemin, 128)
        self.assertTrue(os.path.exists(attendu.replace("/large/", "/normal/")))
        del app

    def test_pdf_si_poppler(self):
        import shutil
        if not shutil.which("pdftoppm"):
            self.skipTest("pdftoppm absent")
        from PyQt6.QtGui import QGuiApplication, QPdfWriter, QPainter, QPageSize
        app = QGuiApplication.instance() or QGuiApplication([])
        import apercu
        chemin = os.path.join(self.tmp, "doc.pdf")
        w = QPdfWriter(chemin)
        w.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        p = QPainter(w)
        p.drawText(100, 100, "Bonjour")
        w.newPage()
        p.end()
        self.assertEqual(apercu.nombre_pages_pdf(chemin), 2 if shutil.which("pdfinfo") or apercu.QPdfDocument else 1)
        image = apercu.rendre(chemin, 300, page=1)
        self.assertIsNotNone(image)
        self.assertEqual(max(image.width(), image.height()), 300)
        del app


class TestIcones(unittest.TestCase):
    def test_tous_les_svg_sont_valides(self):
        from PyQt6.QtCore import QByteArray
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtSvg import QSvgRenderer
        app = QGuiApplication.instance() or QGuiApplication([])
        import icones
        idents = [f"g/{n}/A8D479" for n in icones.GLYPHES] + \
                 [f"t/{c}/{t}" for c in icones.COULEUR_TYPE for t in (0, 1)] + \
                 [f"d/{e}/0" for e in ("", "documents", "images", "musique", "videos", "telechargements", "bureau", "accueil")]
        for ident in idents:
            svg = icones.svg_pour(ident)
            self.assertNotIn("<filter", svg)
            self.assertTrue(QSvgRenderer(QByteArray(svg.encode())).isValid(), ident)
        del app


if __name__ == "__main__":
    unittest.main()

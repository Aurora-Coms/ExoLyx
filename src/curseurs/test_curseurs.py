#!/usr/bin/env python3
"""Vérifie les fichiers Xcursor produits : relit chaque fichier octet par
octet (sans dépendance), contrôle l'en-tête, la table des matières, les
tailles 24/32/48/64, les points chauds, l'animation et les alias.

Usage : python3 test_curseurs.py [dossier_theme]
"""
import os
import struct
import sys
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
THEME = os.environ.get("THEME_CURSEURS", os.path.join(ICI, "ExoLyx-Curseur"))
TAILLES = {24, 32, 48, 64}
TYPE_IMAGE = 0xFFFD0002

OBLIGATOIRES = """default left_ptr pointer hand2 text xterm wait watch progress left_ptr_watch
crosshair not-allowed grab grabbing move fleur help n-resize s-resize e-resize w-resize
ne-resize nw-resize se-resize sw-resize ew-resize ns-resize nesw-resize nwse-resize
col-resize row-resize all-scroll copy alias context-menu cell vertical-text zoom-in zoom-out
""".split()
ANIMES = {"wait", "watch", "progress", "left_ptr_watch"}


def lire(chemin):
    with open(chemin, "rb") as fh:
        d = fh.read()
    magic, hsize, version, ntoc = struct.unpack_from("<4sIII", d, 0)
    assert magic == b"Xcur", "signature"
    assert hsize == 16, "taille d'en-tête"
    assert version == 0x00010000, "version"
    assert 0 < ntoc < 1000, "ntoc"
    images = []
    for i in range(ntoc):
        typ, sous, pos = struct.unpack_from("<III", d, hsize + 12 * i)
        assert typ == TYPE_IMAGE, "type de toc"
        ch, ctype, csub, cver, w, h, xh, yh, delai = struct.unpack_from("<9I", d, pos)
        assert (ch, ctype, csub, cver) == (36, TYPE_IMAGE, sous, 1), "en-tête de chunk"
        assert pos + 36 + 4 * w * h <= len(d), "chunk tronqué"
        px = struct.unpack_from("<%dI" % (w * h), d, pos + 36)
        images.append(dict(taille=sous, w=w, h=h, xh=xh, yh=yh, delai=delai, px=px))
    return images


class TestCurseurs(unittest.TestCase):
    def fichier(self, nom):
        return os.path.join(THEME, "cursors", nom)

    def test_index(self):
        with open(os.path.join(THEME, "index.theme"), encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn("[Icon Theme]", txt)
        self.assertIn("Name=ExoLyx-Curseur", txt)

    def test_noms_obligatoires(self):
        for nom in OBLIGATOIRES:
            self.assertTrue(os.path.isfile(self.fichier(nom)), nom)

    def test_alias_relatifs(self):
        for nom in os.listdir(os.path.join(THEME, "cursors")):
            p = self.fichier(nom)
            if os.path.islink(p):
                cible = os.readlink(p)
                self.assertNotIn("/", cible, nom)
                self.assertTrue(os.path.isfile(p), "alias cassé : " + nom)

    def test_fichiers(self):
        for nom in sorted(os.listdir(os.path.join(THEME, "cursors"))):
            p = self.fichier(nom)
            if os.path.islink(p):
                continue
            with self.subTest(curseur=nom):
                images = lire(p)
                tailles = {im["taille"] for im in images}
                self.assertEqual(tailles, TAILLES)
                trames = {t: [im for im in images if im["taille"] == t] for t in TAILLES}
                n = {len(v) for v in trames.values()}
                self.assertEqual(len(n), 1, "même nombre de trames par taille")
                for im in images:
                    self.assertEqual((im["w"], im["h"]), (im["taille"], im["taille"]))
                    self.assertLess(im["xh"], im["w"])
                    self.assertLess(im["yh"], im["h"])
                    # ARGB prémultiplié : aucune composante > alpha
                    for v in im["px"][:: 7]:
                        a = v >> 24
                        self.assertLessEqual(max((v >> 16) & 255, (v >> 8) & 255, v & 255), a)
                    self.assertTrue(any(v >> 24 for v in im["px"]), "image vide")
                # points chauds proportionnels entre tailles
                ref = trames[32][0]
                for t in TAILLES:
                    im = trames[t][0]
                    self.assertAlmostEqual(im["xh"] / t, ref["xh"] / 32, delta=1.0 / 24 + 0.01)
                    self.assertAlmostEqual(im["yh"] / t, ref["yh"] / 32, delta=1.0 / 24 + 0.01)

    def test_animation(self):
        for nom in ANIMES:
            images = lire(self.fichier(nom))
            t32 = [im for im in images if im["taille"] == 32]
            self.assertGreaterEqual(len(t32), 8, nom)
            self.assertTrue(all(im["delai"] > 0 for im in t32))
            self.assertNotEqual(t32[0]["px"], t32[len(t32) // 2]["px"], "trames identiques")

    def test_point_chaud_fleche(self):
        im = [i for i in lire(self.fichier("default")) if i["taille"] == 32][0]
        # le pixel du point chaud (pointe de la flèche) doit être opaque ou presque
        alpha = max(im["px"][(im["yh"] + dy) * 32 + im["xh"] + dx] >> 24
                    for dx in (0, 1) for dy in (0, 1))
        self.assertGreater(alpha, 100)


    def test_libxcursor(self):
        """Contre-vérification avec la vraie libXcursor si elle est présente."""
        import ctypes
        import ctypes.util
        nom_lib = ctypes.util.find_library("Xcursor")
        if not nom_lib:
            self.skipTest("libXcursor absente")
        lib = ctypes.CDLL(nom_lib)

        class Image(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint) for n in ("version", "size", "width", "height",
                                                    "xhot", "yhot", "delay")] + [("pixels", ctypes.c_void_p)]

        class Images(ctypes.Structure):
            _fields_ = [("nimage", ctypes.c_int), ("images", ctypes.POINTER(ctypes.POINTER(Image))),
                        ("name", ctypes.c_char_p)]
        lib.XcursorFilenameLoadImages.restype = ctypes.POINTER(Images)
        lib.XcursorFilenameLoadImages.argtypes = [ctypes.c_char_p, ctypes.c_int]
        lib.XcursorImagesDestroy.argtypes = [ctypes.POINTER(Images)]
        for nom in OBLIGATOIRES:
            for taille in sorted(TAILLES):
                with self.subTest(curseur=nom, taille=taille):
                    res = lib.XcursorFilenameLoadImages(self.fichier(nom).encode(), taille)
                    self.assertTrue(res, "libXcursor refuse le fichier")
                    ims = res.contents
                    self.assertGreaterEqual(ims.nimage, 1)
                    first = ims.images[0].contents
                    self.assertEqual((first.size, first.width, first.height), (taille, taille, taille))
                    if nom in ANIMES:
                        self.assertGreaterEqual(ims.nimage, 8)
                    lib.XcursorImagesDestroy(res)


if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        THEME = sys.argv.pop(1)
    unittest.main(verbosity=1)

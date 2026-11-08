"""Outils communs aux tests : dossiers temporaires isolés et variables XDG."""

import os
import shutil
import sys
import tempfile
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def xattr_disponible(dossier):
    chemin = os.path.join(dossier, ".essai-xattr")
    with open(chemin, "w"):
        pass
    try:
        os.setxattr(chemin, "user.essai", b"1")
        return True
    except OSError:
        return False
    finally:
        os.unlink(chemin)


class TestAvecDossier(unittest.TestCase):
    """Fournit self.tmp et des XDG_* qui pointent dedans."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fichiers-test-")
        self._env = {k: os.environ.get(k) for k in ("XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME")}
        for k, sous in (("XDG_DATA_HOME", "data"), ("XDG_CACHE_HOME", "cache"), ("XDG_CONFIG_HOME", "config")):
            os.environ[k] = os.path.join(self.tmp, sous)
            os.makedirs(os.environ[k], exist_ok=True)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ecrire(self, chemin_relatif, contenu="x"):
        chemin = os.path.join(self.tmp, chemin_relatif)
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        mode = "wb" if isinstance(contenu, bytes) else "w"
        with open(chemin, mode) as f:
            f.write(contenu)
        return chemin

    def lire(self, chemin):
        with open(chemin) as f:
            return f.read()

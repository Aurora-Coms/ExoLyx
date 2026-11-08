"""Miniatures (cache freedesktop ~/.cache/thumbnails) et aperçus d'images, PDF, vidéos, textes."""

import hashlib
import os
import shutil
import subprocess
import tempfile
import urllib.parse

from PyQt6.QtCore import QBuffer, QByteArray, QSize, Qt, QUrl
from PyQt6.QtGui import QColor, QImage, QImageReader
from PyQt6.QtQuick import QQuickImageProvider

LOGICIEL = "ExoLyx Fichiers"
TAILLE_MAX_IMAGE = 150 * 1024 * 1024
CLASSES = [(128, "normal"), (256, "large"), (512, "x-large"), (1024, "xx-large")]

try:  # QtPdf (fourni par qt6-webengine sur Arch) si les liaisons existent
    from PyQt6.QtPdf import QPdfDocument  # type: ignore
except ImportError:  # pragma: no cover - dépend de l'installation
    QPdfDocument = None

_formats = None


def formats_image():
    global _formats
    if _formats is None:
        _formats = {bytes(f).decode().lower() for f in QImageReader.supportedImageFormats()}
    return _formats


def outil(nom):
    return shutil.which(nom)


def pdf_disponible():
    return QPdfDocument is not None or outil("pdftoppm") is not None


def peut_miniaturiser(categorie, nom, taille):
    ext = os.path.splitext(nom)[1].lower().lstrip(".")
    if categorie == "image":
        return ext in formats_image() and taille < TAILLE_MAX_IMAGE
    if categorie == "pdf":
        return pdf_disponible()
    if categorie == "video":
        return outil("ffmpegthumbnailer") is not None
    return False


def dossier_miniatures():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "thumbnails")


def uri_de(chemin):
    return bytes(QUrl.fromLocalFile(os.path.abspath(chemin)).toEncoded()).decode("ascii")


def chemin_miniature(chemin, taille=256):
    """Chemin du fichier de cache selon la spécification (md5 de l'URI)."""
    classe = next((c for t, c in CLASSES if taille <= t), CLASSES[-1][1])
    nom = hashlib.md5(uri_de(chemin).encode("ascii")).hexdigest() + ".png"
    return os.path.join(dossier_miniatures(), classe, nom), dict((c, t) for t, c in CLASSES)[classe]


# --- rendu brut -------------------------------------------------------------

def rendre_image(chemin, cote):
    lecteur = QImageReader(chemin)
    lecteur.setAutoTransform(True)
    taille = lecteur.size()
    if taille.isValid() and (taille.width() > cote or taille.height() > cote):
        lecteur.setScaledSize(taille.scaled(cote, cote, Qt.AspectRatioMode.KeepAspectRatio))
    image = lecteur.read()
    return image if not image.isNull() else None


def nombre_pages_pdf(chemin):
    if QPdfDocument is not None:
        doc = QPdfDocument()
        doc.load(chemin)
        n = doc.pageCount()
        doc.close()
        return n
    if outil("pdfinfo"):
        try:
            sortie = subprocess.run(["pdfinfo", chemin], capture_output=True, text=True, timeout=10).stdout
            for ligne in sortie.splitlines():
                if ligne.startswith("Pages:"):
                    return int(ligne.split()[1])
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    return 1


def rendre_pdf(chemin, cote, page=0):
    if QPdfDocument is not None:
        doc = QPdfDocument()
        doc.load(chemin)
        if doc.pageCount() > page:
            t = doc.pagePointSize(page)
            echelle = cote / max(t.width(), t.height(), 1)
            image = doc.render(page, QSize(int(t.width() * echelle), int(t.height() * echelle)))
            doc.close()
            if not image.isNull():
                return fond_blanc(image)
    if outil("pdftoppm"):
        try:
            sortie = subprocess.run(
                ["pdftoppm", "-f", str(page + 1), "-l", str(page + 1), "-scale-to", str(cote),
                 "-png", "-singlefile", chemin],
                capture_output=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        image = QImage()
        if image.loadFromData(sortie, "PNG"):
            return image
    return None


def rendre_video(chemin, cote):
    if not outil("ffmpegthumbnailer"):
        return None
    with tempfile.TemporaryDirectory(prefix="exolyx-") as d:
        sortie = os.path.join(d, "m.png")
        try:
            subprocess.run(["ffmpegthumbnailer", "-i", chemin, "-o", sortie, "-s", str(cote), "-c", "png"],
                           capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        image = QImage(sortie)
        return image if not image.isNull() else None


def fond_blanc(image):
    """Les pages PDF transparentes sont posées sur du blanc."""
    resultat = QImage(image.size(), QImage.Format.Format_RGB32)
    resultat.fill(QColor("white"))
    from PyQt6.QtGui import QPainter
    p = QPainter(resultat)
    p.drawImage(0, 0, image)
    p.end()
    return resultat


def rendre(chemin, cote, page=0):
    ext = os.path.splitext(chemin)[1].lower()
    if ext == ".pdf":
        return rendre_pdf(chemin, cote, page)
    if ext.lstrip(".") in formats_image():
        return rendre_image(chemin, cote)
    from modele import classifieur
    cat = classifieur().classer(os.path.basename(chemin), False)[1]
    if cat == "video":
        return rendre_video(chemin, cote)
    if cat == "image":
        return rendre_image(chemin, cote)
    return None


# --- cache freedesktop ------------------------------------------------------

def miniature(chemin, taille=256):
    """QImage de la miniature (depuis le cache si à jour, sinon générée et enregistrée)."""
    try:
        st = os.stat(chemin)
    except OSError:
        return None
    racine = dossier_miniatures()
    fichier, cote = chemin_miniature(chemin, taille)
    mtime = str(int(st.st_mtime))
    # NB : QImageReader.text() découpe les clés sur « : » ; QImage lit bien « Thumb::MTime »
    if os.path.exists(fichier):
        image = QImage(fichier)
        if not image.isNull() and image.text("Thumb::MTime") == mtime:
            return image
    echec = os.path.join(racine, "fail", "exolyx-fichiers-1.0", os.path.basename(fichier))
    if os.path.exists(echec) and QImage(echec).text("Thumb::MTime") == mtime:
        return None
    image = rendre(chemin, cote)
    dans_cache = os.path.realpath(chemin).startswith(os.path.realpath(racine) + os.sep)
    if dans_cache:
        return image  # jamais de miniature de miniature
    if image is None:
        vide = QImage(1, 1, QImage.Format.Format_ARGB32)
        vide.fill(0)
        _enregistrer(vide, echec, chemin, st, mtime)
        return None
    if image.width() > cote or image.height() > cote:
        image = image.scaled(cote, cote, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    _enregistrer(image, fichier, chemin, st, mtime)
    return image


def _enregistrer(image, fichier, chemin, st, mtime):
    try:
        os.makedirs(os.path.dirname(fichier), mode=0o700, exist_ok=True)
        image.setText("Thumb::URI", uri_de(chemin))
        image.setText("Thumb::MTime", mtime)
        image.setText("Thumb::Size", str(st.st_size))
        image.setText("Software", LOGICIEL)
        fd, temporaire = tempfile.mkstemp(dir=os.path.dirname(fichier), suffix=".png")
        os.close(fd)
        if image.save(temporaire, "PNG"):
            os.chmod(temporaire, 0o600)
            os.replace(temporaire, fichier)
        else:
            os.unlink(temporaire)
    except OSError:
        pass


def texte(chemin, limite=24000):
    """Début d'un fichier texte, ou None s'il semble binaire."""
    try:
        with open(chemin, "rb") as f:
            brut = f.read(limite)
    except OSError:
        return None
    if b"\x00" in brut[:4096]:
        return None
    t = brut.decode("utf-8", "replace")
    return t + ("\n…" if len(brut) == limite else "")


# --- fournisseurs d'images QML ----------------------------------------------

def _decoder_id(ident):
    ident = ident.split("?", 1)[0]
    return urllib.parse.unquote(ident)


class FournisseurMiniatures(QQuickImageProvider):
    """image://miniature/<chemin encodé>?<mtime> ; sourceSize donne la taille voulue."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, ident, taille_demandee):
        chemin = _decoder_id(ident)
        cote = max(taille_demandee.width(), taille_demandee.height(), 128) if taille_demandee.isValid() else 256
        image = miniature(chemin, 256 if cote <= 256 else 512) or QImage()
        if not image.isNull() and (image.width() > cote or image.height() > cote):
            image = image.scaled(cote, cote, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        return image, image.size()


class FournisseurApercu(QQuickImageProvider):
    """image://apercu/<chemin encodé>?page=N : rendu direct grand format, sans cache."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, ident, taille_demandee):
        chemin = _decoder_id(ident)
        page = 0
        if "?" in ident:
            params = urllib.parse.parse_qs(ident.split("?", 1)[1])
            try:
                page = int(params.get("page", ["0"])[0])
            except ValueError:
                page = 0
        cote = max(taille_demandee.width(), taille_demandee.height()) if taille_demandee.isValid() else 1024
        cote = max(cote, 256)
        image = rendre(chemin, cote, page) or QImage()
        return image, image.size()


def image_en_png(image):
    """Utilitaire de test : QImage -> octets PNG."""
    tableau = QByteArray()
    tampon = QBuffer(tableau)
    tampon.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(tampon, "PNG")
    return bytes(tableau)

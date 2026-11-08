"""Icônes de l'appli, dessinées en SVG (compatible QtSvg, sans filtre) et teintées à la demande.

URL QML :
  image://icone/g/<glyphe>/<RRGGBB>      pictogramme au trait (grille 24)
  image://icone/t/<categorie>/<0|1>      icône de type de fichier (1 = thème clair)
  image://icone/d/<emblème>/<0|1>        dossier, avec emblème facultatif (documents, images…)
"""

from PyQt6.QtCore import QByteArray, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtQuick import QQuickImageProvider
from PyQt6.QtSvg import QSvgRenderer

from config import PALETTE


def _point(x, y, r=1.15):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{{c}}" stroke="none"/>'


GLYPHES = {
    "retour": '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    "avancer": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "haut": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "rafraichir": '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3M19.5 4.5v4.5H15"/>',
    "recherche": '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.4-4.4"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "couper": '<circle cx="6.5" cy="6.5" r="2.8"/><circle cx="6.5" cy="17.5" r="2.8"/>'
              '<path d="M20 5L8.6 15.4M14.2 13.8L20 19M8.6 8.6l3.2 2.9"/>',
    "copier": '<rect x="9" y="9" width="11" height="11" rx="2"/>'
              '<path d="M15 5.5V5a1.5 1.5 0 0 0-1.5-1.5h-8A1.5 1.5 0 0 0 4 5v8.5A1.5 1.5 0 0 0 5.5 15H6"/>',
    "coller": '<rect x="8.5" y="2.5" width="7" height="4" rx="1"/>'
              '<path d="M15.5 4.5h2a2 2 0 0 1 2 2V19a2 2 0 0 1-2 2h-11a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2h2"/>',
    "renommer": '<path d="M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4"/>',
    "supprimer": '<path d="M4 7h16M9.5 11v6M14.5 11v6M6 7l1 12.5A1.5 1.5 0 0 0 8.5 21h7a1.5 1.5 0 0 0 1.5-1.5L18 7'
                 'M9 7V4.5A1.5 1.5 0 0 1 10.5 3h3A1.5 1.5 0 0 1 15 4.5V7"/>',
    "proprietes": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/>' + _point(12, 7.6),
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M7.5 9.5l3 2.5-3 2.5M13 15h3.5"/>',
    "grille": '<rect x="4" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5"/>'
              '<rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5"/>',
    "liste": '<path d="M9 6h11M9 12h11M9 18h11"/>' + _point(4.5, 6) + _point(4.5, 12) + _point(4.5, 18),
    "tri": '<path d="M7 4v16M3.5 16.5L7 20l3.5-3.5M17 20V4M13.5 7.5L17 4l3.5 3.5"/>',
    "accueil": '<path d="M3.5 11L12 4l8.5 7M5.5 9.5V19a1 1 0 0 0 1 1H10v-5.5h4V20h3.5a1 1 0 0 0 1-1V9.5"/>',
    "epingle": '<path d="M12 16.5V21M8.5 3.5h7l-1 5.5 3.5 4v1.5H6V13l3.5-4z"/>',
    "lecteur": '<rect x="3" y="13" width="18" height="7" rx="2"/><path d="M4.5 13l2.6-7.2A1.5 1.5 0 0 1 8.5 5h7a1.5 1.5 0 0 1 1.4.8L19.5 13"/>'
               + _point(16.5, 16.5),
    "usb": '<rect x="7" y="9" width="10" height="12.5" rx="2"/><path d="M9 9V3h6v6"/>' + _point(10.8, 6, 0.9) + _point(13.2, 6, 0.9),
    "etiquette": '<path d="M3.5 12.2V5A1.5 1.5 0 0 1 5 3.5h7.2l8.3 8.3a1.5 1.5 0 0 1 0 2.1l-6.6 6.6a1.5 1.5 0 0 1-2.1 0z"/>'
                 '<circle cx="8" cy="8" r="1.6"/>',
    "parametres": '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2.2"/><circle cx="9" cy="17" r="2.2"/>',
    "fermer": '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    "reduire": '<path d="M6 12.5h12"/>',
    "agrandir": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "restaurer": '<rect x="5" y="9" width="10" height="10" rx="1.8"/><path d="M9 6.5A1.5 1.5 0 0 1 10.5 5h7A1.5 1.5 0 0 1 19 6.5v7a1.5 1.5 0 0 1-1.5 1.5"/>',
    "apercu": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    "chevron": '<path d="M9.5 6l6 6-6 6"/>',
    "chevronGauche": '<path d="M14.5 6l-6 6 6 6"/>',
    "chevronBas": '<path d="M6 9.5l6 6 6-6"/>',
    "ejecter": '<path d="M5 14.5h14L12 6zM5 19h14"/>',
    "dossier": '<path d="M3 7.5A2.5 2.5 0 0 1 5.5 5h3.6l2.2 2.2h7.2A2.5 2.5 0 0 1 21 9.7v7.8a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z"/>',
    "dossierPlus": '<path d="M3 7.5A2.5 2.5 0 0 1 5.5 5h3.6l2.2 2.2h7.2A2.5 2.5 0 0 1 21 9.7v7.8a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z'
                   'M12 10.5v6M9 13.5h6"/>',
    "fichier": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5"/>',
    "fichierPlus": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M12 11v6M9 14h6"/>',
    "documents": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h6"/>',
    "images": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="8.5" cy="9.5" r="1.8"/><path d="M21 15.5l-5-5L6 20"/>',
    "musique": '<path d="M9 17.5V5.5l11-2v12"/><circle cx="6.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="15.5" r="2.5"/>',
    "videos": '<rect x="3" y="5.5" width="13" height="13" rx="2.5"/><path d="M16 10.5l5-3v9l-5-3"/>',
    "telechargements": '<path d="M12 4v11M7 10.5l5 5 5-5M5 20h14"/>',
    "bureau": '<rect x="3" y="4" width="18" height="12.5" rx="2"/><path d="M8.5 20.5h7M12 16.5v4"/>',
    "annuler": '<path d="M9 14.5L4 9.5l5-5M4 9.5h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "coche": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "attention": '<path d="M12 3.5l9.5 16.5h-19z"/><path d="M12 10v4.5"/>' + _point(12, 17.3),
    "points": _point(5.5, 12, 1.5) + _point(12, 12, 1.5) + _point(18.5, 12, 1.5),
    "recents": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "ouvrir": '<path d="M14 4h6v6M20 4l-8.5 8.5M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
    "lien": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3A4 4 0 0 0 13 5.3l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 18.7l1-1"/>',
    "theme": '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17A8.5 8.5 0 0 0 12 3.5z" fill="{c}"/>',
    "oeilBarre": '<path d="M3 3l18 18M10.6 5.6A10 10 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.8 3.6M6.3 6.9A16.5 16.5 0 0 0 2.5 12S6 18.5 12 18.5a9.6 9.6 0 0 0 4.4-1.1M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    "croixCercle": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "texte": '<path d="M5 6h14M5 10h14M5 14h14M5 18h9"/>',
}

# Couleur du pictogramme posé sur les icônes de type
COULEUR_TYPE = {
    "image": "info", "video": "erreur", "audio": "attention", "pdf": "erreur", "archive": "attention",
    "code": "accentFroid", "texte": "texteDoux", "document": "info", "tableur": "accent",
    "presentation": "attention", "executable": "accent", "disque": "texteDoux", "fichier": "texteDoux",
    "lien": "info",
}
GLYPHE_TYPE = {
    "image": "images", "video": "videos", "audio": "musique", "pdf": "documents", "archive": "archive",
    "code": "code", "texte": "texte", "document": "texte", "tableur": "tableur", "presentation": "presentation",
    "executable": "terminal", "disque": "disque", "fichier": None, "lien": "lien",
}
GLYPHES.update({
    "archive": '<rect x="4" y="4" width="16" height="16" rx="2.5"/><path d="M12 4v3M12 9v2M12 13v2"/><rect x="10" y="15" width="4" height="4" rx="1"/>',
    "code": '<path d="M8.5 7.5L4 12l4.5 4.5M15.5 7.5L20 12l-4.5 4.5M13.5 5l-3 14"/>',
    "tableur": '<rect x="4" y="4" width="16" height="16" rx="2.5"/><path d="M4 9.5h16M4 14.5h16M10 4v16"/>',
    "presentation": '<rect x="3.5" y="4.5" width="17" height="11" rx="2"/><path d="M12 15.5v4M8.5 20h7"/>',
    "disque": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="2.5"/>',
})


def _svg_glyphe(nom, couleur, epaisseur=1.8):
    corps = GLYPHES.get(nom, GLYPHES["fichier"]).replace("{c}", couleur)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{couleur}" '
            f'stroke-width="{epaisseur}" stroke-linecap="round" stroke-linejoin="round">{corps}</svg>')


def _melanger(a, b, t):
    ca, cb = QColor(a), QColor(b)
    return QColor(round(ca.red() + (cb.red() - ca.red()) * t), round(ca.green() + (cb.green() - ca.green()) * t),
                  round(ca.blue() + (cb.blue() - ca.blue()) * t)).name()


def _c(jeton, clair):
    return PALETTE[jeton][1 if clair else 0]


def svg_dossier(embleme, clair):
    accent = _c("accent", clair)
    haut = _c("accentClair", clair)
    dos = _melanger(accent, "#000000", 0.30 if not clair else 0.22)
    trait = _melanger(accent, "#000000", 0.55)
    embl = ""
    if embleme and embleme in GLYPHES:
        corps = GLYPHES[embleme].replace("{c}", trait)
        embl = (f'<g transform="translate(22 27) scale(0.84)" fill="none" stroke="{trait}" stroke-width="2.2" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity="0.75">{corps}</g>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{haut}"/><stop offset="1" stop-color="{accent}"/></linearGradient></defs>
  <path d="M5 15a4 4 0 0 1 4-4h13.5a4 4 0 0 1 2.8 1.2l3.4 3.4h26.3a4 4 0 0 1 4 4V50a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4z" fill="{dos}"/>
  <path d="M5 23.5a4 4 0 0 1 4-4h46a4 4 0 0 1 4 4V50a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4z" fill="url(#f)"/>
  <path d="M9 21.5h46" stroke="#FFFFFF" stroke-opacity="0.35" stroke-width="1.5" stroke-linecap="round"/>
  {embl}
</svg>'''


def svg_type(categorie, clair):
    page = _c("surface", clair) if clair else _c("surfaceHaute", clair)
    bord = _c("bordure", clair) if clair else _melanger(_c("bordure", clair), "#FFFFFF", 0.08)
    pli = _melanger(page, _c("bordure", clair), 0.6)
    couleur = _c(COULEUR_TYPE.get(categorie, "texteDoux"), clair)
    glyphe = GLYPHE_TYPE.get(categorie)
    g = ""
    if glyphe:
        corps = GLYPHES[glyphe].replace("{c}", couleur)
        g = (f'<g transform="translate(19 25) scale(1.08)" fill="none" stroke="{couleur}" stroke-width="2" '
             f'stroke-linecap="round" stroke-linejoin="round">{corps}</g>')
    bande = f'<rect x="11" y="49" width="38" height="4" rx="2" fill="{couleur}" opacity="0.85"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <path d="M15 5h22.2a3 3 0 0 1 2.1.9l12.8 12.8a3 3 0 0 1 .9 2.1V55a4 4 0 0 1-4 4H15a4 4 0 0 1-4-4V9a4 4 0 0 1 4-4z"
        fill="{page}" stroke="{bord}" stroke-width="1.5"/>
  <path d="M38 5.5V15a4 4 0 0 0 4 4h10.5" fill="{pli}" stroke="{bord}" stroke-width="1.5" stroke-linejoin="round"/>
  {g}
  {bande}
</svg>'''


def rendre_svg(svg, taille):
    rendu = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    image = QImage(taille, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    rendu.render(p, QRectF(0, 0, taille.width(), taille.height()))
    p.end()
    return image


def svg_pour(ident):
    morceaux = ident.split("?", 1)[0].split("/")
    genre = morceaux[0]
    nom = morceaux[1] if len(morceaux) > 1 else ""
    param = morceaux[2] if len(morceaux) > 2 else ""
    if genre == "g":
        couleur = "#" + param if param else "#97A893"
        return _svg_glyphe(nom, couleur)
    clair = param == "1"
    if genre == "d":
        return svg_dossier(nom, clair)
    return svg_type(nom, clair)


class FournisseurIcones(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, ident, taille_demandee):
        taille = taille_demandee if taille_demandee.isValid() and taille_demandee.width() > 0 else QSize(64, 64)
        if taille.height() <= 0:
            taille = QSize(taille.width(), taille.width())
        image = rendre_svg(svg_pour(ident), taille)
        return image, image.size()

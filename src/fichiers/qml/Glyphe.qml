import QtQuick
import QtQuick.Window

// Pictogramme au trait, teinté par le fournisseur d'icônes
Image {
    id: racine
    property string nom: "fichier"
    property string couleur: theme.texte
    property real taille: 18
    width: taille
    height: taille
    source: nom ? "image://icone/g/" + nom + "/" + couleur.replace("#", "") : ""
    sourceSize: Qt.size(Math.ceil(taille * Screen.devicePixelRatio), Math.ceil(taille * Screen.devicePixelRatio))
    smooth: true
    cache: true
}

import QtQuick

// Barre de remplissage (espace disque, progression)
Rectangle {
    id: racine
    property real valeur: 0
    property string couleurRemplie: valeur > 0.9 ? theme.erreur : valeur > 0.75 ? theme.attention : theme.accent
    implicitHeight: 6
    radius: height / 2
    color: theme.bordure
    Rectangle {
        width: Math.max(racine.valeur > 0 ? racine.height : 0, parent.width * Math.min(1, racine.valeur))
        height: parent.height
        radius: parent.radius
        color: racine.couleurRemplie
        Behavior on width { NumberAnimation { duration: 160 } }
    }
}

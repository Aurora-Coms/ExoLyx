import QtQuick
import QtQuick.Controls.Basic

// Bouton plat : pictogramme, texte facultatif, info-bulle
Rectangle {
    id: racine
    property string icone: ""
    property string texte: ""
    property string bulle: ""
    property bool actif: true
    property bool coche: false
    property bool fleche: false
    property string couleurIcone: coche ? theme.accent : theme.texte
    property string couleurTexte: theme.texte
    property real tailleIcone: 18
    property bool survol: zone.containsMouse
    signal clique()
    signal cliqueDroit()

    implicitHeight: 32
    implicitWidth: texte ? contenu.implicitWidth + 20 : 32
    radius: 6
    opacity: actif ? 1 : 0.38
    color: zone.pressed && actif ? theme.bordure
         : coche ? Qt.alpha(theme.accent, 0.16)
         : survol && actif ? theme.surfaceHaute : "transparent"
    Behavior on color { ColorAnimation { duration: 90 } }

    Row {
        id: contenu
        anchors.centerIn: parent
        spacing: 7
        Glyphe {
            nom: racine.icone
            taille: racine.tailleIcone
            couleur: racine.couleurIcone
            visible: racine.icone !== ""
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: racine.texte
            visible: racine.texte !== ""
            color: racine.couleurTexte
            font.pixelSize: 13
            anchors.verticalCenter: parent.verticalCenter
        }
        Glyphe {
            nom: "chevronBas"
            taille: 12
            couleur: racine.couleurTexte === theme.texte ? theme.texteDoux : racine.couleurTexte
            visible: racine.fleche
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        id: zone
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: (souris) => {
            if (!racine.actif) return
            if (souris.button === Qt.RightButton) racine.cliqueDroit()
            else racine.clique()
        }
    }

    InfoBulle {
        visible: zone.containsMouse && racine.bulle !== "" && !zone.pressed
        text: racine.bulle
    }
}

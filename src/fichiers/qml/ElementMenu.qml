import QtQuick
import QtQuick.Controls.Basic

MenuItem {
    id: element
    property string icone: ""
    property string raccourci: ""
    property bool danger: false
    property string pastille: ""      // couleur d'une étiquette, le cas échéant
    implicitHeight: visible ? 32 : 0
    height: visible ? implicitHeight : 0
    implicitWidth: 262
    padding: 0
    arrow: null
    indicator: null
    contentItem: Item {
        implicitHeight: 32
        Rectangle {
            id: puce
            visible: element.pastille !== ""
            width: 10; height: 10; radius: 5
            color: element.pastille
            x: 13
            anchors.verticalCenter: parent.verticalCenter
        }
        Glyphe {
            id: glyphe
            x: 10
            anchors.verticalCenter: parent.verticalCenter
            nom: element.checkable ? (element.checked ? "coche" : "") : element.icone
            visible: nom !== "" && !puce.visible
            taille: 16
            couleur: element.danger ? theme.erreur : element.checked ? theme.accent : theme.texteDoux
        }
        Rectangle {
            visible: element.checkable && element.checked && puce.visible
            x: 10; width: 16; height: 16; radius: 8
            color: "transparent"; border.color: theme.accent; border.width: 1.5
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            x: 36
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - x - (raccourciTexte.visible ? raccourciTexte.width + 12 : 0) - (fleche.visible ? 22 : 12)
            text: element.text
            elide: Text.ElideRight
            font.pixelSize: 13
            color: !element.enabled ? Qt.alpha(theme.texte, 0.38) : element.danger ? theme.erreur : theme.texte
        }
        Text {
            id: raccourciTexte
            visible: element.raccourci !== ""
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: element.raccourci
            font.pixelSize: 11
            color: theme.texteDoux
        }
        Glyphe {
            id: fleche
            visible: element.subMenu !== null
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            nom: "chevron"
            taille: 14
            couleur: theme.texteDoux
        }
    }
    background: Rectangle {
        implicitHeight: 32
        radius: 6
        color: element.highlighted && element.enabled ? (element.danger ? Qt.alpha(theme.erreur, 0.14) : theme.surfaceHaute) : "transparent"
    }
}

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Base des boîtes de dialogue : modale, centrée, titrée
Popup {
    id: dialogue
    property string titre: ""
    default property alias contenu: zoneContenu.data
    property alias boutons: zoneBoutons.data
    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(460, (parent ? parent.width : 460) - 48)
    padding: 22
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    Overlay.modal: Rectangle { color: Qt.alpha("#000000", theme.clair ? 0.25 : 0.5) }
    background: Rectangle {
        color: theme.surface
        border.color: theme.bordure
        radius: 14
    }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 }
        NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 120; easing.type: Easing.OutCubic }
    }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 90 } }

    contentItem: ColumnLayout {
        spacing: 16
        Text {
            text: dialogue.titre
            visible: text !== ""
            font.pixelSize: 17
            font.weight: Font.DemiBold
            color: theme.texte
            Layout.fillWidth: true
            elide: Text.ElideRight
        }
        ColumnLayout {
            id: zoneContenu
            spacing: 10
            Layout.fillWidth: true
        }
        RowLayout {
            id: zoneBoutons
            spacing: 8
            Layout.alignment: Qt.AlignRight
            Layout.topMargin: 4
        }
    }
}

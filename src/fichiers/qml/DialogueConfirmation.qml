import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Dialogue {
    id: dialogue
    property string message: ""
    property string texteValider: "Supprimer"
    property var action: null

    function demander(titre, message, bouton, fonction) {
        dialogue.titre = titre
        dialogue.message = message
        texteValider = bouton
        action = fonction
        open()
    }
    onOpened: boutonValider.forceActiveFocus()

    Text {
        text: dialogue.message
        color: theme.texteDoux
        font.pixelSize: 13
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    boutons: [
        Bouton { texte: "Annuler"; onClique: dialogue.close() },
        Bouton {
            id: boutonValider
            texte: dialogue.texteValider
            danger: true
            focus: true
            Keys.onReturnPressed: { dialogue.close(); if (dialogue.action) dialogue.action() }
            onClique: { dialogue.close(); if (dialogue.action) dialogue.action() }
        }
    ]
}

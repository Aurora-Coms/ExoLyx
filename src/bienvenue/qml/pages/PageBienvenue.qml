// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import "../composants"

Item {
    id: page
    readonly property var p: ctrl.palette

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width, 620)
        spacing: 18

        Image {
            Layout.alignment: Qt.AlignHCenter
            source: ctrl.logo
            Layout.preferredWidth: 190; Layout.preferredHeight: 190
            sourceSize: Qt.size(380, 380)
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Bienvenue dans ExoLyx"
            color: page.p.texte
            font.pixelSize: 34; font.weight: Font.Bold
        }
        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: page.p.texteDoux
            font.pixelSize: 16
            lineHeight: 1.2
            text: ctrl.live
                ? "Vous utilisez ExoLyx depuis la clé USB, sans rien modifier sur cet ordinateur. Quand vous êtes prêt, installez-le en quelques minutes."
                : "Votre système est prêt. En quelques étapes, choisissez son apparence, installez les pilotes utiles et vos applications préférées."
        }
        Item { Layout.preferredHeight: 6 }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 14
            Bouton {
                visible: ctrl.live
                principal: true; grand: true
                text: "Installer ExoLyx"
                onClicked: ctrl.lancerInstallateur()
            }
            Bouton {
                grand: true
                principal: !ctrl.live
                text: ctrl.live ? "Découvrir d'abord" : "Commencer"
                onClicked: ctrl.suivant()
            }
        }
    }
}

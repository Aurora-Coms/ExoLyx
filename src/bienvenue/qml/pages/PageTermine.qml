// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import "../composants"

Item {
    id: page
    readonly property var p: ctrl.palette

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width, 640)
        spacing: 18

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 84; height: 84; radius: 42
            color: page.p.accentVoile
            Rectangle {
                anchors.centerIn: parent; width: 58; height: 58; radius: 29; color: page.p.accent
                Text { anchors.centerIn: parent; text: "✓"; color: page.p.surAccent; font.pixelSize: 30; font.bold: true }
            }
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: ctrl.live ? "Prêt à installer ?" : "Tout est prêt !"
            color: page.p.texte; font.pixelSize: 32; font.weight: Font.Bold
        }
        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
            color: page.p.texteDoux; font.pixelSize: 16; lineHeight: 1.2
            text: ctrl.live
                ? "Lancez l'installation quand vous le souhaitez : vos réglages pourront être refaits au premier démarrage du système installé."
                : "Profitez d'ExoLyx ! Les mises à jour vous seront proposées automatiquement, et un instantané de sécurité est créé avant chacune d'elles."
        }

        Bouton {
            visible: ctrl.live
            Layout.alignment: Qt.AlignHCenter
            principal: true; grand: true
            text: "Installer ExoLyx"
            onClicked: ctrl.lancerInstallateur()
        }

        // Liens
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 8
            spacing: 14
            Repeater {
                model: [ { id: "aide", titre: "Aide et documentation", sous: "Guides pas à pas" },
                         { id: "depot", titre: "Dépôt GitHub", sous: "Code source, signaler un problème" } ]
                delegate: Rectangle {
                    id: lien
                    required property var modelData
                    width: 250; height: 66; radius: 10
                    color: zl.containsMouse ? page.p.surfaceHaute : page.p.surface
                    border.color: zl.containsMouse ? page.p.accent : page.p.bordure
                    Column {
                        anchors.verticalCenter: parent.verticalCenter; x: 16
                        Text { text: lien.modelData.titre + "  ↗"; color: page.p.texte; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Text { text: lien.modelData.sous; color: page.p.texteDoux; font.pixelSize: 12 }
                    }
                    MouseArea { id: zl; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: ctrl.ouvrirLien(lien.modelData.id) }
                }
            }
        }

        Item {
            visible: !ctrl.live
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 6
            implicitWidth: ligneCase.implicitWidth
            implicitHeight: ligneCase.implicitHeight
            Row {
                id: ligneCase
                spacing: 10
                Case { coche: ctrl.afficherAuDemarrage; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Afficher cet assistant à chaque démarrage"; color: page.p.texteDoux; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: ctrl.afficherAuDemarrage = !ctrl.afficherAuDemarrage
            }
        }
    }
}

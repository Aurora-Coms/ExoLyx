// SPDX-License-Identifier: GPL-3.0-or-later
// Bienvenue dans ExoLyx — fenêtre principale.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "composants"

ApplicationWindow {
    id: fenetre
    readonly property var p: ctrl.palette
    readonly property var pages: ({
        "Bienvenue": "pages/PageBienvenue.qml",
        "Apparence": "pages/PageApparence.qml",
        "Pilotes": "pages/PagePilotes.qml",
        "Applications": "pages/PageApplis.qml",
        "Terminé": "pages/PageTermine.qml"
    })
    readonly property bool derniere: ctrl.etape === ctrl.etapes.length - 1

    width: 1060; height: 680
    minimumWidth: 900; minimumHeight: 600
    visible: true
    title: "Bienvenue dans ExoLyx"
    color: p.fond
    font.family: "Inter"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ---- Barre latérale ------------------------------------------------
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 250
            color: fenetre.p.surface

            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: fenetre.p.bordure }

            Column {
                anchors.fill: parent
                anchors.margins: 22
                spacing: 6

                Row {
                    spacing: 12
                    Image {
                        source: ctrl.logo
                        width: 44; height: 44
                        sourceSize: Qt.size(88, 88)
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text { text: "ExoLyx"; color: fenetre.p.texte; font.pixelSize: 20; font.weight: Font.Bold }
                        Text { text: "Premiers pas"; color: fenetre.p.texteDoux; font.pixelSize: 12 }
                    }
                }
                Item { width: 1; height: 26 }

                Repeater {
                    model: ctrl.etapes
                    delegate: Rectangle {
                        id: ligne
                        required property string modelData
                        required property int index
                        readonly property bool courante: index === ctrl.etape
                        readonly property bool faite: index < ctrl.etape
                        width: parent.width; height: 44; radius: 6
                        color: courante ? fenetre.p.accentVoile
                             : zone.containsMouse ? fenetre.p.surfaceHaute : "transparent"
                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            x: 10; spacing: 12
                            Rectangle {
                                width: 26; height: 26; radius: 13
                                color: ligne.courante || ligne.faite ? fenetre.p.accent : "transparent"
                                border.color: ligne.courante || ligne.faite ? fenetre.p.accent : fenetre.p.bordure
                                border.width: 2
                                Text {
                                    anchors.centerIn: parent
                                    text: ligne.faite ? "✓" : (ligne.index + 1)
                                    color: ligne.courante || ligne.faite ? fenetre.p.surAccent : fenetre.p.texteDoux
                                    font.pixelSize: 12; font.weight: Font.Bold
                                }
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: ligne.modelData
                                color: ligne.courante ? fenetre.p.texte : fenetre.p.texteDoux
                                font.pixelSize: 15
                                font.weight: ligne.courante ? Font.DemiBold : Font.Normal
                            }
                        }
                        MouseArea {
                            id: zone
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: !ctrl.occupe
                            cursorShape: Qt.PointingHandCursor
                            onClicked: ctrl.allerA(ligne.index)
                        }
                    }
                }
            }

            // Badge du mode live
            Rectangle {
                visible: ctrl.live
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 22 }
                height: 54; radius: 10
                color: fenetre.p.surfaceHaute
                border.color: fenetre.p.bordure
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    x: 14
                    Text { text: "Session live"; color: fenetre.p.accent; font.pixelSize: 13; font.weight: Font.DemiBold }
                    Text { text: "Rien n'est encore installé"; color: fenetre.p.texteDoux; font.pixelSize: 12 }
                }
            }
        }

        // ---- Contenu -----------------------------------------------------------
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Loader {
                id: page
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 36
                Layout.bottomMargin: 12
                source: fenetre.pages[ctrl.nomEtape]
                onLoaded: { item.opacity = 0; apparition.restart() }
                NumberAnimation { id: apparition; target: page.item; property: "opacity"; to: 1; duration: 220 }
            }

            // Barre de navigation
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 72
                color: "transparent"
                Rectangle { width: parent.width; height: 1; color: fenetre.p.bordure }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 36; anchors.rightMargin: 36
                    spacing: 12
                    Bouton {
                        text: "Précédent"
                        visible: ctrl.etape > 0
                        enabled: !ctrl.occupe
                        onClicked: ctrl.precedent()
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: (ctrl.etape + 1) + " / " + ctrl.etapes.length
                        color: fenetre.p.texteDoux
                        font.pixelSize: 13
                    }
                    Bouton {
                        principal: true
                        text: fenetre.derniere ? "Terminer" : "Suivant"
                        enabled: !ctrl.occupe
                        onClicked: fenetre.derniere ? ctrl.terminer() : ctrl.suivant()
                    }
                }
            }
        }
    }
}

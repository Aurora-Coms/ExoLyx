// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import "../composants"

Item {
    id: page
    readonly property var p: ctrl.palette

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

        Flickable {
            id: defil
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentHeight: colonne.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: colonne
                width: defil.width
                spacing: 16

                Titre {
                    Layout.fillWidth: true
                    titre: "Applications populaires"
                    sousTitre: "Cochez les applications à installer. Vous en trouverez des milliers d'autres dans Discover."
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: defil.width > 680 ? 3 : 2
                    columnSpacing: 12; rowSpacing: 12
                    Repeater {
                        model: ctrl.applis
                        delegate: Rectangle {
                            id: carte
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: 66
                            radius: 10
                            color: zone.containsMouse && !modelData.installe ? page.p.surfaceHaute : page.p.surface
                            border.color: modelData.coche ? page.p.accent : page.p.bordure
                            border.width: modelData.coche ? 2 : 1
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 12
                                Rectangle {
                                    Layout.preferredWidth: 40; Layout.preferredHeight: 40; radius: 10
                                    color: carte.modelData.couleur
                                    Text { anchors.centerIn: parent; text: carte.modelData.nom.charAt(0); color: "#0D1310"; font.pixelSize: 18; font.weight: Font.Bold }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        Text { Layout.fillWidth: true; text: carte.modelData.nom; color: page.p.texte; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideRight }
                                        Rectangle {
                                            implicitWidth: badge.implicitWidth + 10; implicitHeight: 17; radius: 4
                                            color: page.p.surfaceHaute
                                            Text { id: badge; anchors.centerIn: parent; text: carte.modelData.source; color: carte.modelData.source === "Flathub" ? page.p.info : page.p.texteDoux; font.pixelSize: 10 }
                                        }
                                    }
                                    Text { Layout.fillWidth: true; text: carte.modelData.installe ? "Installé" : carte.modelData.description; color: carte.modelData.installe ? page.p.accent : page.p.texteDoux; font.pixelSize: 12; elide: Text.ElideRight }
                                }
                                Case { coche: carte.modelData.coche || carte.modelData.installe; opacity: carte.modelData.installe ? 0.5 : 1 }
                            }
                            MouseArea {
                                id: zone
                                anchors.fill: parent; hoverEnabled: true
                                enabled: !ctrl.occupe && !carte.modelData.installe
                                cursorShape: Qt.PointingHandCursor
                                onClicked: ctrl.basculerAppli(carte.modelData.id)
                            }
                        }
                    }
                }

            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: ctrl.nombreApplis === 0 ? "Aucune application sélectionnée."
                    : ctrl.nombreApplis + (ctrl.nombreApplis > 1 ? " applications sélectionnées." : " application sélectionnée.")
                color: page.p.texteDoux; font.pixelSize: 13
            }
            Bouton {
                principal: true
                text: ctrl.nombreApplis > 0 ? "Installer (" + ctrl.nombreApplis + ")" : "Installer"
                enabled: !ctrl.occupe && ctrl.nombreApplis > 0
                onClicked: ctrl.installerApplis()
            }
        }

        PanneauTache { Layout.fillWidth: true }
    }
}

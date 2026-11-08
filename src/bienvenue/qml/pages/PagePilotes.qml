// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import "../composants"

Item {
    id: page
    readonly property var p: ctrl.palette
    readonly property int nbCoches: ctrl.pilotes.filter(x => x.coche).length

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
                    titre: "Pilotes"
                    sousTitre: "ExoLyx inclut les pilotes libres pour la plupart du matériel. Certains composants fonctionnent mieux avec un pilote supplémentaire."
                }

                // Matériel détecté
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: mat.implicitHeight + 28
                    radius: 10; color: page.p.surface; border.color: page.p.bordure
                    Column {
                        id: mat
                        x: 16; y: 14; width: parent.width - 32; spacing: 6
                        Text { text: "Matériel détecté"; color: page.p.texteDoux; font.pixelSize: 12; font.weight: Font.DemiBold; font.capitalization: Font.AllUppercase; font.letterSpacing: 0.8 }
                        Repeater {
                            model: ctrl.materiel
                            Text { required property string modelData; text: "•  " + modelData; color: page.p.texte; font.pixelSize: 14 }
                        }
                    }
                }

                // Pilotes proposés
                Repeater {
                    model: ctrl.pilotes
                    delegate: Rectangle {
                        id: carte
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: 86
                        radius: 10
                        color: page.p.surface
                        border.color: modelData.coche ? page.p.accent : page.p.bordure
                        border.width: modelData.coche ? 2 : 1
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 16; spacing: 14
                            Case { coche: carte.modelData.coche; visible: !carte.modelData.installe }
                            Text { visible: carte.modelData.installe; text: "✓"; color: page.p.accent; font.pixelSize: 20; font.bold: true }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 3
                                Text { text: carte.modelData.nom + (carte.modelData.installe ? " — installé" : ""); color: page.p.texte; font.pixelSize: 15; font.weight: Font.DemiBold }
                                Text { Layout.fillWidth: true; text: carte.modelData.description; color: page.p.texteDoux; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                Text { text: carte.modelData.paquets; color: page.p.texteDoux; opacity: 0.8; font.family: "JetBrains Mono"; font.pixelSize: 11 }
                            }
                        }
                        MouseArea {
                            anchors.fill: parent; enabled: !ctrl.occupe && !carte.modelData.installe
                            cursorShape: Qt.PointingHandCursor
                            onClicked: ctrl.basculerPilote(carte.modelData.id)
                        }
                    }
                }

                // Rien à proposer / remarques
                Rectangle {
                    Layout.fillWidth: true
                    visible: ctrl.pilotes.length === 0 || ctrl.remarques.length > 0
                    implicitHeight: rem.implicitHeight + 28
                    radius: 10
                    color: page.p.infoVoile
                    border.color: page.p.infoBord
                    Column {
                        id: rem
                        x: 16; y: 14; width: parent.width - 32; spacing: 6
                        Text {
                            width: parent.width; visible: ctrl.pilotes.length === 0
                            text: "Aucun pilote supplémentaire n'est nécessaire : votre matériel fonctionne avec les pilotes libres inclus."
                            color: page.p.texte; font.pixelSize: 14; wrapMode: Text.WordWrap
                        }
                        Repeater {
                            model: ctrl.remarques
                            Text { required property string modelData; width: rem.width; text: modelData; color: page.p.texte; font.pixelSize: 14; wrapMode: Text.WordWrap }
                        }
                    }
                }

            }
        }

        RowLayout {
            visible: ctrl.pilotes.length > 0
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: "Un mot de passe administrateur vous sera demandé. Redémarrez ensuite l'ordinateur."
                color: page.p.texteDoux; font.pixelSize: 13; wrapMode: Text.WordWrap
            }
            Bouton {
                principal: true
                text: "Installer les pilotes sélectionnés"
                enabled: !ctrl.occupe && page.nbCoches > 0
                onClicked: ctrl.installerPilotes()
            }
        }

        PanneauTache { Layout.fillWidth: true }
    }
}

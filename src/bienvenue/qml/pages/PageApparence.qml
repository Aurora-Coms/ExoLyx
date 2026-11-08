// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import "../composants"

Flickable {
    id: page
    readonly property var p: ctrl.palette
    contentHeight: colonne.implicitHeight
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    ColumnLayout {
        id: colonne
        width: page.width
        spacing: 16

        Titre {
            Layout.fillWidth: true
            titre: "Apparence"
            sousTitre: "Choisissez un thème et un style d'icônes. Les changements s'appliquent immédiatement, vous pourrez les modifier plus tard dans la Configuration du système."
        }

        Text { text: "Thème et fond d'écran"; color: page.p.texte; font.pixelSize: 17; font.weight: Font.DemiBold; Layout.topMargin: 6 }

        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            Repeater {
                model: [ { sombre: true, nom: "Sombre", desc: "Reposant pour les yeux, idéal le soir" },
                         { sombre: false, nom: "Clair", desc: "Lumineux et contrasté, idéal le jour" } ]
                delegate: Rectangle {
                    id: carte
                    required property var modelData
                    readonly property bool choisi: ctrl.sombre === modelData.sombre
                    readonly property var q: ({
                        fond: modelData.sombre ? "#0D1310" : "#F4F8F1",
                        surface: modelData.sombre ? "#141C17" : "#FFFFFF",
                        barre: modelData.sombre ? "#1C2620" : "#E9F0E4",
                        texte: modelData.sombre ? "#E6EFE1" : "#16201A",
                        doux: modelData.sombre ? "#97A893" : "#5B6B57",
                        accent: modelData.sombre ? "#A8D479" : "#5E9B2E"
                    })
                    Layout.fillWidth: true
                    Layout.preferredHeight: 200
                    radius: 10
                    color: page.p.surface
                    border.color: choisi ? page.p.accent : page.p.bordure
                    border.width: choisi ? 2 : 1

                    // aperçu du bureau
                    Rectangle {
                        id: apercu
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                        height: 124; radius: 8; clip: true
                        color: carte.q.fond
                        Image {
                            anchors.fill: parent
                            source: carte.modelData.sombre ? ctrl.fonds.sombre : ctrl.fonds.clair
                            fillMode: Image.PreserveAspectCrop
                            sourceSize.width: 480
                            asynchronous: true
                        }
                        // fenêtre miniature
                        Rectangle {
                            x: parent.width * 0.12; y: 16; width: parent.width * 0.5; height: 78; radius: 6
                            color: carte.q.surface; opacity: 0.96
                            Rectangle { width: parent.width; height: 14; radius: 6; color: carte.q.barre }
                            Column { x: 10; y: 24; spacing: 6
                                Rectangle { width: 70; height: 7; radius: 3; color: carte.q.texte }
                                Rectangle { width: 96; height: 6; radius: 3; color: carte.q.doux }
                                Rectangle { width: 44; height: 14; radius: 4; color: carte.q.accent } }
                        }
                        // panneau
                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width; height: 16
                            color: carte.q.surface; opacity: 0.94
                            Row { anchors.centerIn: parent; spacing: 6
                                Repeater { model: 5; Rectangle { width: 9; height: 9; radius: 3; color: index === 0 ? carte.q.accent : carte.q.doux } } }
                        }
                    }
                    Row {
                        anchors { left: parent.left; bottom: parent.bottom; margins: 14 }
                        spacing: 12
                        Case { coche: carte.choisi; anchors.verticalCenter: parent.verticalCenter }
                        Column {
                            Text { text: carte.modelData.nom; color: page.p.texte; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Text { text: carte.modelData.desc; color: page.p.texteDoux; font.pixelSize: 12 }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: ctrl.choisirTheme(carte.modelData.sombre)
                    }
                }
            }
        }

        Text { text: "Style d'icônes"; color: page.p.texte; font.pixelSize: 17; font.weight: Font.DemiBold; Layout.topMargin: 10 }

        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            Repeater {
                model: ctrl.stylesIcones
                delegate: Rectangle {
                    id: carteIc
                    required property var modelData
                    readonly property bool choisi: ctrl.styleIcones === modelData.nom
                    readonly property var icones: ctrl.apercus[modelData.nom] || []
                    Layout.fillWidth: true
                    Layout.preferredHeight: 136
                    radius: 10
                    color: page.p.surface
                    border.color: choisi ? page.p.accent : page.p.bordure
                    border.width: choisi ? 2 : 1

                    Rectangle {
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                        height: 66; radius: 8; clip: true
                        color: page.p.surfaceHaute
                        Row {
                            anchors.centerIn: parent
                            spacing: 8
                            visible: carteIc.icones.length > 0
                            Repeater {
                                model: carteIc.icones.slice(0, 4)
                                Image { required property string modelData; source: modelData; width: 34; height: 34; sourceSize: Qt.size(68, 68) }
                            }
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: carteIc.icones.length === 0
                            text: "Aperçu indisponible"
                            color: page.p.texteDoux; font.pixelSize: 12
                        }
                    }
                    Row {
                        anchors { left: parent.left; bottom: parent.bottom; margins: 14 }
                        spacing: 12
                        Case { coche: carteIc.choisi; anchors.verticalCenter: parent.verticalCenter }
                        Column {
                            Text { text: carteIc.modelData.nom; color: page.p.texte; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Text { text: carteIc.modelData.description; color: page.p.texteDoux; font.pixelSize: 12 }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: ctrl.choisirIcones(carteIc.modelData.nom)
                    }
                }
            }
        }
    }
}

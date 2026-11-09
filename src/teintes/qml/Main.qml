// SPDX-License-Identifier: GPL-3.0-or-later
// Teintes dynamiques — les couleurs d'ExoLyx suivent le fond d'écran.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: fen
    readonly property var p: ctrl.palette
    width: 980; height: 640
    minimumWidth: 760; minimumHeight: 560
    visible: true
    title: "Teintes dynamiques"
    color: p.fond
    font.family: "Inter"
    Behavior on color { ColorAnimation { duration: 250 } }

    component Titre: Text { color: fen.p.texte; font.pixelSize: 15; font.weight: Font.DemiBold }
    component Aide: Text { color: fen.p.doux; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }

    // Bouton à choix (pastille)
    component Choix: Rectangle {
        id: c
        property string texte
        property bool choisi
        signal clic
        implicitWidth: lab.implicitWidth + 28; implicitHeight: 34; radius: 17
        color: choisi ? fen.p.accent : (zc.containsMouse ? fen.p.haute : fen.p.surface)
        border.color: choisi ? fen.p.accent : fen.p.bord
        opacity: enabled ? 1 : 0.45
        Behavior on color { ColorAnimation { duration: 150 } }
        Text { id: lab; anchors.centerIn: parent; text: c.texte; font.pixelSize: 13
               color: c.choisi ? fen.p.surAccent : fen.p.texte; font.weight: c.choisi ? Font.DemiBold : Font.Normal }
        MouseArea { id: zc; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: c.clic() }
    }

    // Interrupteur
    component Interrupteur: Rectangle {
        id: it
        property bool coche
        signal bascule
        width: 52; height: 28; radius: 14
        color: coche ? fen.p.accent : fen.p.haute
        border.color: coche ? fen.p.accent : fen.p.bord
        Behavior on color { ColorAnimation { duration: 150 } }
        Rectangle { width: 22; height: 22; radius: 11; y: 3; x: it.coche ? 27 : 3
                    color: it.coche ? fen.p.surAccent : fen.p.doux
                    Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } } }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: it.bascule() }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 28

        // ---- Réglages -------------------------------------------------------
        ColumnLayout {
            Layout.fillHeight: true
            Layout.preferredWidth: 430
            spacing: 18

            Row {
                spacing: 12
                Image { source: ctrl.logo; width: 40; height: 40; sourceSize: Qt.size(80, 80); anchors.verticalCenter: parent.verticalCenter }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text { text: "Teintes dynamiques"; color: fen.p.texte; font.pixelSize: 21; font.weight: Font.Bold }
                    Text { text: "Les couleurs du système suivent votre fond d'écran"; color: fen.p.doux; font.pixelSize: 13 }
                }
            }

            Rectangle {
                Layout.fillWidth: true; implicitHeight: 70; radius: 10
                color: fen.p.surface; border.color: fen.p.bord
                RowLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 12
                    Column {
                        Layout.fillWidth: true
                        Titre { text: "Adapter les couleurs au fond d'écran" }
                        Text { text: ctrl.actif ? "Activé : chaque nouveau fond recolore le système" : "Désactivé : vert ExoLyx d'origine"
                               color: fen.p.doux; font.pixelSize: 12 }
                    }
                    Interrupteur { coche: ctrl.actif; onBascule: ctrl.definirActif(!ctrl.actif) }
                }
            }

            ColumnLayout {
                enabled: ctrl.actif; opacity: enabled ? 1 : 0.5
                Layout.fillWidth: true; spacing: 18

                ColumnLayout {
                    spacing: 8
                    Titre { text: "Sombre ou clair" }
                    Flow {
                        Layout.fillWidth: true; spacing: 8
                        Choix { texte: "Selon le fond"; choisi: ctrl.mode === "auto"; onClic: ctrl.definirMode("auto") }
                        Choix { texte: "Toujours sombre"; choisi: ctrl.mode === "sombre"; onClic: ctrl.definirMode("sombre") }
                        Choix { texte: "Toujours clair"; choisi: ctrl.mode === "clair"; onClic: ctrl.definirMode("clair") }
                    }
                }

                ColumnLayout {
                    spacing: 8
                    Titre { text: "Couleur reprise du fond" }
                    Flow {
                        Layout.fillWidth: true; spacing: 8
                        Choix { texte: "La plus présente"; choisi: ctrl.source === "dominante"; onClic: ctrl.definirSource("dominante") }
                        Choix { texte: "La plus vive"; choisi: ctrl.source === "vive"; onClic: ctrl.definirSource("vive") }
                    }
                }

                ColumnLayout {
                    spacing: 6
                    Layout.fillWidth: true
                    RowLayout {
                        Layout.fillWidth: true
                        Titre { text: "Intensité de la teinte"; Layout.fillWidth: true }
                        Text { text: curseur.value < 34 ? "Discrète" : curseur.value < 67 ? "Équilibrée" : "Intense"
                               color: fen.p.accent; font.pixelSize: 13; font.weight: Font.DemiBold }
                    }
                    Slider {
                        id: curseur
                        Layout.fillWidth: true
                        from: 0; to: 100; stepSize: 5
                        value: ctrl.intensite
                        onMoved: ctrl.definirIntensite(value)
                        background: Rectangle {
                            x: curseur.leftPadding; y: curseur.topPadding + curseur.availableHeight / 2 - 3
                            width: curseur.availableWidth; height: 6; radius: 3; color: fen.p.haute
                            Rectangle { width: curseur.visualPosition * parent.width; height: 6; radius: 3; color: fen.p.accent }
                        }
                        handle: Rectangle {
                            x: curseur.leftPadding + curseur.visualPosition * (curseur.availableWidth - 20)
                            y: curseur.topPadding + curseur.availableHeight / 2 - 10
                            width: 20; height: 20; radius: 10; color: fen.p.accent; border.color: fen.p.fond; border.width: 3
                        }
                    }
                    Aide { text: "Discrète : seuls les boutons et la sélection prennent la couleur. Intense : les fenêtres et panneaux aussi." }
                }
            }

            Item { Layout.fillHeight: true }

            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Choix { texte: "Changer de fond d'écran…"; onClic: ctrl.changerFond() }
                Choix { texte: "Réglages par défaut"; onClic: ctrl.reinitialiser() }
                Item { Layout.fillWidth: true }
            }
            Text { text: ctrl.message; visible: text !== ""; color: fen.p.doux; font.pixelSize: 12 }
        }

        // ---- Aperçu --------------------------------------------------------------
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 12

            Rectangle {
                id: scene
                Layout.fillWidth: true
                Layout.preferredHeight: width * 9 / 16
                radius: 14; clip: true
                color: fen.p.surface; border.color: fen.p.bord
                Image {
                    anchors.fill: parent; anchors.margins: 1
                    source: ctrl.fond; fillMode: Image.PreserveAspectCrop
                    sourceSize.width: 640; asynchronous: true
                }
                // fenêtre factice
                Rectangle {
                    x: parent.width * 0.1; y: parent.height * 0.12
                    width: parent.width * 0.62; height: parent.height * 0.62
                    radius: 8; color: fen.p.fond; border.color: fen.p.bord; clip: true
                    Row {
                        anchors.fill: parent
                        Rectangle {
                            width: parent.width * 0.32; height: parent.height; color: fen.p.surface
                            Column {
                                anchors.fill: parent; anchors.margins: 8; spacing: 6
                                Rectangle { width: parent.width; height: 10; radius: 3; color: fen.p.voile
                                            Rectangle { width: 3; height: 10; radius: 1.5; color: fen.p.accent } }
                                Repeater { model: 3; Rectangle { width: parent.width * (0.9 - index * 0.15); height: 8; radius: 3; color: fen.p.haute } }
                            }
                        }
                        Rectangle {
                            width: parent.width * 0.68; height: parent.height; color: fen.p.vue
                            Column {
                                anchors.fill: parent; anchors.margins: 10; spacing: 7
                                Rectangle { width: parent.width * 0.55; height: 10; radius: 3; color: fen.p.texte }
                                Rectangle { width: parent.width * 0.9; height: 6; radius: 3; color: fen.p.doux }
                                Rectangle { width: parent.width * 0.7; height: 6; radius: 3; color: fen.p.doux }
                                Rectangle { width: parent.width; height: 14; radius: 3; color: fen.p.accent; opacity: 0.85
                                            Rectangle { x: 6; y: 4; width: parent.width * 0.4; height: 6; radius: 3; color: fen.p.surAccent } }
                            }
                            Rectangle {
                                anchors { right: parent.right; bottom: parent.bottom; margins: 10 }
                                width: 58; height: 20; radius: 5; color: fen.p.accent
                                Text { anchors.centerIn: parent; text: "Valider"; color: fen.p.surAccent; font.pixelSize: 10; font.weight: Font.DemiBold }
                            }
                        }
                    }
                }
                // dock factice
                Rectangle {
                    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 10 }
                    width: 150; height: 26; radius: 8; color: fen.p.surface; border.color: fen.p.bord; opacity: 0.95
                    Row {
                        anchors.centerIn: parent; spacing: 7
                        Repeater { model: [fen.p.accent, fen.p.accent2, fen.p.accentFroid, fen.p.doux, fen.p.texte]
                                   Rectangle { width: 16; height: 16; radius: 5; color: modelData } }
                    }
                }
            }

            Text { text: ctrl.description; color: fen.p.texte; font.pixelSize: 14; font.weight: Font.DemiBold }

            // nuancier
            Flow {
                Layout.fillWidth: true; spacing: 8
                Repeater {
                    model: [["fond", "Fond"], ["surface", "Panneaux"], ["haute", "Champs"], ["bord", "Bordures"],
                            ["accent", "Accent"], ["accent2", "Survol"], ["accentFroid", "Secondaire"], ["texte", "Texte"]]
                    Column {
                        spacing: 4
                        Rectangle { width: 48; height: 32; radius: 7; color: fen.p[modelData[0]]; border.color: fen.p.bord
                                    Behavior on color { ColorAnimation { duration: 250 } } }
                        Text { text: modelData[1]; color: fen.p.doux; font.pixelSize: 11; width: 48; horizontalAlignment: Text.AlignHCenter }
                    }
                }
            }
            Item { Layout.fillHeight: true }
        }
    }
}

// SPDX-License-Identifier: GPL-3.0-or-later
// Progression de l'installation en cours + journal dépliable.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: panneau
    readonly property var p: ctrl.palette
    readonly property bool deplie: ctrl.journalDeplie
    visible: ctrl.occupe || ctrl.resultat !== "" || ctrl.journal.length > 0
    radius: 10
    color: p.surface
    border.color: ctrl.resultat === "erreur" ? p.erreur : p.bordure
    implicitHeight: colonne.implicitHeight + 28

    ColumnLayout {
        id: colonne
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Rectangle {
                width: 10; height: 10; radius: 5
                color: ctrl.resultat === "erreur" ? panneau.p.erreur
                     : ctrl.resultat === "ok" ? panneau.p.accent : panneau.p.info
                SequentialAnimation on opacity {
                    running: ctrl.occupe; loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 600 }
                    NumberAnimation { to: 1; duration: 600 }
                }
            }
            Text {
                Layout.fillWidth: true
                text: ctrl.libelle !== "" ? ctrl.libelle : "Journal des opérations"
                color: panneau.p.texte
                elide: Text.ElideRight
                font.family: "Inter"; font.pixelSize: 14
            }
            Text {
                visible: ctrl.occupe || ctrl.resultat === "ok"
                text: Math.round(ctrl.progression * 100) + " %"
                color: panneau.p.texteDoux
                font.family: "Inter"; font.pixelSize: 13
            }
            Text {
                text: panneau.deplie ? "Masquer le journal ▴" : "Afficher le journal ▾"
                color: panneau.p.accent
                font.family: "Inter"; font.pixelSize: 13
                MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor
                    onClicked: ctrl.journalDeplie = !ctrl.journalDeplie }
            }
        }

        // barre de progression
        Rectangle {
            Layout.fillWidth: true
            visible: ctrl.occupe || ctrl.resultat !== ""
            height: 8; radius: 4
            color: panneau.p.surfaceHaute
            Rectangle {
                height: parent.height; radius: 4
                width: parent.width * ctrl.progression
                color: ctrl.resultat === "erreur" ? panneau.p.erreur : panneau.p.accent
                Behavior on width { NumberAnimation { duration: 250 } }
            }
        }

        // journal
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            visible: panneau.deplie
            radius: 6
            color: ctrl.sombre ? "#0A0F0C" : "#F9FBF7"
            border.color: panneau.p.bordure
            ScrollView {
                id: defilement
                anchors.fill: parent
                anchors.margins: 6
                TextArea {
                    readOnly: true
                    text: ctrl.journal
                    color: panneau.p.texteDoux
                    font.family: "JetBrains Mono"; font.pixelSize: 11
                    wrapMode: TextArea.WrapAnywhere
                    background: null
                    onTextChanged: cursorPosition = length
                }
            }
        }
    }
}
